# =============================================================================
# rank_activities.py
# =============================================================================
# N6 - XẾP HẠNG HOẠT ĐỘNG DU LỊCH
#
# MỤC TIÊU:
#   Nhận danh sách hoạt động (đã được module N5 sinh ra), sau đó chấm điểm
#   từng hoạt động dựa trên sở thích người dùng + ràng buộc + ngữ cảnh,
#   cuối cùng trả về top_k hoạt động có điểm cao nhất.
#
# Ý TƯỞNG TỔNG QUÁT:
#   Mỗi hoạt động sẽ có 1 điểm tổng, tính từ 3 nhóm điểm con:
#
#       Điểm tổng = 0.5  * (Điểm khớp sở thích)
#                 + 0.25 * (Điểm phù hợp ràng buộc)
#                 + 0.25 * (Điểm phù hợp ngữ cảnh)
#
#   Trong đó:
#     - Điểm khớp sở thích: dùng cosine similarity giữa vector người dùng
#       và vector của hoạt động.
#     - Điểm ràng buộc: hoạt động có rẻ không? có vừa thời gian không?
#     - Điểm ngữ cảnh: có hợp giờ trong ngày không? có hợp thời tiết không?
#
#   Sau khi tính xong, sắp xếp giảm dần và lấy top_k.
# =============================================================================

import math   # dùng math.sqrt để tính cosine similarity

#=============================================================================
#DANH SÁCH CÁC HÀM PHỤ HỖ TRỢ
#=============================================================================

# Hàm 1: kiểm tra ràng buộc cứng

def hard_constraint_violated(metadata, constraints):
    """
    trả về True nếu hoạt động vi phạm ràng buộc cứng (bị loại).
    trả về False nếu hoạt động không vi phạm ràng buộc nào.

    hiện tại chỉ kiểm tra: thời gian hoạt động không vượt thời gian rảnh của user.
    """
    duration_user=constraints.get("duration")
    duration_act=metadata.get("estimated_duration")

    #nếu cả hai đều có giá trị và hoạt động dài hơn thời gian rảnh -> loại
    if duration_user is not None and duration_act is not None:
        if duration_act > duration_user:
            return True

    return False

from backend.shared.weights import get_weights

#--------------------------------------------------------------------------------
# Hàm 2: tính điểm khớp sở thích

def _semantic_score(user_vectors, act_vectors, text_k=0, tags_k=0):
    """
    Tính độ giống nhau giữa vector sở thích người dùng và vector hoạt động
    Sử dụng trọng số động dựa trên text_k và tags_k
    """
    weights = get_weights(text_k, tags_k)
    
    channel_pairs = [
        ("aug_tags", "tag", weights.get("aug_tags", 0.0)),
        ("aug_text", "text", weights.get("aug_text", 0.0)),
        ("text", "text", weights.get("text", 0.0)),
    ]

    sum_score=0.0
    total_weight=0.0
    #duyệt qua từng channel
    for channel_user, channel_act, weight in channel_pairs:
        v_user = user_vectors.get(channel_user)
        v_act = act_vectors.get(channel_act)

        # nếu thiếu một trong hai thì bỏ qua cặp này
        if v_user is None or v_act is None:
            continue
        if len(v_user)==0 or len(v_act)==0:
            continue

        # tính cosine similarity (kết quả từ -1 đến 1)
        sim = cosine_similarity(v_user, v_act)

        #đưa từ [-1,1] về [0,1] để dễ kết hợp với các điểm khác
        normalized_sim = ( sim + 1.0 ) / 2.0

        sum_score += normalized_sim * weight
        total_weight +=weight

    # nếu không có cặp vector nào ->trả về điểm trung tính 0.5
    if total_weight ==0:
        return 0.5

    #lấy điểm trung bình có trọng số
    return sum_score/total_weight


