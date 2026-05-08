# =============================================================================
# n5_llm_generator.py
# =============================================================================
# LLM-based activity generation sử dụng Gemini API.
#
# HYBRID APPROACH:
#   - LLM được gọi khi có GEMINI_API_KEY → sinh ~25 activities/location
#   - Mỗi location gọi LLM 1 lần với prompt yêu cầu 25 activities đa dạng
#   - Kết quả LLM + template bank = đủ 100 activities/location
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
import os
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

from config.settings import GEMINI_API_KEY

GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

LLM_ACTIVITIES_PER_CALL = 10

# Danh sách tags chuẩn để LLM tham khảo
VALID_TAGS = [
    "nature", "food", "culture", "adventure", "relax", "photography",
    "history", "sports", "shopping", "entertainment", "health", "education",
    "sea", "beach", "fun", "music", "family", "sightseeing", "trekking",
    "mountain", "waterfall", "cave", "island", "temple", "market",
    "nightlife", "romantic", "ethnic", "village", "cycling", "kayak",
    "diving", "snorkeling", "sunrise", "sunset", "cuisine", "local_food",
    "street_food", "heritage", "architecture", "hidden_gem", "scenic",
    "wildlife", "eco", "spiritual", "art", "craft", "unique",
    "motorbiking", "road_trip", "camping", "homestay", "experience",
    "flower", "lake", "river", "forest", "agriculture", "tradition",
]


def is_llm_available() -> bool:
    return bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())


