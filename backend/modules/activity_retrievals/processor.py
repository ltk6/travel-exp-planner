"""
processor.py — Clean + filter + rank + enrich raw retrievals into usable activities.

Pipeline:
    retrieve_all(loc, dedupe=True)          # 3697 → 2841 (ví dụ loc_001)
        → filter(has_coords AND has_type)   # 2841 → ~1834
        → quality_score (completeness)
        → sort by (quality DESC, distance ASC)
        → top_k cap                          # default LLM_N5_TARGET_COUNT (10)
        → LLM enrich missing descriptions    # optional
        → persist to processed/{loc_id}.json

Public API:
    >>> from backend.modules.activity_retrievals import process_activities
    >>> result = process_activities({"location_id":"loc_001","lat":22.3,"lng":103.77})
    >>> result["activities"]   # top-10 usable activities
    >>> result["stats"]        # {raw, after_filter, output, descriptions_enriched}
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import LLM_N5_TARGET_COUNT

from .orchestrator import retrieve_all

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).parent / "processed"

# activity_type values coi là "ngắm cảnh / di tích" (passive viewing) thay vì
# "hoạt động" (actively doing). Dùng để cân bằng tỉ lệ trong output.
_SIGHTSEEING_TYPES = {"nature", "culture"}

# Hậu tố/tiền tố địa lý chung cần strip khi so khớp tên POI với anchor.
# Giúp "Hạ Long" == "Hạ Long Bay" == "Vịnh Hạ Long" (sau normalize).
_ANCHOR_FILLER_WORDS = {
    "bay", "vinh",
    "island", "cu lao", "dao",
    "national park", "park", "vqg", "vuon quoc gia",
    "town", "city", "district", "ward",
    "thi tran", "thanh pho", "huyen", "phuong", "xa",
    "mountain", "nui",
    "lake", "ho",
    "beach", "bai bien", "bai",
    "river", "song",
    "valley", "thung lung",
    "cave", "hang", "dong",
}


# Field completeness weights for quality score (sum normalized to 1.0)
_QUALITY_WEIGHTS_META = {
    "description":        2.0,
    "activity_type":      1.5,
    "indoor_outdoor":     1.0,
    "estimated_duration": 0.5,
}
_QUALITY_WEIGHTS_SIGNALS = {
    "rating":        1.5,
    "image_url":     1.0,
    "opening_hours": 0.5,
    "website":       0.3,
}
_MAX_QUALITY = sum(_QUALITY_WEIGHTS_META.values()) + sum(_QUALITY_WEIGHTS_SIGNALS.values())


def _quality_score(activity: Dict[str, Any]) -> float:
    """0.0 → 1.0 based on field completeness."""
    score = 0.0
    md = activity.get("metadata", {})
    sg = activity.get("signals", {})
    for field, weight in _QUALITY_WEIGHTS_META.items():
        if md.get(field) is not None:
            score += weight
    for field, weight in _QUALITY_WEIGHTS_SIGNALS.items():
        if sg.get(field) is not None:
            score += weight
    return round(score / _MAX_QUALITY, 4)


def _has_required(activity: Dict[str, Any]) -> bool:
    return (
        activity["place"].get("coordinates") is not None
        and activity["metadata"].get("activity_type") is not None
    )


# =============================================================================
# NAME NORMALIZATION & DEDUPE
# =============================================================================

def _strip_diacritics(s: str) -> str:
    """Bỏ dấu tiếng Việt + map đ→d."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def _normalize_name(s: str) -> str:
    """lowercase + bỏ dấu + bỏ ký tự không phải chữ/số + collapse whitespace."""
    if not s:
        return ""
    s = _strip_diacritics(s.lower())
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _core_name(s: str) -> str:
    """Tên 'cốt lõi' để so khớp với anchor: bỏ filler words địa lý."""
    n = _normalize_name(s)
    if not n:
        return ""
    # Replace multi-word fillers first (e.g. "national park")
    for w in sorted(_ANCHOR_FILLER_WORDS, key=len, reverse=True):
        n = re.sub(r"\b" + re.escape(w) + r"\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _is_anchor_duplicate(poi_name: str, anchor_name: str) -> bool:
    """POI bị coi là 'trùng anchor' khi core-name của 2 bên trùng nhau."""
    if not poi_name or not anchor_name:
        return False
    a = _core_name(poi_name)
    b = _core_name(anchor_name)
    if not a or not b:
        return False
    # Trùng tuyệt đối hoặc một bên chứa toàn bộ bên kia VÀ phần thừa rất ngắn
    if a == b:
        return True
    longer, shorter = (a, b) if len(a) >= len(b) else (b, a)
    if shorter and shorter in longer and len(longer) - len(shorter) <= 3:
        # "ha long" in "ha long s" → có thể là biến thể, drop
        return True
    return False


def _drop_anchor_duplicates(
    activities: List[Dict[str, Any]], anchor_name: str
) -> List[Dict[str, Any]]:
    out = []
    dropped = 0
    for a in activities:
        name = a.get("metadata", {}).get("name", "")
        if _is_anchor_duplicate(name, anchor_name):
            dropped += 1
            continue
        out.append(a)
    if dropped:
        logger.info("Dropped %d POIs duplicating anchor %r", dropped, anchor_name)
    return out


def _dedupe_by_name(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Giữ POI đầu tiên (đã sort theo quality) khớp với:
      - normalized name, HOẶC
      - rounded coords (4 chữ số ~ 11m precision) — cùng vị trí = cùng POI
        ngay cả khi 2 source đặt tên khác nhau ('Gem Coffee Art' vs 'Gem Valley Coffee Art').
    """
    seen_names: set = set()
    seen_coords: set = set()
    out: List[Dict[str, Any]] = []
    for a in activities:
        name_key = _normalize_name(a.get("metadata", {}).get("name", ""))
        coords = a.get("place", {}).get("coordinates") or {}
        coord_key = None
        if coords.get("lat") is not None and coords.get("lng") is not None:
            coord_key = (round(coords["lat"], 4), round(coords["lng"], 4))
        if (name_key and name_key in seen_names) or (coord_key and coord_key in seen_coords):
            continue
        if name_key:
            seen_names.add(name_key)
        if coord_key:
            seen_coords.add(coord_key)
        out.append(a)
    return out


# =============================================================================
# SIGHTSEEING vs ACTIVITY BALANCE
# =============================================================================

def _is_sightseeing(a: Dict[str, Any]) -> bool:
    return a.get("metadata", {}).get("activity_type") in _SIGHTSEEING_TYPES


def _balance_by_type(
    activities: List[Dict[str, Any]],
    top_k: int,
    sightseeing_ratio: float = 0.4,
    preferred_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Cân bằng output theo 2 chế độ:

    1. Nếu `preferred_types` được truyền (user chọn ưu tiên ăn uống / ngắm cảnh /
       v.v. ở UI): lấy 70% từ pool preferred + 30% từ phần còn lại, vẫn giữ một
       chút đa dạng để khám phá. Dùng list[str] để có thể boost nhiều type cùng lúc.

    2. Nếu không có preferred_types: cân bằng sightseeing vs activity theo
       `sightseeing_ratio` (default 0.4 = 40% sightseeing / 60% activity).
       sightseeing = activity_type ∈ {nature, culture}.

    Mỗi pool đã được sort theo quality từ trước nên chỉ cần slice.
    """
    # ─── Mode 1: preferred types ─────────────────────────────────────────────
    if preferred_types:
        prefs = set(preferred_types)
        preferred = [a for a in activities
                     if a.get("metadata", {}).get("activity_type") in prefs]
        others    = [a for a in activities
                     if a.get("metadata", {}).get("activity_type") not in prefs]
        n_pref  = int(round(top_k * 0.7))
        n_other = top_k - n_pref
        chosen_pref  = preferred[:n_pref]
        chosen_other = others[:n_other]
        # Bù nếu pool nào không đủ
        shortfall = top_k - len(chosen_pref) - len(chosen_other)
        if shortfall > 0:
            extra = (preferred[len(chosen_pref):] if len(chosen_other) >= n_other
                     else others[len(chosen_other):])
            chosen_pref.extend(extra[:shortfall])
        # Interleave: 2 preferred, 1 other
        combined: List[Dict[str, Any]] = []
        pi = oi = 0
        while pi < len(chosen_pref) or oi < len(chosen_other):
            for _ in range(2):
                if pi < len(chosen_pref):
                    combined.append(chosen_pref[pi]); pi += 1
            if oi < len(chosen_other):
                combined.append(chosen_other[oi]); oi += 1
        return combined[:top_k]

    # ─── Mode 2: sightseeing vs activity ratio ───────────────────────────────
    sights = [a for a in activities if _is_sightseeing(a)]
    acts   = [a for a in activities if not _is_sightseeing(a)]

    n_sight_target = int(round(top_k * sightseeing_ratio))
    n_act_target   = top_k - n_sight_target

    chosen_sights = sights[:n_sight_target]
    chosen_acts   = acts[:n_act_target]

    shortfall = top_k - len(chosen_sights) - len(chosen_acts)
    if shortfall > 0:
        extra_pool = (sights[len(chosen_sights):] if len(chosen_acts) < n_act_target
                      else acts[len(chosen_acts):])
        chosen_acts.extend(extra_pool[:shortfall])

    # Interleave: 2 activity rồi 1 sightseeing
    combined = []
    si = ai = 0
    while si < len(chosen_sights) or ai < len(chosen_acts):
        for _ in range(2):
            if ai < len(chosen_acts):
                combined.append(chosen_acts[ai]); ai += 1
        if si < len(chosen_sights):
            combined.append(chosen_sights[si]); si += 1
    return combined[:top_k]


def _rank_key(activity: Dict[str, Any]) -> tuple:
    """Higher quality first, then closer distance tiebreaks."""
    qual = activity.get("_quality", 0.0)
    dist = activity["place"].get("distance_from_anchor_m") or 10**9
    return (-qual, dist)


def _enforce_source_diversity(
    activities: List[Dict[str, Any]],
    top_k: int,
    max_per_source: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Walk pre-sorted list, cap N items per source to avoid single-source dominance."""
    if max_per_source is None:
        max_per_source = max(2, (top_k + 2) // 3)  # ~3-4 per source for top_k=10
    seen: Dict[str, int] = {}
    primary: List[Dict[str, Any]] = []
    overflow: List[Dict[str, Any]] = []
    for a in activities:
        src = a["source"]
        if seen.get(src, 0) < max_per_source:
            primary.append(a)
            seen[src] = seen.get(src, 0) + 1
            if len(primary) >= top_k:
                return primary
        else:
            overflow.append(a)
    # Not enough diverse items — fill from overflow (already quality-sorted)
    remaining = top_k - len(primary)
    return primary + overflow[:remaining]


# =============================================================================
# QUALITY + LANGUAGE FILTERS (for DB seed path)
# =============================================================================

# Unicode blocks that signal "không phải tiếng Việt/Anh latin" — drop để DB
# không bị noise tiếng Nga/Trung/Nhật/Hàn/Ả-rập từ các nguồn tourist quốc tế.
# Tiếng Việt có dấu vẫn nằm trong Latin Extended-A/B (< U+0400) nên an toàn.
_FOREIGN_SCRIPT_RE = re.compile(
    "["
    "Ѐ-ӿ"   # Cyrillic
    "֐-׿"   # Hebrew
    "؀-ۿ"   # Arabic
    "一-鿿"   # CJK Unified
    "぀-ゟ"   # Hiragana
    "゠-ヿ"   # Katakana
    "가-힯"   # Hangul
    "]"
)


def _has_foreign_script(text: str) -> bool:
    """True nếu chuỗi chứa ít nhất 1 ký tự thuộc script không Latin."""
    if not text:
        return False
    return bool(_FOREIGN_SCRIPT_RE.search(text))


def drop_foreign_script(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Loại activity có name/description chứa ký tự script ngoài Latin."""
    out = []
    dropped = 0
    for a in activities:
        md = a.get("metadata", {})
        if _has_foreign_script(md.get("name") or "") or _has_foreign_script(md.get("description") or ""):
            dropped += 1
            continue
        out.append(a)
    if dropped:
        logger.info("Dropped %d activities with foreign script", dropped)
    return out


def filter_by_quality(activities: List[Dict[str, Any]], min_quality: float = 0.3) -> List[Dict[str, Any]]:
    """Drop activity có _quality < min_quality. Assumes _quality đã được set."""
    out = [a for a in activities if (a.get("_quality") or 0.0) >= min_quality]
    if len(out) < len(activities):
        logger.info("Quality filter (>=%.2f): %d → %d", min_quality, len(activities), len(out))
    return out


def cap_per_source(activities: List[Dict[str, Any]], max_per: int = 30) -> List[Dict[str, Any]]:
    """Cap số acts per source. Assumes input đã sort theo quality desc."""
    seen: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    for a in activities:
        s = a.get("source", "unknown")
        if seen.get(s, 0) >= max_per:
            continue
        out.append(a)
        seen[s] = seen.get(s, 0) + 1
    return out


def _enrich_descriptions(
    activities: List[Dict[str, Any]],
    location_name: str,
) -> int:
    """
    Rewrite name (sang tiếng Việt, phong cách 'trải nghiệm/hoạt động') +
    generate description tiếng Việt cho TẤT CẢ top results. Trả về count enriched.

    Một LLM call cho toàn bộ list — giúp đồng nhất ngôn ngữ và đảm bảo tên
    POI không lẫn lộn Anh/Việt (vì các nguồn map mỗi cái trả 1 kiểu).
    """
    if not activities:
        return 0

    try:
        from backend.modules.n5_activity_generation.providers import get_llm_chain
    except ImportError as e:
        logger.warning("N5 providers unavailable, skip enrich: %s", e)
        return 0

    chain = get_llm_chain()
    if not chain:
        logger.warning("No LLM provider configured, skip enrich")
        return 0

    targets = activities  # rewrite tất cả
    items_str = "\n".join(
        f'{i+1}. "{a["metadata"]["name"]}" '
        f'(loại={a["metadata"].get("activity_type","?")}, '
        f'subtype={a["metadata"].get("activity_subtype") or "-"})'
        for i, a in enumerate(targets)
    )
    prompt = f"""Bạn là chuyên gia du lịch Việt Nam. Cho danh sách POI/địa điểm tại {location_name} dưới đây, với MỖI item hãy tạo:

1. "name" — Tên hoạt động trải nghiệm (5-10 từ, tiếng Việt thuần).
   - Giữ tên riêng/brand/địa danh (VD "Gem Coffee Art", "Fansipan", "Cù Lao Chàm").
   - Việt hoá các từ chung tiếng Anh ("Bay"→"Vịnh", "Island"→"Đảo/Cù Lao", "Park"→"Công viên/Vườn Quốc gia", "Restaurant"→"Nhà hàng", "Cafe"→"Quán cà phê").
   - Bắt đầu bằng ĐỘNG TỪ trải nghiệm: Khám phá / Ngắm cảnh / Thưởng thức / Trải nghiệm / Chinh phục / Dạo bộ / Check-in / Vãn cảnh.
   - VÍ DỤ:
     "Hoang Lien National Park" → "Khám phá Vườn quốc gia Hoàng Liên"
     "Fansipan" → "Chinh phục đỉnh Fansipan"
     "Gem Coffee Art" → "Thưởng thức cà phê tại Gem Coffee Art"
     "Cham Island" → "Vãn cảnh Cù Lao Chàm"

2. "description" — 1-2 câu tiếng Việt, súc tích, gợi cảm xúc thật, không sáo rỗng.

POI:
{items_str}

Trả về CHÍNH XÁC 1 JSON array gồm {len(targets)} object, format:
[{{"index":1,"name":"...","description":"..."}}, ...]
CHỈ JSON, không markdown, không giải thích."""

    for provider in chain:
        try:
            text = provider.generate(prompt, retries=0, temperature=0.5, max_tokens=3000)
        except Exception as e:
            logger.warning("Provider %s raised: %s", getattr(provider, "name", "?"), e)
            continue
        if not text:
            continue
        text = text.strip()
        if text.startswith("```"):
            inner = text.split("```", 2)
            if len(inner) >= 2:
                text = inner[1].lstrip("json").strip().rstrip("`").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Provider %s returned non-JSON: %s\nText: %r", provider.name, e, text[:300])
            continue

        if isinstance(parsed, dict):
            list_vals = [v for v in parsed.values() if isinstance(v, list)]
            if len(list_vals) == 1:
                parsed = list_vals[0]

        items: List[Dict[str, Any]] = []
        if isinstance(parsed, list):
            for i, it in enumerate(parsed):
                if isinstance(it, dict):
                    idx = int(it.get("index", i + 1)) - 1
                    items.append({
                        "idx":  idx,
                        "name": (it.get("name") or "").strip(),
                        "desc": (it.get("description") or "").strip(),
                    })

        count = 0
        for it in items:
            idx, new_name, new_desc = it["idx"], it["name"], it["desc"]
            if not (0 <= idx < len(targets)):
                continue
            md = targets[idx]["metadata"]
            if new_name:
                md["name_original"] = md.get("name")  # giữ tên gốc cho debug
                md["name"] = new_name
            if new_desc:
                md["description"] = new_desc
            if new_name or new_desc:
                count += 1
        logger.info("LLM enriched %d/%d (name+desc) via %s", count, len(targets), provider.name)
        return count
    return 0


def process_activities(
    location: Dict[str, Any],
    radius: int = 20000,
    top_k: int = LLM_N5_TARGET_COUNT,
    enrich_descriptions: bool = True,
    persist: bool = True,
    preferred_types: Optional[List[str]] = None,
    sightseeing_ratio: float = 0.4,
) -> Dict[str, Any]:
    """
    Full processing pipeline for 1 anchor location.

    Args:
        location: {"location_id": str, "lat": float, "lng": float, "name"?: str, ...}
        radius:   meters (default 20000)
        top_k:    max output size (default = LLM_N5_TARGET_COUNT)
        enrich_descriptions: gọi N5 LLM để fill description thiếu (default True)
        persist:  ghi processed/{location_id}.json (default True)

    Returns:
        {
            "location_id": str,
            "activities":  [top_k cleaned activities],
            "stats":       {raw, after_filter, output, descriptions_enriched},
            "elapsed_s":   float (chỉ tính retrieve, không tính LLM enrich),
            "output_path": str | None,
        }
    """
    loc_id = str(location["location_id"])
    loc_name = location.get("name") or loc_id

    # NOTE: dedupe disabled — current cross-source dedupe is O(28 × N) name-similarity
    # comparisons over all ~3700 raw items, costing ~50s wall-time for loc_001.
    # Source-diversity cap below + has-coords + has-type filter give acceptable
    # output quality without it. Re-enable once dedupe.py is optimized.
    retrieved = retrieve_all(location, radius=radius, dedupe=False)
    all_acts = retrieved["activities"]

    filtered = [a for a in all_acts if _has_required(a)]
    n_after_has_req = len(filtered)

    # Drop POI trùng tên anchor ("Hạ Long Bay" anchor → drop POI "Hạ Long" etc.)
    filtered = _drop_anchor_duplicates(filtered, loc_name)
    n_after_anchor_drop = len(filtered)

    # Score quality, sort
    for a in filtered:
        a["_quality"] = _quality_score(a)
    filtered.sort(key=_rank_key)

    # Cross-source name-dedupe (cheap O(N) sau sort — giữ entry chất lượng cao nhất)
    filtered = _dedupe_by_name(filtered)
    n_after_name_dedupe = len(filtered)

    # Source diversity cap → lấy candidate pool gấp 2 top_k để balance còn chỗ chọn
    candidates = _enforce_source_diversity(filtered, top_k * 2)

    # Balance — default 40% sightseeing / 60% activity. Nếu user truyền
    # preferred_types qua UI thì boost mạnh các type đó (70/30 preferred/other).
    top = _balance_by_type(
        candidates,
        top_k,
        sightseeing_ratio=sightseeing_ratio,
        preferred_types=preferred_types,
    )

    enriched_count = 0
    if enrich_descriptions and top:
        enriched_count = _enrich_descriptions(top, loc_name)

    for a in top:
        a.pop("_quality", None)

    output_path: Optional[Path] = None
    if persist and top:
        PROCESSED_DIR.mkdir(exist_ok=True)
        output_path = PROCESSED_DIR / f"{loc_id}.json"
        output_path.write_text(
            json.dumps(top, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    n_sight_out = sum(1 for a in top if _is_sightseeing(a))
    result = {
        "location_id": loc_id,
        "activities":  top,
        "stats": {
            "raw":                   retrieved["total_activities"],
            "after_has_required":    n_after_has_req,
            "after_anchor_drop":     n_after_anchor_drop,
            "after_name_dedupe":     n_after_name_dedupe,
            "output":                len(top),
            "output_sightseeing":    n_sight_out,
            "output_activity":       len(top) - n_sight_out,
            "descriptions_enriched": enriched_count,
        },
        "elapsed_s":   retrieved["total_elapsed_s"],
        "output_path": str(output_path) if output_path else None,
    }

    logger.info(
        "process_activities loc=%s: %d raw → %d req → %d anchor-drop → %d name-dedupe → %d out "
        "(%d sight / %d act, %d enriched)",
        loc_id, retrieved["total_activities"], n_after_has_req, n_after_anchor_drop,
        n_after_name_dedupe, len(top), n_sight_out, len(top) - n_sight_out, enriched_count,
    )

    return result


__all__ = ["process_activities", "PROCESSED_DIR"]