def cosine_similarity(v1, v2):
    """
    tính cosine similarity giữa hai vector
    công thức:      dot(v1, v2)
      sim = ---------------------------
               ||v1|| * ||v2||
    ý nghĩa:
    gần 1: hai vector cùng hướng(rất giống nhau)
    gần 0: hai vector vuông góc(không liên quan)
    gần -1:hai vector ngược hướng(đối lập nhau)
    """
    # 2 vector phải có cùng độ dài

    if len(v1)!=len(v2):
        return 0.0

    # tích vô hướng
    dot_product = 0.0
    for i in range(len(v1)):
        dot_product += v1[i] * v2[i]

    #tính độ dài của mỗi vector

    norm_v1=0.0
    for x in v1:
        norm_v1 +=x*x
    norm_v1 = math.sqrt(norm_v1)

    norm_v2=0.0
    for x in v2:
        norm_v2 +=x*x
    norm_v2 = math.sqrt(norm_v2)
    #tránh chia cho 0
    if norm_v1==0 or norm_v2==0:
        return 0.0

    return dot_product/(norm_v1*norm_v2)

#--------------------------------------------------------------------------------
# Hàm 3: tính điểm phug hợp ràng buộc
def _constraint_score(metadata,constraints):
    """
    chấm điểm xem hoạt động có phù hợp với ngân sách + thời gian

    - Hoạt động càng rẻ ->điểm càng cao
    - Hoạt động càng gần thời gian của user ->điểm càng cao

    output: số thực trong [0,1]
    """
    list_score =[]
    # 3.1: điểm về ngân sách
    price =metadata.get("price_level")
    if price is not None:
        # price_level từ N5 nằm trong [1.0, 5.0]:
        #   1.0 (rẻ nhất) -> budget_score = 1.0
        #   5.0 (đắt nhất) -> budget_score = 0.0
        budget_score = max(0.0, min(1.0, (5.0 - float(price)) / 4.0))
        list_score.append(budget_score)


    # 3.2: điểm về thời gian

    duration_user = constraints.get("duration")
    duration_act = metadata.get("estimated_duration")

    if duration_user is not None and duration_act is not None and duration_user > 0:
        # tỉ lệ hoạt động chiếm bao nhiêu % thời gian rảnh có user
        duration_ratio = duration_act / duration_user

        #cho điểm theo tỉ lệ:
        # duration_ratio <= 10% :ngắn so với thời gian rảnh -> 0.7
        # 10% < duration_ratio <= 70% :vừa đẹp -> 1.0
        # duration_ratio >= 70% : chiếm gần hết thời gian -> 0.0

        if duration_ratio <= 0.1:
            duration_score = 0.7
        elif duration_ratio <= 0.7:
            duration_score = 1.0
        else:
            duration_score=1.0-(duration_ratio-0.7)/0.3
            if duration_score < 0:
                duration_score = 0.0

        list_score.append(duration_score)


    # 3.3 lấy điểm trung bình
    if len(list_score) == 0:
        return 0.5 # không có thông tin -> điểm trung tính

    total =0.0
    for d in list_score:
        total += d
    return total/len(list_score)

#--------------------------------------------------------------------------------
# Hàm 4: tính điểm phù hợp ngữ cảnh
def _context_score(metadata, context, constraints):
    """
    chấm điểm xem hoạt động có hợp giờ trong ngay + thời tiết không
    output: số thực trong [0,1]

    """
    list_score=[]

    # 4.1: khớp thời điểm trong ngày (morning / afternoon / night)
    tod_user = context.get("time_of_day")
    tod_act = metadata.get("time_of_day_suitable")

    if tod_user is not None and tod_act is not None:
        tod_user =tod_user.lower().strip()
        tod_act =tod_act.lower().strip()

        if tod_act=="anytime":
            # hoạt động này phù hợp mọi thời điểm
            list_score.append(1.0)
        elif tod_user == tod_act:
            #trùng giờ
            list_score.append(1.0)
        else:
            #lệch giờ mặc định 0.3
            list_score.append(0.3)


    # 4.2: khớp với thời tiết (sunny / rainy / ...)
    weather = constraints.get("weather")
    indoor_outdoor = metadata.get("indoor_outdoor")
    weather_dep = metadata.get("weather_dependent")

    if weather is not None:
        weather = weather.lower().strip()

        #trời xấu: mưa, bảo, tuyết, gió lốc,....
        bad_weather = weather in ["rain", "rainy", "storm", "stormy", "snow"]

        if bad_weather:
            #trời xấu ưu tiên hoạt động trong nhà
            if indoor_outdoor == "indoor":
                list_score.append(1.0)
            elif indoor_outdoor =="mixed":
                list_score.append(0.7)
            elif weather_dep is False:
                list_score.append(0.8)
            else:
                #hoạt động ngoài trời + phụ thuộc thời tiết -> rủi ro
                list_score.append(0.2)
        else:
            # trời đẹp thì ưu tiên ngoài trời
            if indoor_outdoor =="outdoor":
                list_score.append(1.0)
            else:
                list_score.append(0.7)

    # 4.3: lấy điểm trung bình
    if len(list_score)==0:
        return 0.5 # không có data ->trung tính

    total =0.0
    for d in list_score:
        total +=d

    return total/len(list_score)