def _build_prompt(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    budget_per_activity: int,
    max_time_per_activity: int,
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    user_text: str = "",
) -> str:
    tags_str = ", ".join(user_tags) if user_tags else "không có sở thích cụ thể"
    budget_str = f"{budget_per_activity:,}".replace(",", ".")

    loc_id = f"loc_{location_name.lower().replace(' ', '_')}"
    user_context = f"\n🗣️ Yêu cầu của du khách: \"{user_text}\"" if user_text.strip() else ""

    prompt = f"""Bạn là chuyên gia du lịch Việt Nam với 20 năm kinh nghiệm. Hãy tạo đúng 10 activities CHI TIẾT, ĐA DẠNG, THỰC TẾ cho địa điểm: {location_name}.

📍 Địa điểm: {location_name}
📝 Mô tả: {location_description}
❤️ Sở thích du khách: {tags_str}{user_context}
💰 Ngân sách tối đa mỗi hoạt động: {budget_str} VNĐ
⏰ Thời gian tối đa mỗi hoạt động: {max_time_per_activity} phút

YÊU CẦU NGHIÊM NGẶT:
1. Tạo đúng 10 hoạt động, mỗi hoạt động PHẢI KHÁC LOẠI (ngắm cảnh, trekking, ẩm thực, văn hóa, chụp ảnh, mạo hiểm, thư giãn, mua sắm, hidden gem, nightlife...).
2. Mỗi hoạt động PHẢI có TẤT CẢ các trường sau (không thiếu trường nào):

{{
  "activity_id": "act_{loc_id.replace('loc_', '')}_tên_ngắn_01",
  "location_id": "{loc_id}",
  "name": "Tên hoạt động tiếng Việt ngắn gọn",
  "description": "2-4 câu mô tả chi tiết, hấp dẫn, thực tế. Gợi cảm xúc cho du khách.",
  "tags": ["5-7 tags tiếng Anh từ danh sách chuẩn"],
  "cost": số_nguyên_VND,
  "estimated_duration": số_phút,
  "best_time": ["morning" hoặc "afternoon" hoặc "evening"],
  "suitable_for": ["solo", "couple", "family", "friends"],
  "difficulty": "easy" hoặc "medium" hoặc "hard",
  "season": ["jan", "feb", ... tháng phù hợp nhất],
  "reason_template": "Câu ngắn {'{'}matching_tags{'}'} giải thích tại sao phù hợp"
}}

3. Tags PHẢI chọn từ danh sách: nature, food, culture, adventure, relax, photography, history, sports, shopping, entertainment, health, education, sea, beach, fun, music, family, sightseeing, trekking, mountain, waterfall, cave, island, temple, market, nightlife, romantic, ethnic, village, cycling, kayak, diving, snorkeling, sunrise, sunset, cuisine, local_food, street_food, heritage, architecture, hidden_gem, scenic, wildlife, eco, spiritual, art, craft, unique, motorbiking, road_trip, camping, homestay, experience, flower, lake, river, forest, agriculture, tradition.

4. Chi phí PHẢI ≤ {budget_str} VNĐ. Thời gian PHẢI ≤ {max_time_per_activity} phút. Chi phí 0 cho hoạt động miễn phí.
5. Ưu tiên hoạt động phù hợp sở thích: {tags_str}.
6. Hoạt động PHẢI thực tế, có thể thực hiện tại {location_name}, phản ánh đúng đặc trưng địa phương.
7. Đa dạng: có cả hoạt động miễn phí, budget thấp, và cao cấp.
8. season là danh sách tháng viết tắt 3 chữ cái (jan, feb, mar, ...).
9. reason_template dùng placeholder {{matching_tags}} để cá nhân hóa.

TRẢ LỜI BẰNG JSON ARRAY THUẦN TÚY (không markdown, không giải thích thêm):
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
        # Schema v2: kiểm tra đầy đủ các trường mới
        required_fields = [
            "name", "description", "cost", "estimated_duration", "tags",
            "activity_id", "location_id"
        ]
        optional_fields = [
            "best_time", "suitable_for", "difficulty", "season", "reason_template"
        ]
    else:
        # Schema v1: backward-compatible
        required_fields = ["name", "desc", "cost", "time", "tags"]
        optional_fields = []
    
    # Kiểm tra đủ trường bắt buộc
    for field in required_fields:
        if field not in act:
            logger.warning(f"Activity thiếu trường '{field}': {act.get('name', 'unknown')}")
            return False
    
    # Kiểm tra kiểu dữ liệu cơ bản
    name = act.get("name", "")
    if not isinstance(name, str) or not name.strip():
        return False
    
    desc_field = "description" if schema_v2 else "desc"
    if not isinstance(act.get(desc_field, ""), str):
        return False
    
    if not isinstance(act.get("tags", []), list):
        return False
    
    # Chuẩn hóa cost và time/estimated_duration về số nguyên
    try:
        act["cost"] = int(act["cost"])
        if schema_v2:
            act["estimated_duration"] = int(act["estimated_duration"])
        else:
            act["time"] = int(act["time"])
    except (ValueError, TypeError):
        return False
    
    # Cost không âm, time/duration phải dương
    if act["cost"] < 0:
        return False
    
    time_field = "estimated_duration" if schema_v2 else "time"
    if act[time_field] <= 0:
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


def call_gemini_api(prompt: str, retries: int = 2) -> Optional[str]:
    """Gọi Gemini API, trả về text response hoặc None nếu lỗi. Retry tối đa 2 lần cho lỗi tạm thời."""
    if not is_llm_available():
        return None

    import urllib.request
    import urllib.error
    import time

    url = GEMINI_API_URL.format(model=GEMINI_MODEL, key=GEMINI_API_KEY)
    payload = {
        "system_instruction": {
            "parts": [{"text": "You are a travel expert. Always respond with pure JSON only — no markdown, no code blocks, no explanation. Start your response directly with ["}]
        },
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    data = json.dumps(payload).encode("utf-8")

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")

            logger.warning("Gemini unexpected response format: %s", str(result)[:200])
            return None

        except urllib.error.HTTPError as e:
            if e.code in (503, 529) and attempt < retries:
                wait = 3 * (attempt + 1)
                logger.warning("Gemini %d, retry in %ds (attempt %d/%d)", e.code, wait, attempt + 1, retries)
                time.sleep(wait)
            else:
                logger.error("Gemini API error: %s", e)
                return None
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return None


def generate_from_llm(
    location_name: str,
    location_description: str,
    location_tags: List[str],
    user_tags: List[str],
    budget_per_activity: int,
    max_time_per_activity: int,
    num_activities: int = LLM_ACTIVITIES_PER_CALL,
    schema_v2: bool = True,
    user_text: str = "",
) -> Optional[List[Dict]]:
    """
    Sinh hoạt động du lịch bằng LLM (xAI Grok).
    Trả về schema v2 theo mặc định.
    None nếu LLM không khả dụng hoặc thất bại.
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
        user_text=user_text,
    )

    logger.info("Calling Gemini for location: %s (requesting %d activities)", location_name, num_activities)
    response_text = call_gemini_api(prompt)

    if response_text is None:
        logger.warning("Gemini returned no response for %s", location_name)
        return None

    raw_list = _parse_llm_response(response_text)
    if raw_list is None:
        logger.warning("Failed to parse Gemini response for %s", location_name)
        return None
    
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
        return None

    logger.info("LLM generated %d valid activities for %s", len(valid_activities), location_name)
    return valid_activities