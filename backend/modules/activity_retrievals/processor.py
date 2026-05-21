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


# Field completeness weights for quality score (sum normalized to 1.0).
# description + tags được ưu tiên cao nhất — đây là 2 trường quyết định
# việc activity có hiển thị đẹp cho người dùng cuối hay không.
_QUALITY_WEIGHTS_META = {
    "description":        3.0,
    "tags":               2.0,
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
        v = md.get(field)
        if field == "tags":
            # Tags có thể nằm ở metadata.tags hoặc metadata.categories_raw
            if (v and len(v) > 0) or (md.get("categories_raw") and len(md["categories_raw"]) > 0):
                score += weight
        elif field == "description":
            if v and str(v).strip():
                score += weight
        else:
            if v is not None:
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


# Latin diacritics KHÔNG có trong alphabet tiếng Việt — xuất hiện ở giữa text
# tiếng Việt → mojibake (UTF-8 bị decode sai thành Latin-1/Windows-1252 rồi
# encode lại). Loại trừ ï (xuất hiện trong tên Pháp "Hanoï" hợp lệ).
_MOJIBAKE_CHARS_RE = re.compile(r"[ÄËÖÜØÆŒäëöüø]")


def _looks_like_mojibake(text: str) -> bool:
    """True khi text chứa ký tự Latin không-thuộc-Việt giữa context tiếng Việt."""
    if not text:
        return False
    return bool(_MOJIBAKE_CHARS_RE.search(text))


def _fix_mojibake_names(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Recover hoặc drop activities có name mojibake.

    Strategy:
      - Nếu `name` có mojibake VÀ `name_original` sạch → restore name = name_original
      - Nếu cả hai đều mojibake hoặc thiếu name_original → drop row

    Mojibake thường phát sinh khi LLM enrich vô tình re-encode tên (xem
    geoapify_loc_224_b02c4a: "KHU DU LÌCH VÉN THIÜN VI DIÜ THưC" được restore
    về "KHU DU LỊCH VƯỜN THIỀN VI DIỆU THỨC").
    """
    out = []
    restored = 0
    dropped = 0
    for a in activities:
        md = a.get("metadata") or {}
        name = md.get("name") or ""
        if not _looks_like_mojibake(name):
            out.append(a)
            continue
        orig = (md.get("name_original") or "").strip()
        if orig and not _looks_like_mojibake(orig):
            md["name"] = orig
            a["metadata"] = md
            restored += 1
            out.append(a)
        else:
            dropped += 1
    if restored or dropped:
        logger.info(
            "Mojibake repair: %d restored from name_original, %d dropped (no clean source)",
            restored, dropped,
        )
    return out


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


# =============================================================================
# TAG ONTOLOGY (shared/maps/tags.py) — controlled vocabulary cho aug_tags
# =============================================================================

def _allowed_tag_keys() -> List[str]:
    """Lazy import + cache để tránh circular + tránh nhập sai trong test."""
    from backend.shared.maps.tags import ALL_TAGS
    return list(ALL_TAGS.keys())


def _filter_tags(raw_tags: Any) -> List[str]:
    """
    Snap raw tags về controlled vocab. Hai bước:
      1. Exact match (case-insensitive, whitespace-trim).
      2. Fuzzy: nếu raw tag là substring của vocab key hoặc vocab key là
         substring của raw → match. VD "vietnamese food" → "local cuisine"
         không match (khác), nhưng "rice terraces" → "rice terrace" ✓ (plural).
    """
    if not isinstance(raw_tags, list):
        return []
    allowed = {k.lower(): k for k in _allowed_tag_keys()}
    out: List[str] = []
    seen: set = set()

    def add(key_canonical: str) -> None:
        if key_canonical not in seen:
            seen.add(key_canonical)
            out.append(key_canonical)

    for t in raw_tags:
        if not isinstance(t, str):
            continue
        key = re.sub(r"\s+", " ", t.strip().lower())
        if not key:
            continue
        # 1. Exact match.
        if key in allowed:
            add(allowed[key]); continue
        # 2. Plural stem.
        stem = key[:-1] if (len(key) > 4 and key.endswith("s") and not key.endswith("ss")) else None
        if stem and stem in allowed:
            add(allowed[stem]); continue
        # 3. Substring (tight): chỉ match khi 1 vế chứa hết vế kia với delta ≤ 5 chars.
        #    Tránh "shop"⊂"shopping" → cho match; nhưng "bar"⊄"rooftop bar" để tránh
        #    over-match. Yêu cầu vocab_key chứa raw_key (chứ không ngược) để giảm sai.
        for ak, av in allowed.items():
            if key == ak:
                add(av); break
            if key in ak and (len(ak) - len(key)) <= 5:
                add(av); break
    return out


# =============================================================================
# VIETNAMESE LANGUAGE DETECTION
# =============================================================================

# Diacritic letters & đ — strong VN signal. Other Latin-only text could be EN,
# VN-without-tones, brand names, etc. — we check ratio thay vì cứ thấy 1 dấu là VN.
_VIETNAMESE_DIACRITICS_RE = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ]",
    re.IGNORECASE,
)
# Vietnamese-specific function words (case-insensitive, word-bounded).
_VN_WORDS = (
    "của", "và", "ở", "tại", "ngắm", "dạo", "thưởng", "khám phá", "trải nghiệm",
    "chùa", "đền", "nhà", "vườn", "núi", "biển", "đảo", "vịnh", "hồ", "thác",
    "phố", "đường", "cầu", "đồi", "ruộng", "bản",
)


def _vietnamese_score(text: str) -> float:
    """0.0–1.0: tỉ lệ token có dấu hoặc thuộc từ điển VN ngắn."""
    if not text:
        return 0.0
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    if not tokens:
        return 0.0
    vn_hits = 0
    for tok in tokens:
        if _VIETNAMESE_DIACRITICS_RE.search(tok):
            vn_hits += 1
            continue
        low = tok.lower()
        if low in _VN_WORDS:
            vn_hits += 1
    return vn_hits / len(tokens)


def _is_vietnamese_primary(text: str, threshold: float = 0.20) -> bool:
    """True nếu text "đủ Việt": ≥ threshold token có dấu hoặc thuộc từ VN."""
    if not text:
        return False
    # Single-word brand/POI name có thể không có dấu → cho phép nếu tổng tokens < 3.
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    if len(tokens) <= 2:
        # Cho qua nếu tối thiểu có dấu trên text, OR có khả năng là tên riêng VN
        return bool(_VIETNAMESE_DIACRITICS_RE.search(text)) or len(tokens) == 0
    return _vietnamese_score(text) >= threshold


# =============================================================================
# ENRICHMENT — chunked LLM call (compound: web search grounding)
# =============================================================================

# Chunk nhỏ để mỗi call JSON output không bị truncate. Trade-off:
#   - càng nhỏ → càng nhiều round-trip nhưng JSON parse ổn định
#   - groq/compound free-tier có input/output cap chặt → giữ 8 POI/chunk.
_ENRICH_CHUNK_SIZE = 8


_ENRICH_RULES_COMMON = (
    "Bạn là chuyên gia du lịch Việt Nam. Dùng Google Search khi cần xác minh.\n"
    "QUY TẮC name (5-10 từ tiếng Việt thuần):\n"
    " - Bắt đầu bằng động từ trải nghiệm: Khám phá / Thưởng thức / Ngắm / Trải nghiệm / "
    "Chinh phục / Dạo bộ / Check-in / Vãn cảnh / Tham quan.\n"
    " - Việt hoá từ chung Anh→Việt: Bay→Vịnh, Island→Đảo, Park→Công viên, "
    "Restaurant→Nhà hàng, Cafe→Quán cà phê, Museum→Bảo tàng, Bridge→Cầu, "
    "Temple→Đền/Chùa, Beach→Bãi/Biển, Mountain→Núi, Waterfall→Thác, "
    "Cave→Hang/Động, Lake→Hồ, Market→Chợ.\n"
    " - Giữ tên riêng đúng chính tả VN.\n"
    "QUY TẮC description (1-2 câu tiếng Việt, súc tích, KHÔNG sáo rỗng, KHÔNG lặp tên).\n"
    "QUY TẮC at_anchor: true nếu POI nằm TRONG cùng khu vực/thành phố của anchor "
    "HOẶC là sub-experience hợp lý cho khách thăm anchor "
    "(vd: nhà hàng trong Nha Trang vẫn at_anchor=true cho 'Vịnh Nha Trang'). "
    "false CHỈ khi POI ở thành phố/tỉnh khác hẳn (vd: quán ở Đà Nẵng cho anchor 'Vịnh Nha Trang').\n"
    "CHỈ trả về JSON array, KHÔNG markdown, KHÔNG giải thích."
)


# Curated subset cho compound compact prompt — coverage rộng cho seed locations
# (mountain/beach/city/heritage/food) trong khi giữ system prompt nhỏ. Tag chính
# xác từ ALL_TAGS keys → _filter_tags() sẽ exact-match.
_COMPOUND_TAG_HINTS = (
    "mountain hill karst valley cave waterfall beach bay island lake river "
    "national park forest pine forest cool climate tropical history war history "
    "colonial heritage royal tomb cham culture temple pagoda church ethnic minority "
    "festival UNESCO heritage city old town village fishing village market "
    "night market floating market trekking hiking motorbiking cycling caving "
    "camping cable car paragliding scuba diving snorkeling kayaking surfing "
    "kitesurfing boat cruise river cruise mud bath swimming spa cooking class "
    "pottery class farm tour tea tasting coffee tour theme park photography "
    "shopping street food local cuisine fine dining food tour seafood vegetarian "
    "coffee tropical fruit peaceful vibrant chill romantic mysterious nostalgic "
    "rustic picturesque instagrammable adventure off the beaten path authentic "
    "day trip weekend trip solo couple honeymoon family group friends trip "
    "budget mid range luxury boutique homestay eco lodge resort glamping "
    "eco travel agro tourism religious tourism nightlife"
)


def _build_enrich_system(tag_keys: List[str], compact: bool = False) -> str:
    """System prompt — full version includes tag vocab; compact uses curated subset.

    Tag enforcement runs post-call qua _filter_tags() bất kể compact hay không.
    """
    if compact:
        # Compound free-tier cap → dùng curated 80-tag subset (~400 chars).
        return _ENRICH_RULES_COMMON + (
            "\nTAGS hợp lệ — CHỈ chọn 3-8 tag từ list này (exact lowercase):\n"
            + _COMPOUND_TAG_HINTS
        )
    return _ENRICH_RULES_COMMON + (
        "\nTAGS hợp lệ (CHỈ chọn từ list này, lowercase chính xác):\n"
        + ", ".join(tag_keys)
    )


def _build_enrich_prompt(
    targets: List[Dict[str, Any]],
    location_name: str,
    tag_keys: List[str],  # giữ signature backward-compat (tag_keys giờ vào system)
) -> str:
    items_str = "\n".join(
        f'{i+1}. "{a["metadata"].get("name","")}" '
        f'(type={a["metadata"].get("activity_type","?")}, '
        f'dist={int(a["place"].get("distance_from_anchor_m") or 0)}m)'
        for i, a in enumerate(targets)
    )
    return (
        f'Anchor: "{location_name}". Với MỖI POI dưới đây, trả về 1 object:\n'
        f'{{"index":N,"name":"...","description":"...","tags":[3-8 tag],'
        f'"at_anchor":bool,"confidence":0.0-1.0}}\n'
        f"Output: JSON array đúng {len(targets)} phần tử, đúng thứ tự index 1..{len(targets)}.\n\n"
        f"POI:\n{items_str}"
    )


def _parse_enrich_response(text: str, expected_n: int) -> List[Dict[str, Any]]:
    """Tolerant JSON parse: strip code fences, extract first array if response is mixed."""
    if not text:
        return []
    s = text.strip()
    if s.startswith("```"):
        inner = s.split("```", 2)
        if len(inner) >= 2:
            s = inner[1].lstrip("json").strip().rstrip("`").strip()
    # Compound đôi khi prepend text dạng "<think>...</think>\n[...]" hoặc tool log.
    # Bắt đoạn JSON array đầu tiên.
    if not s.startswith("["):
        m = re.search(r"\[\s*\{.*\}\s*\]", s, flags=re.DOTALL)
        if m:
            s = m.group(0)
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError as e:
        logger.warning("enrich JSON decode failed: %s — text=%r", e, text[:240])
        return []

    if isinstance(parsed, dict):
        # Nếu model wrap mảng trong "items"/"results"/...
        list_vals = [v for v in parsed.values() if isinstance(v, list)]
        if len(list_vals) == 1:
            parsed = list_vals[0]

    if not isinstance(parsed, list):
        logger.warning("enrich expected list, got %s", type(parsed).__name__)
        return []

    items: List[Dict[str, Any]] = []
    for i, it in enumerate(parsed):
        if not isinstance(it, dict):
            continue
        try:
            idx = int(it.get("index", i + 1)) - 1
        except (TypeError, ValueError):
            idx = i
        items.append({
            "idx":         idx,
            "name":        (it.get("name") or "").strip(),
            "desc":        (it.get("description") or "").strip(),
            "tags":        it.get("tags") or [],
            "at_anchor":   bool(it.get("at_anchor", True)),
            "confidence":  float(it.get("confidence") or 0.7),
        })
    return items


def _enrich_chunk(
    chain: List[Any],
    chunk: List[Dict[str, Any]],
    location_name: str,
    tag_keys: List[str],
) -> int:
    """1 chunk → 1 LLM call. Mutate activity in-place. Return số POI đã enrich."""
    prompt = _build_enrich_prompt(chunk, location_name, tag_keys)
    for provider in chain:
        # Compound free-tier có cap chặt → dùng system prompt compact (không tag list)
        # và max_tokens nhỏ. Các model khác (70b, ...) chấp nhận full vocab inline.
        is_compound = getattr(provider, "model", "").startswith("groq/compound")
        system = _build_enrich_system(tag_keys, compact=is_compound)
        max_tokens = 1200 if is_compound else 2000
        try:
            text = provider.generate(
                prompt,
                system=system,
                retries=0,
                temperature=0.4,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning("Provider %s raised: %s", getattr(provider, "name", "?"), e)
            continue
        if not text:
            continue
        items = _parse_enrich_response(text, expected_n=len(chunk))
        if not items:
            continue

        # Default tags=[] cho mọi item — tránh tags=None khi LLM skip index.
        for a in chunk:
            md = a["metadata"]
            if md.get("tags") is None:
                md["tags"] = []

        count = 0
        for it in items:
            idx = it["idx"]
            if not (0 <= idx < len(chunk)):
                continue
            md = chunk[idx]["metadata"]
            if it["name"]:
                md["name_original"] = md.get("name")
                md["name"] = it["name"]
            if it["desc"]:
                md["description"] = it["desc"]
            md["tags"] = _filter_tags(it["tags"])
            chunk[idx]["_at_anchor"]  = it["at_anchor"]
            chunk[idx]["_confidence"] = it["confidence"]
            count += 1
        logger.info(
            "enrich chunk: %d/%d via %s (model=%s)",
            count, len(chunk), provider.name, getattr(provider, "model", "?"),
        )
        return count
    return 0


def _enrich_descriptions(
    activities: List[Dict[str, Any]],
    location_name: str,
) -> int:
    """
    Enrich tất cả activities tại 1 anchor:
      - Rewrite name (tiếng Việt thuần, prefix động từ trải nghiệm)
      - Generate description (1-2 câu tiếng Việt)
      - Gán tags từ vocab kiểm soát (shared/maps/tags.py)
      - Đánh dấu _at_anchor & _confidence cho downstream filter

    Chia thành chunk _ENRICH_CHUNK_SIZE để mỗi call JSON output không truncate
    (đã thấy `enrich: 71/120` khi 1-shot). Compound model có web-search → kết
    quả tên VN chính xác + at_anchor reliable hơn.

    Trả về tổng số activities đã enrich (≤ len(activities)).
    """
    if not activities:
        return 0

    try:
        from backend.modules.n5_activity_generation.providers import get_llm_chain
        from backend.modules.n5_activity_generation.providers.registry import _instance
    except ImportError as e:
        logger.warning("N5 providers unavailable, skip enrich: %s", e)
        return 0

    # Ưu tiên compound (web-search grounded) ngay đầu chain — fallback sang
    # config.LLM_CHAIN nếu compound không trả về JSON hợp lệ.
    chain: List[Any] = []
    compound = _instance("groq_compound")
    if compound and compound.is_available():
        chain.append(compound)
    chain.extend(get_llm_chain())
    if not chain:
        logger.warning("No LLM provider configured, skip enrich")
        return 0

    tag_keys = _allowed_tag_keys()
    total = 0
    for start in range(0, len(activities), _ENRICH_CHUNK_SIZE):
        chunk = activities[start:start + _ENRICH_CHUNK_SIZE]
        total += _enrich_chunk(chain, chunk, location_name, tag_keys)
    logger.info(
        "enrich done: %d/%d activities at anchor=%s",
        total, len(activities), location_name,
    )
    return total


# =============================================================================
# POST-ENRICH FILTERS
# =============================================================================

def drop_off_anchor(
    activities: List[Dict[str, Any]],
    min_confidence: float = 0.75,
) -> List[Dict[str, Any]]:
    """
    Bỏ activity mà LLM (sau khi tra web với compound) đánh dấu KHÔNG nằm
    tại anchor location. Chỉ drop khi confidence đủ cao — tránh ăn nhầm
    do hallucinate.
    """
    out: List[Dict[str, Any]] = []
    dropped = 0
    for a in activities:
        at_anchor  = a.get("_at_anchor", True)
        confidence = a.get("_confidence", 0.5)
        if (not at_anchor) and confidence >= min_confidence:
            dropped += 1
            continue
        out.append(a)
    if dropped:
        logger.info("Dropped %d off-anchor activities (confidence ≥ %.2f)", dropped, min_confidence)
    return out


def drop_non_vietnamese(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sau khi LLM rewrite, name+description phải là tiếng Việt là chính. Nếu cả 2
    fail _is_vietnamese_primary → drop. Bảo vệ DB seed khỏi rò rỉ tên thuần Anh.
    """
    out: List[Dict[str, Any]] = []
    dropped = 0
    for a in activities:
        md = a.get("metadata") or {}
        name = md.get("name") or ""
        desc = md.get("description") or ""
        if _is_vietnamese_primary(name) or _is_vietnamese_primary(desc):
            out.append(a)
        else:
            dropped += 1
    if dropped:
        logger.info("Dropped %d non-Vietnamese activities post-enrich", dropped)
    return out


# =============================================================================
# DISTANCE FILTER — "phải ở địa điểm đó", không chỉ "gần đó"
# =============================================================================

def filter_by_distance(
    activities: List[Dict[str, Any]],
    max_distance_m: float = 8000.0,
) -> List[Dict[str, Any]]:
    """
    Drop activity có distance_from_anchor_m > max_distance_m. Default 8km — đủ
    cover các city-level anchor (Nha Trang, Đà Lạt) nhưng vẫn loại các điểm
    cách xa hẳn không thuộc anchor.

    POI không có distance (null) → giữ lại (đã pass _has_required → có coords).
    """
    out: List[Dict[str, Any]] = []
    dropped = 0
    for a in activities:
        dist = (a.get("place") or {}).get("distance_from_anchor_m")
        if dist is not None and dist > max_distance_m:
            dropped += 1
            continue
        out.append(a)
    if dropped:
        logger.info("Dropped %d activities further than %.0fm from anchor", dropped, max_distance_m)
    return out


# =============================================================================
# DEDUP — cross-language + translation-aware (dùng dedup.normalize_name)
# =============================================================================

def _dedupe_aggressive(activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tăng cường dedup: kết hợp:
      1. normalize_name (translation-aware) → bắt "Golden Bridge" ≡ "Cầu Vàng"
      2. coord bucket 3 chữ số thập phân (~110m precision)
      3. (normalized_core, activity_type) bucket — POI cùng tên loại + cùng type

    Giữ entry đầu tiên (input đã sort theo quality desc).
    """
    try:
        from .dedup import normalize_name
    except ImportError:
        normalize_name = _normalize_name  # type: ignore

    seen_names: set = set()
    seen_coords: set = set()
    seen_pairs: set = set()
    out: List[Dict[str, Any]] = []
    dropped = 0
    for a in activities:
        md = a.get("metadata") or {}
        place = a.get("place") or {}
        raw_name = md.get("name") or ""
        norm = normalize_name(raw_name)
        core = _core_name(raw_name)

        coords = place.get("coordinates") or {}
        ckey = None
        if coords.get("lat") is not None and coords.get("lng") is not None:
            ckey = (round(coords["lat"], 3), round(coords["lng"], 3))

        pair_key = (core, md.get("activity_type")) if core else None

        if norm and norm in seen_names:
            dropped += 1; continue
        if ckey and ckey in seen_coords:
            dropped += 1; continue
        if pair_key and pair_key in seen_pairs:
            dropped += 1; continue

        if norm:      seen_names.add(norm)
        if ckey:      seen_coords.add(ckey)
        if pair_key:  seen_pairs.add(pair_key)
        out.append(a)
    if dropped:
        logger.info("Aggressive dedupe: %d → %d (-%d)", len(activities), len(out), dropped)
    return out


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

    # Strict distance — phải nằm TẠI anchor, không chỉ "gần đó".
    filtered = filter_by_distance(filtered, max_distance_m=8000.0)
    n_after_distance = len(filtered)

    # Score quality, sort
    for a in filtered:
        a["_quality"] = _quality_score(a)
    filtered.sort(key=_rank_key)

    # Aggressive dedupe (translation-aware + coord bucket + core-name pair)
    filtered = _dedupe_aggressive(filtered)
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
        top = drop_off_anchor(top)
        top = drop_non_vietnamese(top)

    for a in top:
        a.pop("_quality", None)
        a.pop("_at_anchor", None)
        a.pop("_confidence", None)

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
            "after_distance":        n_after_distance,
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
        "process_activities loc=%s: %d raw → %d req → %d anchor → %d dist → %d dedupe → %d out "
        "(%d sight / %d act, %d enriched)",
        loc_id, retrieved["total_activities"], n_after_has_req, n_after_anchor_drop,
        n_after_distance, n_after_name_dedupe, len(top), n_sight_out, len(top) - n_sight_out,
        enriched_count,
    )

    return result


__all__ = ["process_activities", "PROCESSED_DIR"]
