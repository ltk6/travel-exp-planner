# =============================================================================
# n5_llm_generator.py — LLM-based activity generation
#
# Provider: LLM chain (Groq models) via providers/
# Schema: v2 only — name, description, tags, cost, estimated_duration,
#         best_time, suitable_for, difficulty, season, reason_template
# Tags vocabulary: ALL_TAGS from backend.shared.maps.tags
# =============================================================================

import json
from typing import Dict, List, Optional

from config import setup_logging, LLM_ACTIVITIES_PER_CALL, LLM_MAX_RETRIES

from .providers import get_llm_chain
from backend.shared.maps.tags import ALL_TAGS

logger = setup_logging("N5.llm")

# Tags chuẩn cho LLM tham khảo khi sinh activities — dùng ALL_TAGS vocabulary
VALID_TAGS     = sorted(ALL_TAGS.keys())   # dùng trong prompt
VALID_TAGS_SET = set(ALL_TAGS.keys())      # dùng để lọc output


def is_llm_available() -> bool:
    """LLM khả dụng nếu có ít nhất 1 provider có API key."""
    return bool(get_llm_chain())


# =============================================================================
# PROMPT BUILDER
# =============================================================================

def _build_prompt(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    user_text: str = "",
) -> str:
    tags_str = ", ".join(user_tags) if user_tags else "không có sở thích cụ thể"
    user_context = f"\n🗣️ Yêu cầu của du khách: \"{user_text}\"" if user_text.strip() else ""
    valid_tags_str = ", ".join(VALID_TAGS)

    prompt = f"""Bạn là một thổ địa và chuyên gia du lịch cao cấp tại Việt Nam với am hiểu sâu sắc về văn hóa, địa hình và những 'góc khuất' ít người biết.
Hãy tạo đúng {num_activities} hoạt động TRẢI NGHIỆM ĐỘC ĐÁO, ĐẬM CHẤT ĐỊA PHƯƠNG cho: {location_name}.

📍 Địa điểm: {location_name}
📝 Mô tả: {location_description}
❤️ Cá nhân hóa cho du khách: {tags_str}{user_context}

TIÊU CHUẨN CHẤT LƯỢNG (PHẢI TUÂN THỦ):
1. TÊN HOẠT ĐỘNG: Không được chỉ là "Động từ + Tên địa điểm". Phải gợi cảm xúc, tò mò (Ví dụ: "Săn mây trên đỉnh Langbiang").
2. NỘI DUNG MÔ TẢ: 3-4 câu chi tiết — mô tả cảm giác, âm thanh, mùi vị, hoặc mẹo chỉ người bản địa mới biết. Tránh từ sáo rỗng.
3. TÍNH ĐA DẠNG: Bao gồm ít nhất: cảm giác mạnh/vận động, văn hóa/tâm linh, ẩm thực, chụp ảnh/nghệ thuật, thư giãn/chữa lành.
4. TÍNH THỰC TẾ: Hoạt động phải có thật và khả thi tại {location_name}.
5. TAGS: BẮT BUỘC chọn từ 4 đến 8 tags từ danh sách chuẩn dưới đây. TUYỆT ĐỐI KHÔNG tự bịa tag mới: {valid_tags_str}.

CẤU TRÚC JSON BẮT BUỘC (Trả về đúng 1 Array gồm {num_activities} Objects):
{{
  "name": "Tên trải nghiệm (string)",
  "description": "Mô tả sâu sắc, chân thực, nêu bật được cái 'hồn' của trải nghiệm.",
  "tags": ["tag1", "tag2", ...],  // BẮT BUỘC 4-8 tags, CHỈ lấy từ danh sách chuẩn đã cung cấp
  "activity_type": "Loại hình (chọn 1: food, adventure, culture, nightlife, shopping, relaxation, nature, photography, experience)",
  "intensity": 0.0,      // (float 0.0-1.0) mức độ bận rộn/sôi nổi
  "physical_level": 0.0, // (float 0.0-1.0) mức độ tiêu tốn thể lực
  "social_level": 0.0,   // (float 0.0-1.0) mức độ tương tác xã hội/đông người
  "reasoning": "Tại sao hoạt động này lại phù hợp nhất với sở thích và địa điểm này? (Giải thích ngắn gọn)"
}}

QUY TẮC NGHIÊM NGẶT:
- KHÔNG giải thích đầu/cuối.
- KHÔNG bao bọc trong markdown code blocks (```json ... ```).
- CHỈ trả về duy nhất 1 JSON Array hợp lệ bắt đầu bằng '[' và kết thúc bằng ']'.
- Sử dụng tiếng Việt tự nhiên, sang trọng, đúng phong cách chuyên gia du lịch.
- Cực kỳ súc tích: Mỗi mô tả tối đa 3 câu. KHÔNG viết quá dài để tránh bị cắt ngang (limit 4000 tokens).

TRẢ LỜI:
[
  {{
    "name": "...",
    "description": "...",
    "tags": ["...", "..."],
    "activity_type": "...",
    "intensity": 0.5,
    "physical_level": 0.3,
    "social_level": 0.8,
    "reasoning": "..."
  }},
  ...
]"""

    return prompt


