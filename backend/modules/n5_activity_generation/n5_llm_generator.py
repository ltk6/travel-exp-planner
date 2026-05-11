# =============================================================================
# n5_llm_generator.py
# =============================================================================
# LLM-based activity generation sử dụng Groq API (meta-llama/Llama-4-Scout).
#
# HYBRID APPROACH:
#   - LLM được gọi khi có GROQ_API_KEY → sinh ~10 activities/location
#   - Mỗi location gọi LLM 1 lần với prompt yêu cầu 10 activities đa dạng
#   - Kết quả LLM + template bank = đủ activities/location
#   - Fallback hoàn toàn về template nếu LLM không khả dụng
#
# Hybrid approach kết hợp LLM giúp:
#   - Giảm công sức xây dựng data thủ công: LLM có thể sinh ra hoạt động
#     cho bất kỳ địa điểm nào, ngay cả khi chưa có template.
#   - Tăng tính cá nhân hóa: LLM hiểu context sở thích, ngân sách, thời gian
#     của người dùng để đề xuất hoạt động phù hợp hơn.
#   - Fallback an toàn: Khi LLM không khả dụng (mất mạng, hết API key, lỗi),
#     hệ thống tự động chuyển về rule-based để đảm bảo luôn có kết quả.
#
# === SCHEMA V2 ===
# LLM prompt được cập nhật để sinh activity theo schema v2 đầy đủ:
#   activity_id, location_id, name, description, tags (5-7),
#   cost, estimated_duration, best_time, suitable_for, difficulty,
#   season, reason_template
# =============================================================================

import json
from typing import Dict, Optional, List
from config.settings import setup_logging
logger = setup_logging("N5.llm")

from .providers import get_fallback_chain, LLMProvider
from config.settings import LLM_ACTIVITIES_PER_CALL

from backend.shared.maps.tags import ALL_TAGS
VALID_TAGS = list(ALL_TAGS.keys())


def is_llm_available() -> bool:
    """LLM khả dụng nếu có ít nhất 1 provider có API key."""
    return bool(get_fallback_chain())


def _build_prompt(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    user_text: str = "",
) -> str:
    tags_str = ", ".join(user_tags) if user_tags else "không có sở thích cụ thể"
    loc_id = f"loc_{location_name.lower().replace(' ', '_')}"
    user_context = f"\n🗣️ Yêu cầu của du khách: \"{user_text}\"" if user_text.strip() else ""

    prompt = f"""Bạn là một thổ địa và chuyên gia du lịch cao cấp tại Việt Nam với am hiểu sâu sắc về văn hóa, địa hình và những 'góc khuất' ít người biết. 
Hãy tạo đúng 10 hoạt động TRẢI NGHIỆM ĐỘC ĐÁO, ĐẬM CHẤT ĐỊA PHƯƠNG cho: {location_name}.

📍 Địa điểm: {location_name}
📝 Mô tả hiện có: {location_description}
❤️ Cá nhân hóa cho du khách: {tags_str}{user_context}

TIÊU CHUẨN CHẤT LƯỢNG (PHẢI TUÂN THỦ):
1. TÊN HOẠT ĐỘNG: KHÔNG ĐƯỢC chỉ đơn giản là "Động từ + Tên địa điểm" (Ví dụ: Tránh "Ngắm cảnh Langbiang"). Phải đặt tên gợi cảm xúc, tò mò (Ví dụ: "Săn mây trên đỉnh Langbiang", "Nhâm nhi cà phê chồn giữa rừng thông").
2. NỘI DUNG MÔ TẢ: Phải cực kỳ chi tiết (3-4 câu). Hãy miêu tả cảm giác, âm thanh, mùi vị hoặc một mẹo nhỏ chỉ người bản địa mới biết. Tránh dùng các từ sáo rỗng như "đáng nhớ", "tuyệt vời", "hấp dẫn". Thay vào đó, hãy miêu tả thực tế.
3. TÍNH ĐA DẠNG: Đảm bảo đủ các nhóm:
   - Trải nghiệm cảm giác mạnh/Vận động (Trekking, chèo thuyền, leo núi...)
   - Văn hóa/Tâm linh (Gặp gỡ dân bản địa, thăm chùa chiền cổ...)
   - Ẩm thực (Món ngon lề đường, đặc sản hiếm...)
   - Chụp ảnh/Nghệ thuật (Góc check-in lạ, workshop thủ công...)
   - Thư giãn/Chữa lành (Sunset view, thiền, trà đạo...)
4. TÍNH THỰC TẾ: Hoạt động phải có thật và khả thi tại {location_name}.

CẤU TRÚC JSON (BẮT BUỘC):
{{
  "activity_id": "act_viết_không_dấu_01",
  "location_id": "{loc_id}",
  "name": "Tên trải nghiệm đầy cảm hứng",
  "description": "Mô tả sâu sắc, chân thực, nêu bật được cái 'hồn' của trải nghiệm tại đây.",
  "tags": ["4-9 tags tiếng Anh chuẩn"],
  "best_time": ["morning" hoặc "afternoon" hoặc "evening"],
  "suitable_for": ["solo", "couple", "family", "friends"],
[
  {{"activity_id": "...", "location_id": "...", "name": "...", ...}}
]"""
    return prompt


