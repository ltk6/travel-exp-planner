"""
N13 Wikidata (SPARQL) normalizer.

Raw shape (per binding):
    {
        "place":            {"type": "uri", "value": "http://www.wikidata.org/entity/Qxxx"},
        "placeLabel":       {"xml:lang": "en", "value": str},
        "location":         {"value": "Point(lng lat)"},                # WKT
        "description":      {"xml:lang": "en", "value": str},           # optional
        "image":            {"type": "uri", "value": str},              # optional
        "article":          {"value": "https://en.wikipedia.org/..."},  # optional
        "instance_of":      {"type": "uri", "value": "http://www.wikidata.org/entity/Qxxx"},  # P31, optional
        "instance_ofLabel": {"xml:lang": "en", "value": str}            # optional
    }

P31 → activity_type:
- Bảng `_P31_TO_ACTIVITY_TYPE` ánh xạ instance_of Q-ID sang taxonomy 7-class.
- Một place có thể có nhiều P31 → SPARQL trả nhiều rows; `normalize_all` dedupe theo entity Q-ID.
- Cache cũ (trước upgrade) không có P31 → fallback "culture" để giữ tương thích ngược.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from ..schema import build_activity


# Regex parse WKT Point: "Point(103.892628 22.300283)"
_WKT_POINT_RE = re.compile(r"Point\(\s*([\-0-9.]+)\s+([\-0-9.]+)\s*\)")


# Wikidata P31 (instance of) Q-ID → 7-class activity_type.
# Có thể mở rộng dần. Q-ID không có trong bảng → fallback "culture".
_P31_TO_ACTIVITY_TYPE: Dict[str, str] = {
    # ─── nature ──────────────────────────────────────────────
    "Q23397":   "nature",  # lake
    "Q8502":    "nature",  # mountain
    "Q34038":   "nature",  # waterfall
    "Q4022":    "nature",  # river
    "Q11451":   "nature",  # forest
    "Q22698":   "nature",  # urban park
    "Q170321":  "nature",  # national park
    "Q40080":   "nature",  # beach
    "Q207326":  "nature",  # cave
    "Q39594":   "nature",  # cliff
    "Q39816":   "nature",  # valley
    "Q12567":   "nature",  # volcano
    "Q23442":   "nature",  # island
    "Q1107656": "nature",  # garden
    "Q9430":    "nature",  # ocean
    "Q165":     "nature",  # sea
    "Q43229":   "nature",  # nature reserve
    "Q46831":   "nature",  # mountain range
    "Q150784":  "nature",  # strait
    "Q124714":  "nature",  # bay

    # ─── culture ─────────────────────────────────────────────
    "Q33506":    "culture",  # museum
    "Q24398318": "culture",  # religious building
    "Q44539":    "culture",  # temple
    "Q16970":    "culture",  # church building
    "Q32815":    "culture",  # mosque
    "Q4989906":  "culture",  # monument
    "Q1369832":  "culture",  # castle
    "Q35112127": "culture",  # pagoda
    "Q207694":   "culture",  # art museum
    "Q570116":   "culture",  # tourist attraction
    "Q839954":   "culture",  # archaeological site
    "Q49653":    "culture",  # palace
    "Q12876":    "culture",  # tower
    "Q12280":    "culture",  # bridge
    "Q23413":    "culture",  # castle
    "Q1497375":  "culture",  # public art

    # ─── food (rare in Wikidata) ─────────────────────────────
    "Q11707":  "food",      # restaurant
    "Q30022":  "food",      # cafe

    # ─── nightlife ───────────────────────────────────────────
    "Q187456": "nightlife", # bar
    "Q622425": "nightlife", # nightclub

    # ─── shopping ────────────────────────────────────────────
    "Q11315":  "shopping",  # shopping mall
    "Q330284": "shopping",  # marketplace

    # ─── relaxation ──────────────────────────────────────────
    "Q27686":   "relaxation", # hotel
    "Q3014511": "relaxation", # resort
    "Q179700":  "relaxation", # spa

    # ─── adventure ───────────────────────────────────────────
    "Q194195":  "adventure",  # amusement park
    "Q1076486": "adventure",  # ski resort
}


def _parse_wkt_point(wkt: Optional[str]) -> Optional[Dict[str, float]]:
    if not wkt:
        return None
    m = _WKT_POINT_RE.search(wkt)
    if not m:
        return None
    lng, lat = float(m.group(1)), float(m.group(2))
    return {"lat": lat, "lng": lng}


def _entity_id_from_uri(uri: Optional[str]) -> Optional[str]:
    if not uri:
        return None
    # http://www.wikidata.org/entity/Q123 → Q123
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _val(field: Optional[Dict[str, Any]]) -> Optional[str]:
    """Lấy .value từ một SPARQL binding cell."""
    if not isinstance(field, dict):
        return None
    return field.get("value")


def _map_p31_to_activity_type(p31_qid: Optional[str]) -> Optional[str]:
    """Map P31 Q-ID → activity_type. Trả về None nếu không có hoặc không khớp."""
    if not p31_qid:
        return None
    return _P31_TO_ACTIVITY_TYPE.get(p31_qid)


def normalize(raw_item: Dict[str, Any], ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    place_uri = _val(raw_item.get("place"))
    name = _val(raw_item.get("placeLabel"))
    if not name:
        return None

    entity_id = _entity_id_from_uri(place_uri)
    coords = _parse_wkt_point(_val(raw_item.get("location")))
    description = _val(raw_item.get("description"))
    image = _val(raw_item.get("image"))
    article = _val(raw_item.get("article"))

    # P31 mapping; fallback "culture" cho cache cũ (không có P31) hoặc Q-ID lạ.
    p31_qid = _entity_id_from_uri(_val(raw_item.get("instance_of")))
    p31_label = _val(raw_item.get("instance_ofLabel"))
    mapped_type = _map_p31_to_activity_type(p31_qid)
    activity_type = mapped_type or "culture"

    return build_activity(
        source="wikidata",
        location_id=ctx["location_id"],
        raw_source_id=entity_id,
        name=name,
        description=description,
        activity_type=activity_type,
        activity_subtype=p31_label,  # human-readable "lake", "museum", ...
        categories_raw=[p31_label] if p31_label else [],
        coordinates=coords,
        address={
            "country": None, "region": None, "city": None,
            "street": None, "formatted": None,
        },
        image_url=image,
        website=article,
        source_url=place_uri,
        raw=raw_item,
        anchor_lat=ctx.get("anchor_lat"),
        anchor_lng=ctx.get("anchor_lng"),
    )


def normalize_all(raw_items: List[Dict[str, Any]], ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize + dedupe theo entity Q-ID. Vì SPARQL với P31 có thể trả nhiều rows
    cho cùng 1 place (multiple instance_of values), ưu tiên giữ row có P31 map
    được sang taxonomy; nếu tất cả không map được thì giữ row đầu (fallback culture).
    """
    # qid → (normalized_dict, is_p31_mapped)
    by_id: Dict[str, tuple] = {}

    for it in raw_items:
        norm = normalize(it, ctx)
        if norm is None:
            continue
        qid = norm["provenance"]["raw_source_id"] or norm["activity_id"]

        p31_qid = _entity_id_from_uri(_val(it.get("instance_of")))
        is_mapped = _map_p31_to_activity_type(p31_qid) is not None

        if qid not in by_id:
            by_id[qid] = (norm, is_mapped)
            continue

        # Chỉ thay thế nếu entry cũ là fallback (chưa map được) còn entry mới map được.
        _, existing_mapped = by_id[qid]
        if not existing_mapped and is_mapped:
            by_id[qid] = (norm, is_mapped)

    return [v[0] for v in by_id.values()]
