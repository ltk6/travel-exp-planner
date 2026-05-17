# =============================================================================
# n5_llm_generator.py
# =============================================================================
# LLM-based activity generation sử dụng Gemini API.
#
# Mỗi location gọi Gemini 1 lần, yêu cầu N activities theo unified schema
# (xem activity_retrievals/SCHEMA.md). Output được generator hợp nhất với
# template expansion để đạt TARGET_PER_LOCATION.
#
# Khi GEMINI_API_KEY không có hoặc gọi lỗi → trả None, generator fallback
# về template-only path.
# =============================================================================

import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

GEMINI_MODEL   = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
LLM_ACTIVITIES_PER_CALL = 25

# Enum hợp lệ — phải khớp với activity_retrievals/schema.py
_ALLOWED_ACTIVITY_TYPES = {
    "adventure", "relaxation", "food", "culture",
    "nightlife", "nature", "shopping",
}
_ALLOWED_INDOOR_OUTDOOR = {"indoor", "outdoor", "mixed"}
_ALLOWED_TIME_OF_DAY    = {"morning", "afternoon", "night", "anytime"}


def is_llm_available() -> bool:
    return bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())


def _strip_accents(s: str) -> str:
    """Xóa dấu tiếng Việt: 'Sa Pa' → 'sa pa', 'Đà Lạt' → 'da lat'."""
    s = s.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _build_prompt(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    budget_per_activity: int,
    max_time_per_activity: int,
    num_activities: int,
) -> str:
    """
    Prompt yêu cầu LLM trả JSON array các activity tuân unified schema.

    Field LLM phải sinh khớp đúng những gì `n5_activity_generator._build_activity_output`
    đọc → tránh tình trạng generator fallback về default toàn bộ.
    """
    tags_str = ", ".join(user_tags) if user_tags else "không có sở thích cụ thể"
    budget_str = f"{budget_per_activity:,}".replace(",", ".")

    return f"""Bạn là chuyên gia du lịch Việt Nam với 20 năm kinh nghiệm. Hãy tạo đúng {num_activities} activities CHI TIẾT, ĐA DẠNG, THỰC TẾ cho địa điểm: {location_name}.

📍 Địa điểm: {location_name}
📝 Mô tả: {location_description}
❤️ Sở thích du khách: {tags_str}
💰 Ngân sách tối đa mỗi hoạt động: {budget_str} VNĐ
⏰ Thời gian tối đa mỗi hoạt động: {max_time_per_activity} phút

YÊU CẦU:
1. Tạo đúng {num_activities} hoạt động, mỗi hoạt động KHÁC LOẠI (ngắm cảnh, trekking, ẩm thực, văn hóa, chụp ảnh, mạo hiểm, thư giãn, mua sắm, hidden gem, nightlife...).
2. Mỗi hoạt động PHẢI có đúng các trường sau, đúng kiểu dữ liệu:

{{
  "name":                  "Tên hoạt động tiếng Việt ngắn gọn",
  "description":           "2-4 câu mô tả hấp dẫn, gợi cảm xúc.",
  "activity_type":         "adventure" | "relaxation" | "food" | "culture" | "nightlife" | "nature" | "shopping",
  "activity_subtype":      "string tự do, ví dụ: hiking, sunrise_viewing, street_food, museum_visit",
  "estimated_duration":    số phút (int, 30-360),
  "price_level":           số thực 0.0 → 1.0 (0.0=miễn phí, 0.5=trung bình, 1.0=rất đắt),
  "indoor_outdoor":        "indoor" | "outdoor" | "mixed",
  "weather_dependent":     true | false,
  "time_of_day_suitable":  "morning" | "afternoon" | "night" | "anytime"
}}

3. Chi phí ≤ {budget_str} VNĐ — quy đổi về thang 0.0-1.0 cho `price_level`.
4. `estimated_duration` ≤ {max_time_per_activity} phút.
5. Ưu tiên hoạt động phù hợp sở thích: {tags_str}.
6. Hoạt động phải thực tế, có thể thực hiện tại {location_name}, phản ánh đặc trưng địa phương.
7. Đa dạng: có cả hoạt động miễn phí (price_level=0.0) và cao cấp (price_level≥0.7).

TRẢ LỜI BẰNG JSON ARRAY THUẦN TÚY (không markdown, không giải thích):
[
  {{"name": "...", "description": "...", "activity_type": "...", ...}}
]"""


