import json
import time
import random
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Union
from backend.shared.contracts.n17_contracts import N17FeedbackInput

from config import (
    setup_logging, 
    LLM_MAX_RETRIES, 
    LLM_RETRY_WAIT_BASE,
    GROQ_API_KEY, 
    GROQ_API_URL, 
    GROQ_MODEL_NAME, 
    GROQ_MODELS,
    USER_AGENT
)
from backend.shared.maps.tags import ALL_TAGS

logger = setup_logging("N17.processor")

VALID_TAGS = sorted(ALL_TAGS.keys())
VALID_TAGS_SET = set(ALL_TAGS.keys())

def call_groq_direct(prompt: str, system: str = "You are a travel expert. Respond with pure JSON only.", model: str = None) -> tuple:
    """Bare logic to call Groq without complex provider registry."""
    target_model = GROQ_MODELS.get(model, model) if model else GROQ_MODEL_NAME
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": USER_AGENT,
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            content = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = res.get("usage", {})
            return content, target_model, usage
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except:
            body = str(e)
        logger.error(f"Groq HTTP Error {e.code}: {body}")
        return None, None, {}
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return None, None, {}

def _build_feedback_prompt(user_input: str, user_tags: List[str], img_desc: str, feedback_text: str) -> str:
    tags_str = ", ".join(user_tags) if user_tags else "không có"
    valid_tags_str = ", ".join(VALID_TAGS)
    img_context = f'\n- Mô tả ảnh hiện tại: "{img_desc}"' if img_desc else ""

    prompt = f"""Bạn là chuyên gia điều phối ý định du lịch và xử lý các ràng buộc phủ định (loại trừ sở thích).
Dựa trên yêu cầu cũ và phản hồi mới, hãy cập nhật lại TOÀN BỘ thông số tìm kiếm.

THÔNG TIN CŨ:
- Văn bản: "{user_input}"
- Tags: {tags_str}{img_context}

PHẢN HỒI MỚI:
"{feedback_text}"

Nhiệm vụ:
1. Cập nhật "refined_text": Phản ánh ý định mới nhất. 
   - QUAN TRỌNG: Chỉ thay đổi loại hình địa điểm/chủ đề cốt lõi (ví dụ: chuyển từ du lịch biển sang núi rừng) nếu người dùng THỂ HIỆN RÕ RÀNG là họ muốn từ bỏ hoặc không đi biển nữa (ví dụ: "không muốn đi biển nữa", "thay đổi đi núi"). Nếu người dùng chỉ phàn nàn về trạng thái/tính chất (ví dụ: mệt mỏi, ồn ào, đông đúc) nhưng vẫn trong ngữ cảnh cũ, hãy GIỮ NGUYÊN loại địa điểm cốt lõi (ví dụ: vẫn là đi biển) nhưng thay đổi tính chất sang hướng tích cực tương ứng (ví dụ: bãi biển yên bình, vắng vẻ, hoang sơ, thư giãn).
   - Tuyệt đối KHÔNG đưa trực tiếp các từ khóa phủ định/bị cấm đó vào "refined_text" (ví dụ: KHÔNG viết "không muốn đi biển", "không muốn ồn ào", "no beach", "no crowd").
   - Thay vào đó, hãy viết lại bằng các cụm từ mô tả TÍCH CỰC tương ứng:
     * Nếu thực sự từ bỏ biển để đi núi/rừng: viết "du lịch vùng núi rừng, cao nguyên, khí hậu mát mẻ, khám phá đồi chè".
     * Nếu vẫn đi biển nhưng muốn yên tĩnh/tránh đông đúc/tránh ồn ào: viết "du lịch biển hoang sơ, yên bình, bãi biển vắng vẻ, không gian thư giãn tĩnh lặng, nghỉ dưỡng nhẹ nhàng".
2. Cập nhật "refined_tags": Chọn DUY NHẤT các key tiếng Anh từ danh sách chuẩn bên dưới.
   - QUAN TRỌNG: Nếu người dùng loại trừ một chủ đề/địa điểm (ví dụ: "không đi biển"), hãy loại bỏ các tag liên quan (ví dụ: "beach", "island"). Nếu người dùng vẫn đi biển nhưng muốn yên tĩnh, hãy giữ tag "beach", "island" nhưng loại bỏ các tag náo nhiệt ("party", "nightlife", "bar") và thêm các tag như "peaceful", "nature", "resort".
3. Cập nhật "refined_img_desc": Nếu người dùng muốn bỏ qua ảnh, hãy để trống chuỗi rỗng "" (tuyệt đối không ghi 'Bỏ qua ảnh'). Nếu muốn thay đổi mô tả ảnh, hãy cập nhật mô tả mới.

QUAN TRỌNG VỀ PHẢN HỒI VÔ NGHĨA / KHÔNG PHÙ HỢP (WEIRD/SPAM/IRRELEVANT FEEDBACKS):
- Nếu phản hồi mới ("{feedback_text}") là vô nghĩa, spam, ký tự vô nghĩa (ví dụ: "asdasd", "qweqwe", "123123"), hoặc hoàn toàn không liên quan gì đến việc lập kế hoạch du lịch, địa điểm du lịch, sở thích đi lại:
  * Tuyệt đối KHÔNG thay đổi gì cả.
  * Giữ nguyên giá trị cũ: 'refined_text' PHẢI là "{user_input}", 'refined_tags' PHẢI là chính xác danh sách cũ [{tags_str}], và 'refined_img_desc' PHẢI là "{img_desc}".
  * Trong trường 'explanation', trả về một câu phản hồi lịch sự, thân thiện bằng tiếng Việt giải thích rằng hệ thống không hiểu rõ yêu cầu này và mong muốn khách hàng mô tả rõ ràng hơn về sở thích, địa điểm hoặc yêu cầu điều chỉnh lộ trình du lịch (Ví dụ: "Xin lỗi, tôi chưa hiểu rõ yêu cầu này của bạn. Bạn có thể chia sẻ cụ thể hơn về những mong muốn điều chỉnh cho chuyến đi không?").

HÃY TRẢ VỀ JSON:
{{
  "refined_text": "Chuỗi văn bản mới (hoặc giữ nguyên u_input nếu feedback vô nghĩa)",
  "refined_tags": ["tag1", "..."],
  "refined_img_desc": "Mô tả ảnh mới hoặc để trống/giữ nguyên",
  "explanation": "Câu thoại tiếng Việt trực tiếp giải thích sự thay đổi hoặc phản hồi lịch sự nếu feedback vô nghĩa"
}}

DANH SÁCH TAGS CHUẨN:
{valid_tags_str}

QUY TẮC:
- Trả về DUY NHẤT JSON.
- Trường 'explanation' phải là câu thoại tự nhiên, thân thiện, có thể dùng trực tiếp trên UI Chatbot.
- Nếu khách nói "bỏ qua ảnh", trường 'refined_img_desc' PHẢI là "" và xác nhận việc đó trong câu trả lời.
- Số lượng 'refined_tags' nên từ 3 đến 6 tags quan trọng nhất phản ánh đúng ý định mới.


TRẢ LỜI:
"""
    return prompt