def _build_batch_prompt(location_name: str, location_description: str) -> str:
    """
    Prompt đặc biệt cho việc generate batch activities (không phụ thuộc user preference).
    
    Dùng khi generate dữ liệu tĩnh cho activities.json, không cần context user cụ thể.
    """
    loc_id = f"loc_{location_name.lower().replace(' ', '_')}"
    
    prompt = f"""Bạn là chuyên gia du lịch Việt Nam. Tạo đúng 10 activities CHI TIẾT, ĐA DẠNG, THỰC TẾ cho địa điểm: {location_name}.

Mô tả: {location_description}

Trả về CHỈ một JSON array, mỗi object có đúng các trường sau:
{{
  "activity_id": "act_{loc_id.replace('loc_', '')}_unique_01",
  "location_id": "{loc_id}",
  "name": "Tên tiếng Việt",
  "description": "2-4 câu chi tiết hấp dẫn",
  "tags": ["5-7 tags tiếng Anh phong phú"],
  "cost": số VND/người,
  "estimated_duration": số phút,
  "best_time": ["morning", "afternoon", "evening"],
  "suitable_for": ["solo", "couple", "family", "friends"],
  "difficulty": "easy|medium|hard",
  "season": ["jan", "feb", ...],
  "reason_template": "Câu ngắn giải thích phù hợp với sở thích {{matching_tags}}"
}}

Yêu cầu: thực tế, đa dạng loại hoạt động (ngắm cảnh, ẩm thực, trekking, văn hóa, mạo hiểm, chụp ảnh, thư giãn, hidden gem...), tránh lặp, cost/duration hợp lý cho Việt Nam.

TRẢ LỜI BẰNG JSON ARRAY THUẦN TÚY:"""
    return prompt