def _parse_llm_response(response_text: str) -> Optional[List[Dict[str, Any]]]:
    """Parse JSON từ LLM response. Hỗ trợ: pure JSON, markdown fence, JSON embedded trong text."""
    if not response_text or not response_text.strip():
        return None
    text = response_text.strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    for pattern in [r"```json\s*\n?(.*?)\n?\s*```", r"```\s*\n?(.*?)\n?\s*```"]:
        for match in re.findall(pattern, text, re.DOTALL):
            try:
                data = json.loads(match.strip())
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                continue

    bs, be = text.find("["), text.rfind("]")
    if bs != -1 and be > bs:
        try:
            data = json.loads(text[bs:be + 1])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    logger.warning("Cannot parse LLM response: %s...", text[:300])
    return None


def _validate_and_normalize(act: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate 1 activity theo unified schema. Trả về dict đã normalize hoặc None nếu fail.

    Coerce nhẹ: lowercase enum, clamp price_level vào [0, 1], cast int/float/bool.
    Reject nếu thiếu `name`/`description` hoặc enum sai sau khi lowercase.
    """
    name = act.get("name")
    if not isinstance(name, str) or not name.strip():
        return None
    description = act.get("description")
    if not isinstance(description, str) or not description.strip():
        return None

    activity_type = (act.get("activity_type") or "").lower().strip()
    if activity_type not in _ALLOWED_ACTIVITY_TYPES:
        return None

    indoor_outdoor = (act.get("indoor_outdoor") or "").lower().strip()
    if indoor_outdoor not in _ALLOWED_INDOOR_OUTDOOR:
        return None

    tod = (act.get("time_of_day_suitable") or "anytime").lower().strip()
    if tod not in _ALLOWED_TIME_OF_DAY:
        tod = "anytime"

    try:
        duration = int(act.get("estimated_duration", 120))
        price    = float(act.get("price_level", 0.5))
    except (TypeError, ValueError):
        return None
    if duration <= 0:
        return None
    price = max(0.0, min(1.0, price))

    return {
        "name":                 name.strip(),
        "description":          description.strip(),
        "activity_type":        activity_type,
        "activity_subtype":     (act.get("activity_subtype") or None) or None,
        "estimated_duration":   float(duration),
        "price_level":          round(price, 2),
        "indoor_outdoor":       indoor_outdoor,
        "weather_dependent":    bool(act.get("weather_dependent", True)),
        "time_of_day_suitable": tod,
    }


def call_gemini_api(prompt: str) -> Optional[str]:
    """Gọi Gemini API, trả về text response hoặc None nếu lỗi."""
    if not is_llm_available():
        return None

    import urllib.error
    import urllib.request

    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "topP":        0.9,
            "maxOutputTokens": 4096,
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as e:
        logger.error("Gemini network error: %s", e)
        return None
    except json.JSONDecodeError as e:
        logger.error("Gemini response not JSON: %s", e)
        return None

    candidates = result.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        if parts:
            return parts[0].get("text", "")
    logger.warning("Gemini unexpected response format: %s", str(result)[:200])
    return None


def generate_from_llm(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    budget_per_activity: int,
    max_time_per_activity: int,
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
) -> Optional[List[Dict[str, Any]]]:
    """
    Sinh activities bằng LLM (Gemini). Output mỗi item là dict các field khớp
    với những gì `n5_activity_generator._build_activity_output` đọc.

    Returns:
        List[Dict] đã validate, hoặc None nếu LLM không khả dụng / fail toàn bộ.
    """
    if not is_llm_available():
        return None

    prompt = _build_prompt(
        location_name=location_name,
        location_description=location_description,
        location_tags=location_tags,
        user_tags=user_tags,
        budget_per_activity=budget_per_activity,
        max_time_per_activity=max_time_per_activity,
        num_activities=num_activities,
    )

    logger.info("Calling Gemini for '%s' (requesting %d activities)", location_name, num_activities)
    response_text = call_gemini_api(prompt)
    if response_text is None:
        return None

    raw_list = _parse_llm_response(response_text)
    if raw_list is None:
        return None

    validated = []
    for act in raw_list:
        norm = _validate_and_normalize(act)
        if norm is not None:
            validated.append(norm)
        else:
            logger.warning("LLM activity rejected: %s", str(act)[:120])

    if not validated:
        logger.warning("No valid LLM activities for %s", location_name)
        return None

    logger.info("LLM produced %d valid activities for %s", len(validated), location_name)
    return validated