#--------------------------------------------------------------------------------
# * Hàm 5: tạo lý do để giải thích cho user

# Template lý do theo loại hoạt động — đa dạng, tránh lặp
_REASON_BY_TYPE = {
    "nature":      ["Cảnh quan {location_hint}phù hợp với bạn", "Thiên nhiên {intensity_hint}—lý tưởng để khám phá", "Ngắm {location_hint}tự nhiên, đúng gu du lịch của bạn"],
    "adventure":   ["Thử thách {intensity_hint}cho người thích khám phá", "Hoạt động mạo hiểm {intensity_hint}—sẽ nhớ mãi", "Cường độ {intensity_hint}phù hợp sức khỏe và sở thích"],
    "food":        ["Ẩm thực địa phương {price_hint}—không thể bỏ qua", "Trải nghiệm vị ngon {location_hint}với ngân sách hợp lý", "Khẩu vị của bạn sẽ hài lòng với lựa chọn này"],
    "culture":     ["Chiều sâu văn hóa {location_hint}—khác biệt hoàn toàn", "Tìm hiểu bản sắc địa phương {price_hint}", "Trải nghiệm văn hóa độc đáo, phù hợp hành trình của bạn"],
    "relaxation":  ["Thư giãn {time_hint}{price_hint}—đúng lúc cần nghỉ ngơi", "Nhịp điệu chậm, phù hợp sau ngày dài khám phá", "Tái tạo năng lượng {time_hint}với chi phí {price_hint}"],
    "nightlife":   ["Về đêm sẽ thú vị hơn với lựa chọn này", "Điểm nhấn cho buổi tối {location_hint}", "Khám phá Đà Nẵng {location_hint}lúc đêm xuống"],
    "shopping":    ["Mua sắm {price_hint}—quà lưu niệm ý nghĩa", "Tìm đồ địa phương độc đáo {location_hint}", "Trải nghiệm chợ và cửa hàng bản địa"],
}
_REASON_DEFAULT = [
    "Phù hợp với hành trình và sở thích của bạn",
    "Lựa chọn cân bằng giữa trải nghiệm và chi phí",
    "Hoạt động đáng thử trong chuyến đi này",
]

_INTENSITY_LABELS = [(0.7, "cường độ cao"), (0.4, "vừa sức"), (0.0, "nhẹ nhàng")]
_PRICE_LABELS     = [(4.0, "cao cấp"), (2.5, "tầm trung"), (0.0, "tiết kiệm")]
_TIME_LABELS      = {"morning": "buổi sáng ", "afternoon": "buổi chiều ", "evening": "buổi tối "}


def _pick(labels, value):
    for threshold, label in labels:
        if value >= threshold:
            return label
    return labels[-1][1]


def _build_reason(metadata, sem_score, cons_score, ctx_score):
    """
    Sinh lý do cụ thể, đa dạng cho từng hoạt động dựa trên đặc điểm riêng của nó.
    Tránh các cụm từ chung chung lặp lại giữa các activities.
    """
    import random

    activity_type = metadata.get("activity_type", "nature")
    name_act      = metadata.get("name", "Hoạt động này")
    price_level   = float(metadata.get("price_level") or 2.5)
    intensity     = float(metadata.get("intensity") or 0.5)
    tod           = metadata.get("time_of_day_suitable", "anytime")
    indoor_out    = metadata.get("indoor_outdoor", "outdoor")

    intensity_hint = _pick(_INTENSITY_LABELS, intensity) + " "
    price_hint     = _pick(_PRICE_LABELS, price_level)
    time_hint      = _TIME_LABELS.get(tod, "")
    location_hint  = "" if indoor_out == "indoor" else "ngoài trời "

    templates = _REASON_BY_TYPE.get(activity_type, _REASON_DEFAULT)
    # Dùng hash tên để chọn template cố định (không random mỗi lần call)
    idx = hash(name_act) % len(templates)
    reason_body = templates[idx].format(
        intensity_hint=intensity_hint,
        price_hint=price_hint,
        time_hint=time_hint,
        location_hint=location_hint,
    )

    # Thêm điểm nổi bật nếu có
    highlights = []
    if cons_score >= 0.80:
        highlights.append("trong tầm ngân sách")
    if ctx_score >= 0.75 and tod != "anytime":
        highlights.append(f"hợp {time_hint.strip()}")
    if intensity < 0.3:
        highlights.append("không tốn nhiều sức")

    if highlights:
        return f"{name_act}: {reason_body} ({', '.join(highlights)})."
    return f"{name_act}: {reason_body}."
