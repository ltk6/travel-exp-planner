# =============================================================================
# n5_llm_generator.py — LLM-based activity generation
#
# Provider: fallback chain (Gemini / Groq / ...) via providers/
# Schema: v2 only — name, description, tags, cost, estimated_duration,
#         best_time, suitable_for, difficulty, season, reason_template
# Tags vocabulary: ALL_TAGS from backend.shared.maps.tags
# =============================================================================

import json
from typing import Dict, List, Optional

from config.settings import setup_logging, LLM_ACTIVITIES_PER_CALL, LLM_MAX_RETRIES

from .providers import get_fallback_chain
from backend.shared.maps.tags import ALL_TAGS

logger = setup_logging("N5.llm")

# Tags chuẩn cho LLM tham khảo khi sinh activities — dùng ALL_TAGS vocabulary
VALID_TAGS     = sorted(ALL_TAGS.keys())   # dùng trong prompt
VALID_TAGS_SET = set(ALL_TAGS.keys())      # dùng để lọc output

# Chuẩn hóa các tag LLM hay sinh ra nhưng không khớp từng chữ với ALL_TAGS
_TAG_ALIASES: dict[str, str] = {
    "nature":           "wildlife",
    "culture":          "history",
    "scenic":           "picturesque",
    "relax":            "peaceful",
    "relaxation":       "peaceful",
    "heritage":         "history",
    "architecture":     "colonial heritage",
    "entertainment":    "nightlife",
    "diving":           "scuba diving",
    "kayak":            "kayaking",
    "cool_weather":     "cool climate",
    "rice_terrace":     "rice terrace",
    "ethnic":           "ethnic minority",
    "food":             "local cuisine",
    "historical":       "history",
    "hot_spring":       "hot spring",
    "sand_dune":        "sand dune",
    "music":            "traditional music",
    "craft":            "craft village",
    "cooking":          "cooking class",
    "spa_massage":      "spa",
    "adventure_sports": "adventure",
}


def is_llm_available() -> bool:
    """LLM khả dụng nếu có ít nhất 1 provider có API key."""
    return bool(get_fallback_chain())


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
5. TAGS: BẮT BUỘC chọn từ 4 đến 8 tags từ danh sách chuẩn dưới đây. TUYỆT ĐỐI KHÔNG tự bịa tag mới, phải copy NGUYÊN VĂN tên tag từ danh sách: {valid_tags_str}.

CẤU TRÚC JSON BẮT BUỘC (đúng {num_activities} phần tử):
{{
  "name": "Tên trải nghiệm đầy cảm hứng",
  "description": "Mô tả sâu sắc, chân thực, nêu bật được cái 'hồn' của trải nghiệm.",
  "tags": ["tag1", "tag2", ...],  // BẮT BUỘC 4-8 tags, CHỈ lấy từ danh sách chuẩn đã cung cấp
  "intensity": 0.0 đến 1.0 (mức độ bận rộn/sôi nổi),
  "physical_level": 0.0 đến 1.0 (mức độ tiêu tốn thể lực),
  "social_level": 0.0 đến 1.0 (mức độ tương tác xã hội/đông người)
}}

TRẢ LỜI BẰNG JSON ARRAY THUẦN TÚY (không markdown, không giải thích thêm):
[
  {{"activity_id": "...", "location_id": "...", "name": "...", ...}}
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

    # Case 1: parse trực tiếp
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Case 2: tìm mảng JSON đầu tiên trong text (kể cả trong markdown code block)
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
# LLM CALL (fallback chain + retry)
# =============================================================================

def call_llm(
    prompt: str,
    retries: int = LLM_MAX_RETRIES,
    provider_override: Optional[str] = None,
) -> tuple:
    """
    Gọi LLM qua fallback chain (config từ env LLM_PROVIDER / LLM_FALLBACK).

    Mỗi provider tự retry với exponential backoff + jitter (xử lý trong base.py).
    Nếu provider đầu fail sau mọi retry, chuyển sang provider tiếp theo.

    Returns:
        (response_text, provider_used) — provider_used là tên provider trả về
        response thành công, (None, None) nếu tất cả fail.
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
            return result, provider.name, getattr(provider, "last_usage", None)
        logger.warning("Provider %s failed, trying next in chain", provider.name)

    logger.error("All LLM providers in chain failed")
    return None, None, None


# =============================================================================
# PUBLIC API
# =============================================================================

def generate_from_llm(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    user_text: str = "",
    provider: Optional[str] = None,
    retries: int = LLM_MAX_RETRIES,
) -> Optional[List[Dict]]:
    """Sinh hoạt động du lịch bằng LLM. Trả về None nếu fail."""
    activities, _meta = generate_from_llm_with_meta(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        num_activities=num_activities,
        user_text=user_text,
        provider=provider,
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
    provider: Optional[str] = None,
    retries: int = LLM_MAX_RETRIES,
) -> tuple:
    """
    Sinh activities bằng LLM, trả kèm meta dict:
        {
            "provider_used": str | None,
            "latency_ms":    int,
        }
    """
    import time
    t0 = time.time()
    meta = {"provider_used": None, "latency_ms": 0}

    if not is_llm_available():
        return None, meta

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
    response_text, provider_used, usage = call_llm(prompt, retries=retries, provider_override=provider)
    meta["provider_used"] = provider_used
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
            resolved = [_TAG_ALIASES.get(t, t) for t in cleaned]
            filtered = list(dict.fromkeys(t for t in resolved if t in VALID_TAGS_SET))
            dropped  = set(cleaned) - set(filtered)
            if dropped:
                logger.debug("Dropped unrecognised tags for '%s': %s", act.get("name"), dropped)
            act["tags"] = filtered
            valid_activities.append(act)
        else:
            logger.warning("Activity không hợp lệ bị bỏ qua: %s", act.get("name", "unknown"))

    if not valid_activities:
        logger.warning("Không có activity hợp lệ từ LLM cho '%s'", location_name)
        return None, meta

    logger.info("LLM generated %d valid activities for '%s'", len(valid_activities), location_name)
    return valid_activities, meta