def _parse_feedback_response(response_text: str) -> Optional[Dict]:
    if not response_text or not response_text.strip():
        return None
    
    text = response_text.strip()
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
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
    """Barebones LLM call directly to Groq with chain support."""
    from config import LLM_CHAIN
    
    # Resolve models to try
    if chain_override:
        models_to_try = [chain_override]
    else:
        models_to_try = [m.strip() for m in LLM_CHAIN.split(",") if m.strip()]
        if not models_to_try:
            models_to_try = [GROQ_MODEL_NAME]

    for attempt in range(retries + 1):
        if attempt > 0:
            # Entire chain failed, wait before retrying the entire chain
            wait_time = min(60.0, (LLM_RETRY_WAIT_BASE * (3 ** (attempt - 1))) + random.random())
            logger.info(f"Pass {attempt} failed for all models. Retrying entire chain in {wait_time:.2f}s...")
            time.sleep(wait_time)

        for model_alias in models_to_try:
            res_text, model, usage = call_groq_direct(prompt, model=model_alias)
            if res_text:
                return res_text, "groq", model, usage
            
            logger.warning(f"Model {model_alias} failed in pass {attempt + 1}")
        
    return None, None, None, None

def process_feedback(
    user_input: Union[N17FeedbackInput, dict, str], 
    user_tags: Optional[List[str]] = None, 
    img_desc: str = "",
    feedback_text: str = "",
    llm_chain: Optional[str] = None
) -> Dict:
    """Xử lý feedback và trả về input đã tinh chỉnh kèm metadata."""
    if isinstance(user_input, (N17FeedbackInput, dict)):
        validated = N17FeedbackInput.model_validate(user_input) if isinstance(user_input, dict) else user_input
        u_input = validated.user_input
        u_tags = validated.user_tags
        u_img_desc = validated.img_desc
        f_text = validated.feedback_text
        chain = validated.llm_chain
    else:
        u_input = user_input
        u_tags = user_tags if user_tags is not None else []
        u_img_desc = img_desc
        f_text = feedback_text
        chain = llm_chain

    logger.info("N17 — Start processing feedback. Feedback length: %d chars", len(f_text))
    prompt = _build_feedback_prompt(u_input, u_tags, u_img_desc, f_text)
    res_text, provider, model, usage = call_llm(prompt, chain_override=chain)
    
    metadata = {
        "model": model,
        "provider": provider,
        "usage": usage
    }

    if res_text:
        parsed = _parse_feedback_response(res_text)
        if parsed:
            tags = parsed.get("refined_tags", [])
            if isinstance(tags, list):
                parsed["refined_tags"] = [t.lower().strip() for t in tags if isinstance(t, str) and t.lower().strip() in VALID_TAGS_SET][:8]
            if "refined_img_desc" not in parsed:
                parsed["refined_img_desc"] = u_img_desc
            
            logger.info("N17 — Feedback processed successfully. Refined text: '%s'", parsed.get("refined_text"))
            parsed["metadata"] = metadata
            return parsed

    logger.warning("N17 — Failed to parse LLM feedback response. Using fallback.")
    return {
        "refined_text": f"{u_input}. {f_text}",
        "refined_tags": u_tags,
        "refined_img_desc": u_img_desc,
        "explanation": "Sử dụng fallback do lỗi LLM hoặc parse.",
        "metadata": metadata
    }