#=============================================================================
# ENTRY POINT
#=============================================================================
def rank_activities(data):
    """
    Hàm chính:
    input: nhận 1 dict 'data'
    output: dict {"activities": [...]} đã xếp hạng
    """
    # BƯỚC 1: lấy các dữ liệu từ data
    #vector sở thích của user
    user_vectors=data.get("user_vectors",{})
    #bối cảnh (giờ, vị trí,...)
    context      =data.get("context",{})
    #danh sách các hoạt động từ N5
    activities=data.get("activities",[])
    #ngân sách thời gian,....
    constraints=data.get("constraints",{})
    #số lượng cần trả về
    top_k=data.get("top_k",5)
    #tín hiệu mở rộng từ điển
    text_k=data.get("text_k",0)
    tags_k=data.get("tags_k",0)
    #---------------------------------------------------
    # BƯỚC 2: trường hợp đặc biệt(không có gì để xếp hạng)
    if len(activities)==0 or top_k <=0:
        return {"activities": []}

    #-------------------------------------------------------
    # BƯỚC 3: duyệt qua từng hoạt động và tính điểm
    scored_activities = []
    for activity in activities:
        metadata=activity.get("metadata",{})
        vectors=activity.get("vectors",{})

        # 3.1 kiểm tả ràng buộc cứng - nếu vi phạm thì bỏ qua

        if hard_constraint_violated(metadata, constraints):
            continue


        # 3.2 tính 3 điểm con
        sem_score=_semantic_score(user_vectors, vectors, text_k, tags_k) #điểm sở thích
        cons_score=_constraint_score(metadata,constraints)#điểm ràng buộc
        ctx_score=_context_score(metadata, context, constraints)#điểm ngữ cảnh

        # Scale sem_score ra khỏi dead-zone [0.5,1.0] → [0,1]
        # BGE embeddings cùng domain cluster cao, cần kéo giãn để phân biệt
        sem_score_scaled = max(0.0, min(1.0, (sem_score - 0.5) * 2.0))

        # 3.3 tính điểm theo công thức
        sum_score=0.50*sem_score_scaled + 0.25*(cons_score+ctx_score)

        # Đảm bảo điểm nằm trong [0,1]

        if sum_score < 0:
            sum_score = 0.0
        if sum_score > 1:
            sum_score = 1.0

        # 3.4 tạo lý do
        reason = _build_reason(metadata, sem_score, cons_score, ctx_score)


        # 3.5 thêm vào danh sách
        scored_activities.append({
            "activity_id":activity.get("activity_id"),
            "location_id":activity.get("location_id"),
            "score":      round(sum_score, 4), #làm tròn 4 chữ số
            "reason":     reason,
        })
    #----------------------------------------------------------------------------
    # BƯỚC 4: sắp xếp giảm dần theo điểm và lấy top_k
    scored_activities.sort(key=lambda x: x["score"], reverse=True)

    # BƯỚC 5: min-max normalization để kéo giãn khoảng điểm
    # Giữ nguyên thứ hạng, chỉ spread score ra [0.4, 1.0] để dễ đọc hơn
    if len(scored_activities) >= 2:
        max_s = scored_activities[0]["score"]
        min_s = scored_activities[-1]["score"]
        spread = max_s - min_s
        LOW, HIGH = 0.40, 1.0
        if spread > 0.01:
            for a in scored_activities:
                normalized = LOW + (a["score"] - min_s) / spread * (HIGH - LOW)
                a["score"] = round(normalized, 4)
        else:
            # Tất cả bằng nhau → gán đều từ 0.75 đến 0.55
            for i, a in enumerate(scored_activities):
                a["score"] = round(0.75 - i * 0.05, 4)

    result=scored_activities[:top_k]
    return {"activities":result}