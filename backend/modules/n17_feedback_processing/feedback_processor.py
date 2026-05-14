import json
import time
import random
from typing import Dict, List, Optional

from config import setup_logging, LLM_MAX_RETRIES, LLM_RETRY_WAIT_BASE
from backend.modules.n5_activity_generation.providers import get_llm_chain
from backend.shared.maps.tags import ALL_TAGS

logger = setup_logging("N17.feedback")

VALID_TAGS = sorted(ALL_TAGS.keys())
VALID_TAGS_SET = set(ALL_TAGS.keys())

def _build_feedback_prompt(user_input: str, user_tags: List[str], img_desc: str, feedback_text: str) -> str:
    tags_str = ", ".join(user_tags) if user_tags else "không có"
    valid_tags_str = ", ".join(VALID_TAGS)
    img_context = f'\n- Mô tả ảnh hiện tại: "{img_desc}"' if img_desc else ""

    prompt = f"""Bạn là chuyên gia điều phối ý định du lịch. 
Dựa trên yêu cầu cũ và phản hồi mới, hãy cập nhật lại TOÀN BỘ thông số tìm kiếm.

THÔNG TIN CŨ:
- Văn bản: "{user_input}"
- Tags: {tags_str}{img_context}

PHẢN HỒI MỚI:
"{feedback_text}"

Nhiệm vụ:
1. Cập nhật "refined_text" để phản ánh ý định mới nhất.
2. Cập nhật "refined_tags" (chọn từ danh sách chuẩn).
3. Cập nhật "refined_img_desc": Nếu người dùng muốn bỏ qua ảnh hoặc thay đổi mô tả ảnh, hãy chỉnh sửa hoặc để trống "".

HÃY TRẢ VỀ JSON:
{{
  "refined_text": "Chuỗi văn bản mới",
  "refined_tags": ["tag1", "..."],
  "refined_img_desc": "Mô tả ảnh mới hoặc để trống nếu muốn bỏ qua ảnh",
  "explanation": "Câu trả lời trực tiếp cho khách hàng bằng tiếng Việt (Ví dụ: 'Vâng, tôi đã cập nhật lại tìm kiếm để ưu tiên các không gian yên tĩnh và gỡ bỏ ảnh cũ cho bạn.')"
}}

DANH SÁCH TAGS CHUẨN:
{valid_tags_str}

QUY TẮC:
- Trả về DUY NHẤT JSON.
- Trường 'explanation' phải là câu thoại tự nhiên, thân thiện, có thể dùng trực tiếp trên UI Chatbot.
- Nếu khách nói "bỏ qua ảnh", hãy xác nhận việc đó trong câu trả lời.


TRẢ LỜI:
"""
    return prompt

def _parse_feedback_response(response_text: str) -> Optional[Dict]:
    if not response_text or not response_text.strip():
        return None
    
    text = response_text.strip()
    
    # Extract JSON
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            # Ensure required keys exist
            for key in ["refined_text", "refined_tags"]:
                if key not in data: return None
            return data
        except: pass
    
    return None

def call_llm(
    prompt: str,
    retries: int = LLM_MAX_RETRIES,
    chain_override: Optional[str] = None,
    temperature: float = 0.1,
) -> tuple:
    """Pattern tương tự N5: Iterative chain call with retries."""
    chain = get_llm_chain(chain_str=chain_override) if chain_override else get_llm_chain()
    if not chain:
        logger.warning("No LLM provider available for N17")
        return None, None, None, None

    for pass_idx in range(retries + 1):
        for provider in chain:
            logger.info("N17 trying provider=%s model=%s (pass %d)", provider.name, provider.model, pass_idx + 1)
            result = provider.generate(prompt, retries=0, temperature=temperature, max_tokens=2000)
            if result:
                return result, provider.name, provider.model, getattr(provider, "last_usage", None)
            
        if pass_idx < retries:
            wait = min(60.0, (LLM_RETRY_WAIT_BASE * (3 ** pass_idx)) + random.random())
            time.sleep(wait)

    return None, None, None, None

def process_feedback(
    user_input: str, 
    user_tags: List[str], 
    img_desc: str,
    feedback_text: str,
    llm_chain: Optional[str] = None
) -> Dict:
    """Xử lý feedback và trả về input đã tinh chỉnh."""
    prompt = _build_feedback_prompt(user_input, user_tags, img_desc, feedback_text)
    
    res_text, provider, model, usage = call_llm(prompt, chain_override=llm_chain)
    
    if res_text:
        parsed = _parse_feedback_response(res_text)
        if parsed:
            # Validate tags
            tags = parsed.get("refined_tags", [])
            if isinstance(tags, list):
                parsed["refined_tags"] = [t for t in tags if t in VALID_TAGS_SET]
            # Ensure refined_img_desc exists
            if "refined_img_desc" not in parsed:
                parsed["refined_img_desc"] = img_desc
            return parsed

    # Fallback
    return {
        "refined_text": f"{user_input}. {feedback_text}",
        "refined_tags": user_tags,
        "refined_img_desc": img_desc,
        "explanation": "Sử dụng fallback do lỗi LLM hoặc parse."
    }