def _parse_llm_response(response_text: str) -> Optional[List[Dict]]:
    """Parse JSON từ LLM response. Xử lý: pure JSON, markdown code block, JSON trong text."""
    if not response_text or not response_text.strip():
        return None

    text = response_text.strip()

    # Case 1: parse trực tiếp
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Case 2: tìm mảng JSON đầu tiên trong text (bao gồm cả trong markdown code block)
    bracket_start = text.find('[')
    bracket_end   = text.rfind(']')
    if bracket_start != -1 and bracket_end > bracket_start:
        try:
            data = json.loads(text[bracket_start:bracket_end + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    logger.warning("Cannot parse LLM response: %s...", text[:300])
    return None


def _validate_activity(act: Dict, schema_v2: bool = True) -> bool:
    """
    Kiểm tra một activity từ LLM có đủ các trường bắt buộc và hợp lệ không.
    
    Hỗ trợ cả schema v1 (cũ) và schema v2 (mới):
      - v1: name, desc, cost, time, tags
      - v2: name, description, cost, estimated_duration, tags, activity_id,
            location_id, best_time, suitable_for, difficulty, season, reason_template
    
    Đảm bảo dữ liệu từ LLM tuân thủ schema trước khi đưa vào pipeline.
    """
    if schema_v2:
        required_fields = ["name", "description", "tags", "activity_id", "location_id"]
        optional_fields = [
            "best_time", "suitable_for", "difficulty", "season", "reason_template"
        ]
    else:
        required_fields = ["name", "desc", "tags"]
        optional_fields = []
    
    # Kiểm tra đủ trường bắt buộc
    for field in required_fields:
        if field not in act:
            logger.warning(f"Activity thiếu trường '{field}': {act.get('name', 'unknown')}")
            return False
    
    # Kiểm tra kiểu dữ liệu và giới hạn cơ bản
    name = act.get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        return False

    desc_field = "description" if schema_v2 else "desc"
    desc = act.get(desc_field, "")
    if not isinstance(desc, str) or len(desc) > 600:
        return False

    if not isinstance(act.get("tags", []), list):
        return False

    # Validate difficulty nếu có
    if schema_v2 and "difficulty" in act:
        if act["difficulty"] not in ["easy", "medium", "hard"]:
            act["difficulty"] = "easy"  # default
    
    # Validate best_time nếu có
    if schema_v2 and "best_time" in act:
        valid_times = {"morning", "afternoon", "evening"}
        act["best_time"] = [t for t in act["best_time"] if t in valid_times]
        if not act["best_time"]:
            act["best_time"] = ["morning", "afternoon"]
    
    # Validate suitable_for nếu có
    if schema_v2 and "suitable_for" in act:
        valid_suitable = {"solo", "couple", "family", "friends"}
        act["suitable_for"] = [s for s in act["suitable_for"] if s in valid_suitable]
        if not act["suitable_for"]:
            act["suitable_for"] = ["solo", "couple", "friends"]
    
    # Validate season nếu có
    if schema_v2 and "season" in act:
        valid_months = {
            "jan", "feb", "mar", "apr", "may", "jun",
            "jul", "aug", "sep", "oct", "nov", "dec"
        }
        act["season"] = [m for m in act["season"] if m in valid_months]
    
    return True


def _convert_v2_to_v1(act: Dict) -> Dict:
    """
    Chuyển đổi activity schema v2 → v1 để tương thích với pipeline cũ.
    
    Mapping:
      - "description" → "desc"
      - "estimated_duration" → "time"
      - Giữ nguyên: name, cost, tags
    """
    return {
        "name": act.get("name", ""),
        "desc": act.get("description", ""),
        "cost": act.get("cost", 0),
        "time": act.get("estimated_duration", 60),
        "tags": act.get("tags", []),
        # Giữ thêm trường v2 cho enrichment
        "activity_id": act.get("activity_id", ""),
        "best_time": act.get("best_time", []),
        "suitable_for": act.get("suitable_for", []),
        "difficulty": act.get("difficulty", "easy"),
        "season": act.get("season", []),
        "reason_template": act.get("reason_template", ""),
    }


def call_llm(
    prompt: str,
    retries: int = 1,
    provider_override: Optional[str] = None,
) -> tuple:
    """
    Gọi LLM qua fallback chain (config từ env LLM_PROVIDER / LLM_FALLBACK).

    Mỗi provider tự retry với exponential backoff + jitter.
    Nếu provider đầu fail sau mọi retry, chuyển sang provider tiếp theo.

    Args:
        provider_override: nếu có, dùng provider này làm primary thay env
                           (vẫn giữ fallback chain theo LLM_FALLBACK).

    Returns:
        (response_text, provider_used) — provider_used là tên provider đã trả
        response thành công, None nếu tất cả fail.
    """
    if provider_override:
        chain = get_fallback_chain(primary=provider_override)
    else:
        chain = get_fallback_chain()

    if not chain:
        logger.warning("No LLM provider available (check API keys)")
        return None, None

    for provider in chain:
        logger.info("Trying LLM provider=%s model=%s", provider.name, provider.model)
        result = provider.generate(prompt, retries=retries)
        if result:
            return result, provider.name
        logger.warning("Provider %s failed, trying next in chain", provider.name)

    logger.error("All LLM providers in chain failed")
    return None, None


# Backward-compat alias — code cũ có thể vẫn import call_groq_api
# (trả về chỉ text, không tuple — cho compatibility)
def call_groq_api(prompt: str, retries: int = 1) -> Optional[str]:
    text, _ = call_llm(prompt, retries=retries)
    return text


def generate_from_llm(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    schema_v2: bool = True,
    user_text: str = "",
    provider: Optional[str] = None,
) -> Optional[List[Dict]]:
    """Sinh hoạt động du lịch bằng LLM. Trả về None nếu fail."""
    activities, _meta = generate_from_llm_with_meta(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        num_activities=num_activities,
        schema_v2=schema_v2,
        user_text=user_text,
        provider=provider,
    )
    return activities


def generate_from_llm_with_meta(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    schema_v2: bool = True,
    user_text: str = "",
    provider: Optional[str] = None,
) -> tuple:
    """
    Sinh activities fresh - KHÔNG CACHE.
    """
    import time
    t0 = time.time()
    logger.warning(f"!!! TRIGGERING FRESH LLM CALL for {location_name} (CACHING REMOVED) !!!")
    meta = {"provider_used": None, "cache_hit": False, "latency_ms": 0}

    if not is_llm_available():
        return None, meta

    # ── Cache lookup (REMOVED) ──────────────────────────────────────
    # Caching has been completely excised as per user request.
    
    prompt = _build_prompt(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        num_activities=num_activities,
        user_text=user_text,
    )

    logger.info("Calling LLM for location: %s (requesting %d activities)", location_name, num_activities)
    response_text, provider_used = call_llm(prompt, provider_override=provider)
    meta["provider_used"] = provider_used
    meta["latency_ms"] = int((time.time() - t0) * 1000)

    if response_text is None:
        logger.warning("LLM returned no response for %s", location_name)
        return None, meta

    raw_list = _parse_llm_response(response_text)
    if raw_list is None:
        logger.warning("Failed to parse LLM response for %s", location_name)
        return None, meta
    
    # Bước 4: Detect schema version từ response
    # Nếu response có trường "description" → schema v2
    # Nếu response có trường "desc" → schema v1
    is_v2_response = any("description" in act for act in raw_list)

    # Bước 5: Validate và lọc
    valid_activities = []
    for act in raw_list:
        if _validate_activity(act, schema_v2=is_v2_response):
            # Chuẩn hóa tags thành lowercase
            act["tags"] = [tag.lower().strip() for tag in act["tags"]]
            
            # Chuyển đổi schema nếu cần
            if is_v2_response and not schema_v2:
                # Response là v2, nhưng caller muốn v1 → convert
                act = _convert_v2_to_v1(act)
            elif not is_v2_response and schema_v2:
                # Response là v1, caller muốn v2 → thêm trường mặc định
                act.setdefault("description", act.get("desc", ""))
                act.setdefault("estimated_duration", act.get("time", 60))
                act.setdefault("activity_id", "")
                act.setdefault("location_id", "")
                act.setdefault("best_time", ["morning", "afternoon"])
                act.setdefault("suitable_for", ["solo", "couple", "friends"])
                act.setdefault("difficulty", "easy")
                act.setdefault("season", [])
                act.setdefault("reason_template", "")
            
            valid_activities.append(act)
        else:
            logger.warning(f"Activity không hợp lệ bị bỏ qua: {act.get('name', 'unknown')}")
    
    if not valid_activities:
        logger.warning(f"Không có activity hợp lệ từ LLM cho {location_name}")
        return None, meta

    logger.info("LLM generated %d valid activities for %s", len(valid_activities), location_name)
    return valid_activities, meta