# =============================================================================
# RESPONSE PARSING & VALIDATION
# =============================================================================

def _parse_llm_response(response_text: str) -> Optional[List[Dict]]:
    """Parse JSON từ LLM response. Xử lý: pure JSON, markdown code block, JSON trong text."""
    if not response_text or not response_text.strip():
        return None
    text = response_text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Case 2: tìm mảng JSON đầu tiên trong text
    bracket_start = text.find('[')
    bracket_end   = text.rfind(']')
    
    if bracket_start != -1:
        # Nếu không có bracket_end (truncated), cố gắng repair
        json_str = text[bracket_start : (bracket_end + 1 if bracket_end > bracket_start else len(text))]
        
        # Tiền xử lý: Xóa trailing commas [..., ] -> [...]
        import re
        json_str = re.sub(r',\s*\]', ']', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to repair truncated array: [ {...}, {...}, {"name":...
            # Chúng ta tìm dấu } cuối cùng mà có số lượng { và } khớp nhau trong object đó
            if json_str.strip().startswith('['):
                # Thử cắt ngược từ cuối lên để tìm object hợp lệ gần nhất
                temp_str = json_str.strip()
                while len(temp_str) > 1:
                    last_brace = temp_str.rfind('}')
                    if last_brace == -1: break
                    
                    try:
                        potential = temp_str[:last_brace+1] + ']'
                        return json.loads(potential)
                    except:
                        # Nếu không được, cắt bỏ phần đuôi và tìm tiếp brace trước đó
                        temp_str = temp_str[:last_brace]
    
    logger.warning("Cannot parse LLM response: %s...", text[:300])
    return None


def _validate_activity(act: Dict) -> bool:
    """
    Kiểm tra activity từ LLM có đủ trường bắt buộc và hợp lệ không.
    Required: activity_id, location_id, name, description, tags.
    """
    required_fields = ["name", "description", "tags"]
    for field in required_fields:
        if field not in act:
            logger.warning("Activity thiếu trường '%s': %s", field, act.get("name", "unknown"))
            return False

    name = act.get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        return False

    desc = act.get("description", "")
    if not isinstance(desc, str) or len(desc) > 600:
        return False

    if not isinstance(act.get("tags", []), list):
        return False

    if "intensity" in act:
        try:
            act["intensity"] = max(0.0, min(1.0, float(act["intensity"])))
        except:
            act["intensity"] = 0.5
            
    if "physical_level" in act:
        try:
            act["physical_level"] = max(0.0, min(1.0, float(act["physical_level"])))
        except:
            act["physical_level"] = 0.5

    if "social_level" in act:
        try:
            act["social_level"] = max(0.0, min(1.0, float(act["social_level"])))
        except:
            act["social_level"] = 0.5

    return True


# =============================================================================
# LLM CALL (chain execution + retry)
# =============================================================================

def call_llm(
    prompt: str,
    retries: int = LLM_MAX_RETRIES,
    chain_override: Optional[str] = None,
    temperature: float = 0.1,
) -> tuple:
    """
    Gọi LLM qua chain (config từ env LLM_CHAIN).

    Mỗi provider tự retry với exponential backoff + jitter (xử lý trong base.py).
    Nếu provider đầu fail sau mọi retry, chuyển sang provider tiếp theo trong chain.

    Returns:
        (response_text, provider_name, model_name, usage)
    """
    if chain_override:
        chain = get_llm_chain(chain_str=chain_override)
    else:
        chain = get_llm_chain()

    if not chain:
        logger.warning("No LLM provider available (check API keys)")
        return None, None, None

    import time, random
    from config import LLM_RETRY_WAIT_BASE

    for pass_idx in range(retries + 1):
        for provider in chain:
            logger.info("Trying LLM provider=%s model=%s (pass %d)", provider.name, provider.model, pass_idx + 1)
            # Trong mỗi pass, mỗi provider chỉ thử 1 lần (retries=0) 
            # để nhanh chóng chuyển sang model khác nếu bị rate limit.
            result = provider.generate(prompt, retries=0, temperature=temperature, max_tokens=4000)
            if result:
                return result, provider.name, provider.model, getattr(provider, "last_usage", None)
            logger.warning("Provider %s failed in pass %d", provider.name, pass_idx + 1)

        if pass_idx < retries:
            wait = min(8.0, (LLM_RETRY_WAIT_BASE * (1.5 ** pass_idx)) + random.random())
            logger.warning("All models in chain failed. Waiting %.2fs before pass %d...", wait, pass_idx + 2)
            time.sleep(wait)

    logger.error("All LLM providers in all passes failed")
    return None, None, None, None


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_from_llm(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    user_text: str = "",
    llm_chain: Optional[str] = None,
    retries: int = LLM_MAX_RETRIES,
    num_activities: Optional[int] = None,
) -> Optional[List[Dict]]:
    """Sinh hoạt động du lịch bằng LLM. Trả về None nếu fail."""
    from config.settings import LLM_ACTIVITIES_PER_CALL, LLM_N5_TARGET_COUNT
    
    # Ưu tiên lấy giá trị target_count từ config nếu num_activities không được truyền vào
    actual_num = num_activities if num_activities is not None else LLM_N5_TARGET_COUNT
    
    if actual_num <= 0 or LLM_ACTIVITIES_PER_CALL <= 0:
        logger.info("N5: Skipping generation (LLM_ACTIVITIES_PER_CALL=%d, target=%d)", 
                    LLM_ACTIVITIES_PER_CALL, actual_num)
        return []

    activities, _meta = generate_from_llm_with_meta(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        num_activities=actual_num,
        user_text=user_text,
        llm_chain=llm_chain,
        retries=retries,
    )
    return activities


def generate_from_llm_with_meta(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    user_text: str = "",
    llm_chain: Optional[str] = None,
    retries: int = LLM_MAX_RETRIES,
) -> tuple:
    """
    Sinh activities bằng LLM, trả kèm meta dict:
        {
            "provider_used": str | None,
            "model_used":    str | None,
            "latency_ms":    int,
            "usage":         dict | None,
        }
    """
    import time
    from config.settings import LLM_ACTIVITIES_PER_CALL, LLM_N5_TARGET_COUNT
    
    t0 = time.time()
    meta = {"provider_used": None, "latency_ms": 0}

    # Kiểm tra cả hai cấu hình
    if not is_llm_available() or num_activities <= 0 or LLM_ACTIVITIES_PER_CALL <= 0:
        logger.info("N5: Skipping LLM (available=%s, per_call=%d, target=%d)", 
                    is_llm_available(), LLM_ACTIVITIES_PER_CALL, num_activities)
        meta["latency_ms"] = int((time.time() - t0) * 1000)
        return [], meta

    prompt = _build_prompt(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        num_activities=num_activities,
        user_text=user_text,
    )

    logger.info(
        "Calling LLM for location='%s' (requesting %d activities)",
        location_name, num_activities,
    )
    response_text, provider_used, model_used, usage = call_llm(prompt, retries=retries, chain_override=llm_chain)
    meta["provider_used"] = provider_used
    meta["model_used"] = model_used
    meta["usage"] = usage
    meta["latency_ms"] = int((time.time() - t0) * 1000)

    if response_text is None:
        logger.warning("LLM returned no response for '%s'", location_name)
        return None, meta

    raw_list = _parse_llm_response(response_text)
    if raw_list is None:
        logger.warning("Failed to parse LLM response for '%s'", location_name)
        return None, meta

    valid_activities = []
    for act in raw_list:
        if _validate_activity(act):
            # Chuẩn hóa + alias → lọc chỉ giữ keys có trong ALL_TAGS
            cleaned  = [t.lower().strip() for t in act["tags"]]
            filtered = list(dict.fromkeys(t for t in cleaned if t in VALID_TAGS_SET))
            act["tags"] = filtered
            valid_activities.append(act)
        else:
            logger.warning("Activity không hợp lệ bị bỏ qua: %s", act.get("name", "unknown"))

    if not valid_activities:
        logger.warning("Không có activity hợp lệ từ LLM cho '%s'", location_name)
        return None, meta

    logger.info("LLM generated %d valid activities for '%s'", len(valid_activities), location_name)
    return valid_activities, meta