"""
Cross-source deduplication cho unified activities.

Chiến lược 2 tầng:

  Tầng 1 — Geo-blocking + name match (cho activities CÓ coords):
    - Bin lưới ~55m × 50m (bin_size = 0.0005°)
    - So sánh trong cùng bin + 4 bin lân cận (mỗi cặp check đúng 1 lần)
    - Trùng khi: haversine ≤ threshold AND name_similarity ≥ 0.80
    - threshold = 200m nếu activity_type nature, 50m còn lại

  Tầng 2 — Name-only match cho Goong (KHÔNG có coords):
    - So sánh từng Goong activity với toàn bộ canonical đã merge ở tầng 1
    - Trùng khi name_similarity ≥ 0.90 (threshold cao hơn vì thiếu geo signal)
    - Không trùng → giữ riêng

Canonical selection: source priority foursquare > overture > wikidata > geoapify > osm > goong > llm.
Cluster duplicates → 1 canonical + provenance.merged_from = [other source IDs].

Similarity = max(SequenceMatcher.ratio, token-set Jaccard) trên name đã normalize
(strip dấu tiếng Việt, lowercase, bỏ stop-words như "quan", "nha hang"...).
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from .schema import haversine_m


# ─── Configurable thresholds ────────────────────────────────────────────────
GEO_DISTANCE_TIGHT_M:   float = 20.0      # ≤ 20m → name threshold thấp (cross-language)
GEO_DISTANCE_URBAN_M:   float = 50.0
GEO_DISTANCE_NATURE_M:  float = 200.0
NAME_SIM_TIGHT_GEO:     float = 0.55      # filter: chặn over-merge POI khác ngẫu nhiên ở cùng tọa độ
NAME_SIM_GEO_MATCH:     float = 0.80
NAME_SIM_NO_GEO_MATCH:  float = 0.90

# Bin size in degrees lat/lng. 0.0005° ≈ 55m at lat 22°, 50m at equator.
GEO_BIN_SIZE_DEG:       float = 0.0005

# Higher priority = lower index = preferred as canonical
SOURCE_PRIORITY: Tuple[str, ...] = (
    "foursquare", "overture", "wikidata", "geoapify", "osm", "goong", "llm",
)

# Bỏ khi compute Jaccard (vẫn giữ khi compute SequenceMatcher.ratio để bảo toàn char-level).
# Bao gồm:
#   - generic POI prefix (quan, nha hang, ...)
#   - English stop words
#   - Common VN location-name fragments — vì khi search 1 vùng, gần như mọi POI
#     đều chứa tên vùng → các token này tạo overlap giả tạo. Bỏ → so sánh dựa
#     trên phần tên đặc trưng còn lại.
_NAME_STOP_TOKENS = {
    # Generic POI prefix
    "quan", "nha", "hang", "khach", "san", "homestay", "resort",
    "tiem", "cua", "cho", "cafe", "coffee",
    # English fillers
    "the", "and", "of", "in", "at", "de", "den",
    # VN location-name fragments (top destinations)
    "sa", "pa",            # Sa Pa
    "ha", "noi",           # Ha Noi
    "da", "nang",          # Da Nang
    "long",                # Ha Long (riêng "ha" đã có)
    "giang",               # Ha Giang
    "lat",                 # Da Lat
    "hoi", "an",           # Hoi An
    "trang",               # Nha Trang
    "phong",               # Phong Nha
    "phu", "quoc",         # Phu Quoc
    "hue",                 # Huế
    "vietnam", "viet", "nam",
}


# ─── Translation / spelling normalization ──────────────────────────────────
#
# Mục tiêu: bắt được cross-language match như:
#   "Sapa Rice Fields"  vs  "Ruộng bậc thang Sa Pa"
#   "Trung Nguyên Coffee" vs  "Quán cà phê Trung Nguyên"
#
# Áp dụng SAU strip_diacritics + lowercase, TRƯỚC tokenize.
# Pattern dùng \b word boundary. Sort theo length desc → multi-word match trước single-word.
#
# Nguyên tắc chọn entries:
# - Compound city names: bắt buộc (sapa↔sa pa luôn rất nhập nhằng)
# - Multi-word VN→EN: an toàn (không clash proper names)
# - Single-word VN→EN: CHỈ chọn các từ không clash với tên riêng phổ biến.
#   Bỏ qua những từ như "ho" (lake — clash Hồ Chí Minh), "song" (river — clash Sơn),
#   "tra" (tea — clash Trà), "dong" (cave/east — clash nhiều), "ban" (village — clash Bàn/Bản).
_TRANSLATIONS: List[Tuple[str, str]] = sorted([
    # ─── Compound VN city names (canonical = spaced form) ──────────────
    ("hochiminh", "ho chi minh"),
    ("hanoi",     "ha noi"),
    ("danang",    "da nang"),
    ("hagiang",   "ha giang"),
    ("halong",    "ha long"),
    ("phuquoc",   "phu quoc"),
    ("nhatrang",  "nha trang"),
    ("sapa",      "sa pa"),
    ("dalat",     "da lat"),
    ("hoian",     "hoi an"),
    ("phongnha",  "phong nha"),

    # ─── Multi-word VN → EN ────────────────────────────────────────────
    ("ruong bac thang", "rice field"),
    ("pho co",          "old town"),
    ("nha hang",        "restaurant"),
    ("khach san",       "hotel"),
    ("vuon hoa",        "flower garden"),
    ("vuon quoc gia",   "national park"),
    ("ca phe",          "coffee"),
    ("thi tran",        "town"),
    ("hang dong",       "cave"),
    ("bai bien",        "beach"),

    # ─── Single-word VN → EN (safe choices) ─────────────────────────────
    ("nui",   "mountain"),
    ("thac",  "waterfall"),
    ("deo",   "pass"),
    ("chua",  "pagoda"),
    ("vuon",  "garden"),
    ("rung",  "forest"),
    ("cau",   "bridge"),
    ("dao",   "island"),
    ("bien",  "sea"),
    ("vinh",  "bay"),
    ("phay",  "ferry"),
    ("cong",  "park"),
], key=lambda kv: -len(kv[0]))


def _apply_translations(s: str) -> str:
    """Áp dụng các translation/normalization với word boundary."""
    for vn, en in _TRANSLATIONS:
        s = re.sub(r"\b" + re.escape(vn) + r"\b", en, s)
    return s


def _stem_plural_s(token: str) -> str:
    """Strip trailing 's' để "fields" ≡ "field". Chỉ token có > 4 ký tự + không kết "ss"."""
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


# ─── Name normalization & similarity ────────────────────────────────────────

def _strip_diacritics(s: str) -> str:
    """Bỏ dấu tiếng Việt + combining marks khác. `đ`/`Đ` → `d`/`D`."""
    nfd = unicodedata.normalize("NFD", s)
    no_combining = "".join(c for c in nfd if not unicodedata.combining(c))
    return no_combining.replace("đ", "d").replace("Đ", "D")


def normalize_name(name: Optional[str]) -> str:
    """
    Normalize POI name để so sánh:
    - strip diacritics + lowercase
    - bỏ punctuation
    - apply translations (VN compound names → spaced, VN terms → EN)
    - collapse whitespace
    """
    if not name:
        return ""
    s = _strip_diacritics(name).lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _apply_translations(s)
    s = re.sub(r"\s+", " ", s).strip()   # collapse lại sau translation
    return s


def name_similarity(name_a: Optional[str], name_b: Optional[str]) -> float:
    """
    Similarity = max(SequenceMatcher.ratio, token-set Jaccard).
    Bắt cả char-level edits ("Sapa" vs "Sa Pa") và word-order changes.
    Token-set Jaccard có stem plural ('s') để "fields" ≡ "field".
    Trả về float ∈ [0, 1].
    """
    a = normalize_name(name_a)
    b = normalize_name(name_b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    ratio = SequenceMatcher(None, a, b).ratio()

    tokens_a = {_stem_plural_s(t) for t in a.split() if t not in _NAME_STOP_TOKENS}
    tokens_b = {_stem_plural_s(t) for t in b.split() if t not in _NAME_STOP_TOKENS}
    if tokens_a and tokens_b:
        jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    else:
        jaccard = 0.0

    return max(ratio, jaccard)


# ─── Geo helpers ────────────────────────────────────────────────────────────

def _geo_bin(coords: Dict[str, float]) -> Tuple[int, int]:
    return (int(coords["lat"] / GEO_BIN_SIZE_DEG),
            int(coords["lng"] / GEO_BIN_SIZE_DEG))


def _geo_threshold(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """200m nếu ít nhất 1 trong 2 là nature; còn lại 50m."""
    type_a = a["metadata"].get("activity_type")
    type_b = b["metadata"].get("activity_type")
    if type_a == "nature" or type_b == "nature":
        return GEO_DISTANCE_NATURE_M
    return GEO_DISTANCE_URBAN_M


def _are_duplicates_geo(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[bool, bool]:
    """
    Trả về (is_duplicate, was_tight_geo).

    Quy tắc theo distance:
      - dist > threshold (50m thường / 200m nature): KHÔNG trùng
      - dist ≤ GEO_DISTANCE_TIGHT_M (20m): chỉ cần name_sim ≥ 0.40
        → bắt được cross-language ("Sapa Rice Fields" vs "Ruộng bậc thang Sa Pa")
        → CHẶN over-merge các POI khác ngẫu nhiên cùng tọa độ
          (Overture có thể có 30 quán khác nhau cùng tọa độ → tên khác hẳn → < 0.40)
      - 20m < dist ≤ threshold: cần name_sim ≥ 0.80 (strict)
    """
    coords_a = a["place"]["coordinates"]
    coords_b = b["place"]["coordinates"]
    if not coords_a or not coords_b:
        return False, False
    dist = haversine_m(coords_a["lat"], coords_a["lng"],
                       coords_b["lat"], coords_b["lng"])
    if dist > _geo_threshold(a, b):
        return False, False

    sim = name_similarity(a["metadata"]["name"], b["metadata"]["name"])
    if dist <= GEO_DISTANCE_TIGHT_M:
        return sim >= NAME_SIM_TIGHT_GEO, True
    return sim >= NAME_SIM_GEO_MATCH, False


# ─── Union-Find ─────────────────────────────────────────────────────────────

class _UnionFind:
    def __init__(self, items: List[str]) -> None:
        self.parent = {x: x for x in items}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # path compression
            x = self.parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry


# ─── Canonical selection & merge ────────────────────────────────────────────

def _source_priority(source: str) -> int:
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def _pick_canonical(cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Source priority thấp nhất thắng (foursquare nhất, llm cuối)."""
    return min(cluster, key=lambda a: _source_priority(a["source"]))


