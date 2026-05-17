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

import logging

from backend.shared.math import cosine_normalized_unit as _cosine_unit

logger = logging.getLogger(__name__)

#=============================================================================
#DANH SÁCH CÁC HÀM PHỤ HỖ TRỢ 
#=============================================================================

# Hàm 1: kiểm tra ràng buộc cứng

def hard_constraint_violated(metadata, constraints):
    """
    trả về true nếu hoạt động vi phạm ràng buộc cứng(bi loại)
    trả về false nếu hoạt động không hợp lệ 

    hiện tại chỉ kiểm tra :thời gian của hoạt động không qua thời gian rảnh của 
    user
    """
    duration_user=constraints.get("duration")
    duration_act=metadata.get("estimated_duration")
    
    #nếu cả hai đều có giá trị và hoạt động dài hơn thời gian rảnh -> loại
    if duration_user is not None and duration_act is not None:
        if duration_act > duration_user:
            return True

    return False

#--------------------------------------------------------------------------------
# Hàm 2: tính điểm khớp sở thích  

def _semantic_score(user_vectors, act_vectors):
    """ 
    Tính độ giống nhau giữa vector sở thích người dùng và vector hoạt động

    ý tưởng:
    user có nhiều kênh vector: tag, context, emotion, image
    hoạt động cũng có nhiều kênh vector : text, tag, intent
    ta ghép các cặp kênh tương ứng , tính COSINE SIMILARITY từng cặp,   
    rồi lấy trung bình từng trọng số

    trả về: số thực trong đoạn [0,1] ( càng gần 1 càng khớp sở thích và ngược lại)

    """
    channel_pairs = [
        ("tag", "tag", 0.40),   # tag-tag là tín hiệu mạnh nhất
        ("context", "text", 0.35),   # context user khớp với mô tả text
        ("emotion", "intent", 0.25),   # cảm xúc khớp với ý định
    ]

    sum_score = 0.0
    total_weight = 0.0
    for channel_user, channel_act, weight in channel_pairs:
        v_user = user_vectors.get(channel_user)
        v_act  = act_vectors.get(channel_act)
        if not v_user or not v_act:
            continue
        # cosine_normalized_unit đã map [-1,1] → [0,1] và handle length mismatch.
        sum_score += _cosine_unit(v_user, v_act) * weight
        total_weight += weight

    if total_weight == 0:
        return 0.5
    return sum_score / total_weight

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
        #price=0.0(miễn phí)-> điểm 1.0
        #price=1.0(rất đắt)->điểm 0.0
        budget_score = 1.0 - float(price)

        if budget_score < 0:
            budget_score = 0.0 #quy về băng 0.0 nếu điểm ngân sách dưới 0

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
# * Hàm 5: tạo lý do để giải thích có user

def _build_reason(metadata, sem_score, cons_score, ctx_score):
    """
    giải thích ngắn gọn tại sao hoạt động này được xếp hạng cao
    output: một câu ngắn gọn giải thích tại sao hoạt động này được xếp hạng cao
    ví dụ: đồi thông đà lạt: rất phù hợp với sở thích, trong tầm ngân sách.
    """
    name_act = metadata.get("name"," Hoạt động")
    parts =[]
    # 5.1: sở thích
    if sem_score >= 0.75:
        parts.append("Rất khớp với sở thích")
    elif sem_score >= 0.55:
        parts.append("Khá phù hợp với sở thích")

    #5.2:điểm ràng buộc
    if cons_score >= 0.75:
        parts.append("rất phù hợp với ngân sách và thời gian")
    elif cons_score >= 0.55:
        parts.append("ổn về ngân sách và thời gian")

    # 5.3: ngữ cảnh
    if ctx_score >= 0.75:
        parts.append("hợp khung giờ và thời tiết")
    elif ctx_score >= 0.55:
        parts.append("khung giờ và thời tiết chấp nhận được ")

    # 5.4: nếu không có lý do nổi bậc nào
    if len(parts) == 0:
        parts.append("đáp ứng các tiêu chí cơ bản")

    # 5.5: ghép lại thành một câu hoàn chỉnh
    result = name_act + ": " + ", ".join(parts) + "."

    return result
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
    top_k=data.get("top_k",0)
    #---------------------------------------------------
    # BƯỚC 2: trường hợp đặc biệt(không có gì để xếp hạng)
    if len(activities)==0 or top_k <=0:
        return {"activities": []}

    # Cảnh báo 1 lần nếu activities thiếu vectors → semantic_score sẽ luôn trả 0.5
    # (điểm trung tính), khiến N6 mất ~50% sức mạnh ranking. Vectors phải được
    # bơm vào bởi bước embedding (N1) trước khi gọi N6.
    if not any(a.get("vectors") for a in activities):
        logger.warning(
            "[N6] %d activities có vectors=None/empty. semantic_score sẽ fallback 0.5. "
            "Hãy chạy N1 embedding để enrich `vectors` trước khi gọi rank_activities().",
            len(activities),
        )

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
        sem_score=_semantic_score(user_vectors, vectors) #điểm sở thích
        cons_score=_constraint_score(metadata,constraints)#điểm ràng buộc
        ctx_score=_context_score(metadata, context, constraints)#điểm ngữ cảnh


        # 3.3 tính điểm theo công thức
        sum_score=0.50*sem_score + 0.25*(cons_score+ctx_score)

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
    # BƯỚC4: sắp xếp giảm gần theo điểm và lấy top_k
    scored_activities.sort(key=lambda x: x["score"], reverse=True)
    result=scored_activities[:top_k]

    return {"activities":result}





