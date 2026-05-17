# =============================================================================
# rank_activities.py (OPTIMIZED VERSION)
# =============================================================================
from __future__ import annotations

import hashlib
import math
import heapq
from typing import Any, Dict, List, Optional, Tuple

from backend.shared.weights import get_weights
from .preferences import infer_user_preferences

W_SEMANTIC = 0.5
W_ATTRIBUTE = 0.5

# =============================================================================
# SEMANTIC SCORE
# =============================================================================

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    # Tối ưu: Dùng list comprehension & sum built-in của C (nhanh hơn vòng lặp for thuần)
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)

def _semantic_score(
    user_vectors: Dict,
    act_vectors: Dict,
    weights: Dict[str, float]
) -> float:
    sum_score = 0.0
    total_weight = 0.0
    
    # Unroll vòng lặp để tránh overhead tạo list tuple
    for ch_user, ch_act, w_key in [("aug_tags", "tag", "aug_tags"), 
                                   ("aug_text", "text", "aug_text"), 
                                   ("text", "text", "text")]:
        w = weights.get(w_key, 0.0)
        if w == 0.0: continue
        
        v_user = user_vectors.get(ch_user)
        v_act = act_vectors.get(ch_act)
        
        if v_user and v_act:
            sim = cosine_similarity(v_user, v_act)
            normalized = (sim + 1.0) / 2.0
            sum_score += normalized * w
            total_weight += w

    return sum_score / total_weight if total_weight > 0 else 0.5

# =============================================================================
# ATTRIBUTE SCORE
# =============================================================================

def _attribute_score(metadata: Dict, user_prefs: Dict[str, Optional[float]]) -> float:
    axis_fits = []
    
    # Truy xuất trực tiếp, giảm thiểu các hàm gọi lồng nhau (function call overhead)
    for axis, meta_key in [("intensity", "intensity"), ("physical", "physical_level"), ("social", "social_level")]:
        u_pref = user_prefs.get(axis)
        m_val = metadata.get(meta_key)
        
        if u_pref is not None and m_val is not None:
            axis_fits.append(max(0.0, 1.0 - abs(float(u_pref) - float(m_val))))

    if not axis_fits:
        return 0.5
    return sum(axis_fits) / len(axis_fits)

# =============================================================================
# REASON BUILDER
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

def _build_reason(metadata: Dict, sem_score: float, attr_score: float) -> str:
    activity_type = metadata.get("activity_type", "nature")
    name_act = metadata.get("name", "Trải nghiệm")
    intensity = float(metadata.get("intensity") or 0.5)
    
    intensity_hint = next((label for threshold, label in _INTENSITY_LABELS if intensity >= threshold), "nhẹ nhàng") + " "

    templates = _REASON_BY_TYPE.get(activity_type, _REASON_DEFAULT)
    idx = int(hashlib.md5(name_act.encode()).hexdigest(), 16) % len(templates)
    body = templates[idx].format(intensity_hint=intensity_hint)

    highlights = []
    if attr_score >= 0.8: highlights.append("rất hợp sở thích")
    if sem_score >= 0.8:  highlights.append("đúng ý bạn tìm")

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
    activities   = data.get("activities", []) or []
    top_k        = int(data.get("top_k", 5))
    text_k       = int(data.get("text_k", 0))
    tags_k       = int(data.get("tags_k", 0))

    if not activities or top_k <= 0:
        return {"activities": [], "metadata": {"latency_ms": 0}}

    user_prefs = infer_user_preferences(user_input)
    weights = get_weights(text_k, tags_k)

    scored_heap = []
    
    # 1. TÍNH TOÁN & CHỌN LỌC NHANH (KHÔNG BUILD REASON Ở ĐÂY)
    for activity in activities:
        metadata = activity.get("metadata", {}) or {}
        vectors  = activity.get("vectors", {}) or {}

        sem_score = _semantic_score(user_vectors, vectors, weights)
        sem_scaled = max(0.0, min(1.0, (sem_score - 0.5) * 2.0))
        attr_score = _attribute_score(metadata, user_prefs)

        total = W_SEMANTIC * sem_scaled + W_ATTRIBUTE * attr_score
        total = max(0.0, min(1.0, total))

        # Đưa vào heap, giữ kích thước heap nhỏ gọn
        heap_item = (total, activity.get("activity_id"), activity.get("location_id"), metadata, sem_scaled, attr_score)
        
        if len(scored_heap) < top_k:
            heapq.heappush(scored_heap, heap_item)
        else:
            heapq.heappushpop(scored_heap, heap_item)

    # Lấy top K và sắp xếp giảm dần
    top_activities = sorted(scored_heap, key=lambda x: x[0], reverse=True)

    # 2. XỬ LÝ FORMAT & REASON (CHỈ ÁP DỤNG CHO TOP K)
    final_results = []
    if top_activities:
        max_s = top_activities[0][0]
        min_s = top_activities[-1][0]
        spread = max_s - min_s
        LOW, HIGH = 0.40, 1.0

        n = len(top_activities)
        step = (HIGH - LOW) / (n - 1) if n > 1 else 0.0

        for i, (score, act_id, loc_id, meta, sem, attr) in enumerate(top_activities):
            # Cân bằng điểm số (Min-Max Scaling)
            if spread > 0.01:
                norm_score = LOW + (score - min_s) / spread * (HIGH - LOW)
            else:
                norm_score = HIGH - i * step
            
            final_score = round(max(0.0, min(1.0, norm_score)), 4)

            # BÂY GIỜ MỚI BUILD REASON CHO 5-10 ITEMS NÀY
            final_results.append({
                "activity_id": act_id,
                "location_id": loc_id,
                "score": final_score,
                "reason": _build_reason(meta, sem, attr),
            })

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "activities": final_results, 
        "metadata": {
            "user_prefs": user_prefs,
            "weights": weights,
            "text_k": text_k,
            "tags_k": tags_k,
            "latency_ms": elapsed_ms
        }
    }