def _merge_cluster(cluster: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gộp cluster: chọn canonical, các bản còn lại được serialize vào
    provenance.merged_from. Trả về SHALLOW copy (canonical + provenance mới).
    """
    canonical = _pick_canonical(cluster)
    others = [a for a in cluster if a["activity_id"] != canonical["activity_id"]]

    merged_from = [
        {
            "source":         a["source"],
            "activity_id":    a["activity_id"],
            "raw_source_id":  a["provenance"]["raw_source_id"],
            "source_url":     a["provenance"]["source_url"],
        }
        for a in others
    ]

    new_provenance = {**canonical["provenance"], "merged_from": merged_from}
    return {**canonical, "provenance": new_provenance}


def _ensure_merged_from(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Bảo đảm activity có `provenance.merged_from = []` (empty list)."""
    if "merged_from" in activity["provenance"]:
        return activity
    new_provenance = {**activity["provenance"], "merged_from": []}
    return {**activity, "provenance": new_provenance}


# ─── Main entry ─────────────────────────────────────────────────────────────

def dedupe_activities(
    activities: List[Dict[str, Any]],
    name_threshold_no_geo: float = NAME_SIM_NO_GEO_MATCH,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Cross-source dedupe. Trả (deduped_list, stats).

    `stats` chứa:
        input_count, geo_clusters_merged, geo_records_absorbed,
        no_geo_matched, no_geo_kept_separate, output_count
    """
    stats: Dict[str, Any] = {
        "input_count":            len(activities),
        "geo_clusters_merged":    0,
        "geo_records_absorbed":   0,
        "geo_only_merges":        0,   # số cặp merged nhờ rule ≤ 20m (không cần name)
        "no_geo_matched":         0,
        "no_geo_kept_separate":   0,
        "output_count":           0,
    }

    if not activities:
        return [], stats

    # Tách activities có coords vs không có coords
    with_coords: List[Dict[str, Any]] = []
    without_coords: List[Dict[str, Any]] = []
    for a in activities:
        if a["place"]["coordinates"]:
            with_coords.append(a)
        else:
            without_coords.append(a)

    # ─── Tầng 1: Geo-blocking + name match ──────────────────────────────────
    bins: Dict[Tuple[int, int], List[Dict[str, Any]]] = defaultdict(list)
    for a in with_coords:
        bins[_geo_bin(a["place"]["coordinates"])].append(a)

    uf = _UnionFind([a["activity_id"] for a in with_coords])

    # Cặp neighbor: chỉ check 4 hướng (right, down-left, down, down-right)
    # → mỗi cặp inter-bin được check đúng 1 lần
    _NEIGHBOR_OFFSETS = ((0, 1), (1, -1), (1, 0), (1, 1))

    for (bin_lat, bin_lng), items in bins.items():
        # Within-bin pairs
        for i in range(len(items)):
            ai = items[i]
            for j in range(i + 1, len(items)):
                is_dup, geo_only = _are_duplicates_geo(ai, items[j])
                if is_dup:
                    uf.union(ai["activity_id"], items[j]["activity_id"])
                    if geo_only:
                        stats["geo_only_merges"] += 1
        # Inter-bin pairs với 4 neighbor offsets
        for d_lat, d_lng in _NEIGHBOR_OFFSETS:
            neighbor = (bin_lat + d_lat, bin_lng + d_lng)
            if neighbor not in bins:
                continue
            for a in items:
                for b in bins[neighbor]:
                    is_dup, geo_only = _are_duplicates_geo(a, b)
                    if is_dup:
                        uf.union(a["activity_id"], b["activity_id"])
                        if geo_only:
                            stats["geo_only_merges"] += 1

    # Group by root
    clusters: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for a in with_coords:
        clusters[uf.find(a["activity_id"])].append(a)

    geo_merged: List[Dict[str, Any]] = []
    canonical_index: Dict[str, Dict[str, Any]] = {}   # activity_id → canonical dict (mutable)
    for cluster in clusters.values():
        if len(cluster) > 1:
            stats["geo_clusters_merged"] += 1
            stats["geo_records_absorbed"] += len(cluster) - 1
            merged = _merge_cluster(cluster)
        else:
            merged = _ensure_merged_from(cluster[0])
        geo_merged.append(merged)
        canonical_index[merged["activity_id"]] = merged

    # ─── Tầng 2: Name-only match cho without_coords (Goong) ──────────────────
    final: List[Dict[str, Any]] = list(geo_merged)

    for ng_act in without_coords:
        best_match: Optional[Dict[str, Any]] = None
        best_sim: float = 0.0
        ng_name = ng_act["metadata"]["name"]

        for canonical in geo_merged:
            sim = name_similarity(ng_name, canonical["metadata"]["name"])
            if sim > best_sim:
                best_sim = sim
                best_match = canonical

        if best_match is not None and best_sim >= name_threshold_no_geo:
            # Append ng_act vào merged_from của canonical
            # (mutate in-place — best_match được link trong canonical_index)
            best_match["provenance"]["merged_from"].append({
                "source":          ng_act["source"],
                "activity_id":     ng_act["activity_id"],
                "raw_source_id":   ng_act["provenance"]["raw_source_id"],
                "source_url":      ng_act["provenance"]["source_url"],
                "name_similarity": round(best_sim, 3),
            })
            stats["no_geo_matched"] += 1
        else:
            final.append(_ensure_merged_from(ng_act))
            stats["no_geo_kept_separate"] += 1

    stats["output_count"] = len(final)
    return final, stats


__all__ = [
    "dedupe_activities",
    "name_similarity",
    "normalize_name",
    "GEO_DISTANCE_URBAN_M",
    "GEO_DISTANCE_NATURE_M",
    "NAME_SIM_GEO_MATCH",
    "NAME_SIM_NO_GEO_MATCH",
    "SOURCE_PRIORITY",
]
