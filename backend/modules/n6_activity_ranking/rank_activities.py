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

import hashlib
import math
from typing import Any, Dict, List, Optional

from backend.shared.weights import get_weights
from .preferences import infer_user_preferences

# Trọng số top-level
W_SEMANTIC = 0.5
W_ATTRIBUTE = 0.5


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


def _attribute_score(
    metadata: Dict,
    user_prefs: Dict[str, Optional[float]],
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
    "nature":      ["Khám phá cảnh quan tuyệt đẹp", "Hòa mình vào thiên nhiên {intensity_hint}đậm chất địa phương"],
    "adventure":   ["Thử thách bản thân với hoạt động {intensity_hint}đầy phấn khích", "Trải nghiệm cảm giác mạnh {intensity_hint}giữa thiên nhiên"],
    "food":        ["Thưởng thức tinh túy ẩm thực đặc trưng", "Khám phá hương vị địa phương độc đáo"],
    "culture":     ["Tìm hiểu chiều sâu văn hóa bản địa", "Trải nghiệm di sản và phong tục truyền thống"],
    "relaxation":  ["Phút giây thư giãn nhẹ nhàng", "Tìm lại sự cân bằng trong không gian yên bình"],
    "nightlife":   ["Sôi động và lung linh về đêm", "Khám phá nhịp sống về đêm đầy sắc màu"],
    "shopping":    ["Săn tìm những món quà lưu niệm độc bản", "Ghé thăm không gian mua sắm đậm chất địa phương"],
    "photography": ["Ghi lại những khoảnh khắc {intensity_hint}tuyệt đẹp", "Lưu giữ kỷ niệm qua những khung hình nghệ thuật"],
    "experience":  ["Kết nối sâu sắc với nhịp sống địa phương", "Trải nghiệm thực tế {intensity_hint}đầy chân thực và gần gũi"],
}
_REASON_DEFAULT = ["Lựa chọn tuyệt vời cho hành trình của bạn", "Trải nghiệm thú vị không nên bỏ lỡ"]

_INTENSITY_LABELS = [(0.7, "mạnh mẽ"), (0.4, "vừa sức"), (0.0, "nhẹ nhàng")]


def _pick(labels, value):
    for threshold, label in labels:
        if value >= threshold:
            return label
    return labels[-1][1]


def _build_reason(metadata: Dict, sem_score: float, attr_score: float) -> str:
    activity_type  = metadata.get("activity_type", "nature")
    name_act       = metadata.get("name", "Trải nghiệm")
    intensity      = float(metadata.get("intensity") or 0.5)
    intensity_hint = _pick(_INTENSITY_LABELS, intensity) + " "

    templates = _REASON_BY_TYPE.get(activity_type, _REASON_DEFAULT)
    idx = int(hashlib.md5(name_act.encode()).hexdigest(), 16) % len(templates)
    body = templates[idx].format(intensity_hint=intensity_hint)

    highlights = []
    if attr_score >= 0.8:
        highlights.append("rất hợp sở thích")
    if sem_score >= 0.8:
        highlights.append("đúng ý bạn tìm")

    suffix = f" ({', '.join(highlights)})" if highlights else ""
    return f"{body}{suffix}."


# =============================================================================
# ENTRY POINT
# =============================================================================

def rank_activities(data: Dict) -> Dict:
    import time
    t0 = time.time()
    user_input   = data.get("user_input", {}) or {}
    user_vectors = data.get("user_vectors", {}) or {}
    context      = data.get("context", {}) or {}
    activities   = data.get("activities", []) or []
    top_k        = int(data.get("top_k", 5))
    text_k       = int(data.get("text_k", 0))
    tags_k       = int(data.get("tags_k", 0))

    if not activities or top_k <= 0:
        return {"activities": [], "metadata": {"latency_ms": 0}}

    user_prefs = infer_user_preferences(user_input)
    weights = get_weights(text_k, tags_k)

    scored: List[Dict] = []
    for activity in activities:
        metadata = activity.get("metadata", {}) or {}
        vectors  = activity.get("vectors", {}) or {}

        sem_score = _semantic_score(user_vectors, vectors, text_k, tags_k)
        # Kéo khỏi dead-zone [0.5, 1.0] cho embeddings cùng domain
        sem_scaled = max(0.0, min(1.0, (sem_score - 0.5) * 2.0))

        attr_score = _attribute_score(metadata, user_prefs)

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
                a["score"] = round(max(0.0, min(1.0, norm)), 4)
        else:
            # Tight cluster — trải đều từ HIGH xuống LOW, clamp trong [0,1]
            n = len(scored)
            step = (HIGH - LOW) / (n - 1) if n > 1 else 0.0
            for i, a in enumerate(scored):
                a["score"] = round(max(0.0, min(1.0, HIGH - i * step)), 4)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "activities": scored[:top_k], 
        "metadata": {
            "user_prefs": user_prefs,
            "weights": weights,
            "text_k": text_k,
            "tags_k": tags_k,
            "latency_ms": elapsed_ms
        }
    }
