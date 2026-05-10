# =============================================================================
# rank_activities.py
# =============================================================================
# N6 — XẾP HẠNG HOẠT ĐỘNG DU LỊCH
#
# INPUT (contract mới):
#   user_input, user_vectors, text_k, tags_k, activities, top_k
#   context = { "time_of_day": str | None }
#
# CÔNG THỨC:
#   score = 0.5 * semantic_score  +  0.5 * attribute_score
#
#   - semantic_score:  cosine sim giữa user_vectors và activity vectors
#                      (reuse kiến trúc N4, kéo giãn khỏi dead-zone [0.5, 1.0])
#   - attribute_score: fit giữa preference user (suy luận từ tags+text)
#                      với metadata activity (intensity, physical_level,
#                      social_level) + time_of_day match
# =============================================================================

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from backend.shared.weights import get_weights
from .preferences import infer_user_preferences

# Trọng số top-level
W_SEMANTIC = 0.5
W_ATTRIBUTE = 0.5

# Trong attribute score: 3 trục preference + time_of_day. Chia đều 4 phần.
ATTR_AXIS_WEIGHT = 0.25  # mỗi axis trong {intensity, physical, social, tod}


# =============================================================================
# SEMANTIC SCORE — giữ nguyên thiết kế cũ
# =============================================================================

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Cosine similarity trong [-1, 1]; trả 0 nếu vector rỗng hoặc khác chiều."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = 0.0
    n1 = 0.0
    n2 = 0.0
    for a, b in zip(v1, v2):
        dot += a * b
        n1  += a * a
        n2  += b * b

    n1 = math.sqrt(n1)
    n2 = math.sqrt(n2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def _semantic_score(
    user_vectors: Dict,
    act_vectors: Dict,
    text_k: int = 0,
    tags_k: int = 0,
) -> float:
    """
    Điểm khớp ngữ nghĩa: weighted cosine giữa user vectors và activity vectors.
    Reuse `shared.weights.get_weights` để weights khớp N1/N4.
    """
    weights = get_weights(text_k, tags_k)

    channel_pairs = [
        ("aug_tags", "tag",  weights.get("aug_tags", 0.0)),
        ("aug_text", "text", weights.get("aug_text", 0.0)),
        ("text",     "text", weights.get("text",     0.0)),
    ]

    sum_score = 0.0
    total_weight = 0.0
    for ch_user, ch_act, w in channel_pairs:
        v_user = user_vectors.get(ch_user)
        v_act  = act_vectors.get(ch_act)
        if not v_user or not v_act:
            continue

        sim = cosine_similarity(v_user, v_act)
        normalized = (sim + 1.0) / 2.0           # [-1,1] → [0,1]
        sum_score   += normalized * w
        total_weight += w

    if total_weight == 0:
        return 0.5
    return sum_score / total_weight


# =============================================================================
# ATTRIBUTE SCORE — MỚI: khớp preference với metadata
# =============================================================================

def _axis_fit(user_pref: Optional[float], act_value: Optional[float]) -> Optional[float]:
    """
    Fit score cho 1 axis: càng gần nhau càng cao. Dùng 1 - |diff|.

    Return None nếu user không có preference (pref is None) hoặc activity thiếu
    metadata — caller sẽ skip axis này khỏi averaging để không phạt oan.
    """
    if user_pref is None or act_value is None:
        return None
    diff = abs(float(user_pref) - float(act_value))
    return max(0.0, 1.0 - diff)


def _tod_fit(tod_user: Optional[str], tod_act: Optional[str]) -> Optional[float]:
    """
    Khớp giờ trong ngày — giữ lại như helper dự phòng, KHÔNG dùng trong
    attribute score hiện tại (contract chỉ chấm 3 axis: intensity/physical/social).
    """
    if not tod_user or not tod_act:
        return None
    tu = tod_user.lower().strip()
    ta = tod_act.lower().strip()
    if ta == "anytime" or tu == ta:
        return 1.0
    return 0.3


def _attribute_score(
    metadata: Dict,
    user_prefs: Dict[str, Optional[float]],
    tod_user: Optional[str] = None,  # kept for call-site compat, unused
) -> float:
    """
    Điểm thuộc tính: trung bình fit của 3 axis intensity / physical / social.
    Axis nào thiếu user_pref hoặc metadata → bỏ qua khỏi averaging.
    Không axis nào có dữ liệu → trả 0.5 (neutral).
    """
    axis_fits: List[float] = []

    for axis, meta_key in [
        ("intensity", "intensity"),
        ("physical",  "physical_level"),
        ("social",    "social_level"),
    ]:
        fit = _axis_fit(user_prefs.get(axis), metadata.get(meta_key))
        if fit is not None:
            axis_fits.append(fit)

    if not axis_fits:
        return 0.5
    return sum(axis_fits) / len(axis_fits)


# =============================================================================
# REASON BUILDER — rút gọn, dùng thông tin mới
# =============================================================================

_REASON_BY_TYPE = {
    "nature":     ["Cảnh quan {location_hint}phù hợp sở thích của bạn", "Thiên nhiên {intensity_hint}đúng gu khám phá"],
    "adventure":  ["Thử thách {intensity_hint}cho người thích khám phá", "Hoạt động mạo hiểm {intensity_hint}đáng nhớ"],
    "food":       ["Ẩm thực địa phương — không thể bỏ qua", "Khẩu vị của bạn sẽ hài lòng với lựa chọn này"],
    "culture":    ["Chiều sâu văn hóa {location_hint}khác biệt hoàn toàn", "Trải nghiệm văn hóa độc đáo"],
    "relaxation": ["Thư giãn {time_hint}— đúng lúc cần nghỉ ngơi", "Nhịp điệu chậm, phù hợp người tìm yên tĩnh"],
    "nightlife":  ["Về đêm sẽ thú vị hơn với lựa chọn này", "Điểm nhấn cho buổi tối {location_hint}"],
    "shopping":   ["Mua sắm — quà lưu niệm ý nghĩa", "Tìm đồ địa phương độc đáo {location_hint}"],
}
_REASON_DEFAULT = ["Phù hợp với hành trình và sở thích của bạn", "Hoạt động đáng thử trong chuyến đi này"]

_INTENSITY_LABELS = [(0.7, "cường độ cao"), (0.4, "vừa sức"), (0.0, "nhẹ nhàng")]
_TIME_LABELS      = {"morning": "buổi sáng ", "afternoon": "buổi chiều ", "evening": "buổi tối "}


def _pick(labels, value):
    for threshold, label in labels:
        if value >= threshold:
            return label
    return labels[-1][1]


def _build_reason(metadata: Dict, sem_score: float, attr_score: float) -> str:
    activity_type = metadata.get("activity_type", "nature")
    name_act      = metadata.get("name", "Hoạt động này")
    intensity     = float(metadata.get("intensity") or 0.5)
    tod           = metadata.get("time_of_day_suitable", "anytime")
    indoor_out    = metadata.get("indoor_outdoor", "outdoor")

    intensity_hint = _pick(_INTENSITY_LABELS, intensity) + " "
    time_hint      = _TIME_LABELS.get(tod, "")
    location_hint  = "" if indoor_out == "indoor" else "ngoài trời "

    templates = _REASON_BY_TYPE.get(activity_type, _REASON_DEFAULT)
    idx = hash(name_act) % len(templates)
    body = templates[idx].format(
        intensity_hint=intensity_hint,
        time_hint=time_hint,
        location_hint=location_hint,
    )

    highlights = []
    if attr_score >= 0.75:
        highlights.append("hợp sở thích cá nhân")
    if sem_score >= 0.75:
        highlights.append("khớp mô tả của bạn")

    if highlights:
        return f"{name_act}: {body} ({', '.join(highlights)})."
    return f"{name_act}: {body}."


# =============================================================================
# ENTRY POINT
# =============================================================================

def rank_activities(data: Dict) -> Dict:
    """
    Xếp hạng activities theo công thức:
        score = 0.5 * semantic_score + 0.5 * attribute_score

    Input (đã rút gọn so với bản cũ):
        text_k, tags_k           — tín hiệu từ N1 cho weight dynamic
        user_input               — {text, img_desc, tags} dùng để suy preference
        user_vectors             — 4 kênh vector từ N1
        context.time_of_day      — dùng riêng cho attribute matching
        activities               — list từ N5 + N1 (đã embed)
        top_k

    Các field cũ (budget / duration / people / weather) đã bị loại bỏ hoàn toàn.
    """
    user_input   = data.get("user_input", {}) or {}
    user_vectors = data.get("user_vectors", {}) or {}
    context      = data.get("context", {}) or {}
    activities   = data.get("activities", []) or []
    top_k        = int(data.get("top_k", 5))
    text_k       = int(data.get("text_k", 0))
    tags_k       = int(data.get("tags_k", 0))

    if not activities or top_k <= 0:
        return {"activities": []}

    tod_user   = context.get("time_of_day")
    user_prefs = infer_user_preferences(user_input)

    scored: List[Dict] = []
    for activity in activities:
        metadata = activity.get("metadata", {}) or {}
        vectors  = activity.get("vectors", {}) or {}

        sem_score = _semantic_score(user_vectors, vectors, text_k, tags_k)
        # Kéo khỏi dead-zone [0.5, 1.0] cho embeddings cùng domain
        sem_scaled = max(0.0, min(1.0, (sem_score - 0.5) * 2.0))

        attr_score = _attribute_score(metadata, user_prefs, tod_user)

        total = W_SEMANTIC * sem_scaled + W_ATTRIBUTE * attr_score
        total = max(0.0, min(1.0, total))

        scored.append({
            "activity_id": activity.get("activity_id"),
            "location_id": activity.get("location_id"),
            "score":       round(total, 4),
            "reason":      _build_reason(metadata, sem_scaled, attr_score),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # Min-max spread [0.40, 1.0] để hiển thị dễ đọc, giữ nguyên thứ hạng
    if len(scored) >= 2:
        max_s = scored[0]["score"]
        min_s = scored[-1]["score"]
        spread = max_s - min_s
        LOW, HIGH = 0.40, 1.0
        if spread > 0.01:
            for a in scored:
                norm = LOW + (a["score"] - min_s) / spread * (HIGH - LOW)
                a["score"] = round(norm, 4)
        else:
            for i, a in enumerate(scored):
                a["score"] = round(0.75 - i * 0.05, 4)

    return {"activities": scored[:top_k], "user_prefs": user_prefs}
