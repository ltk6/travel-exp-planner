import json
import base64
import urllib.request
from PIL import Image
import io
from config import GROQ_API_KEY, GROQ_VISION_MODEL, GROQ_API_URL, USER_AGENT, setup_logging
logger = setup_logging("N2")

from typing import Union
from backend.shared.contracts.n2_contracts import N2ImageInput

def process_image(data: Union[N2ImageInput, dict]) -> dict:
    """
    The sole public API function of Module N2 (image processing).
    Uses Groq Vision (Llama 3.2 Vision).
    Input:  {"image": bytes}
    Output: {"img_desc": "..."}
    """
    validated = N2ImageInput.model_validate(data) if isinstance(data, dict) else data
    image_bytes = validated.image
    if not image_bytes:
        logger.warning("No image provided to N2")
        return {
            "img_desc": "",
            "error": "No image provided"
        }


    logger.info(f"Processing image ({len(image_bytes)} bytes) via Groq Vision...")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Optimize for Vision API: Downscale if too large and compress
        img.thumbnail((1560, 1560)) 
        
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        logger.info(f"Image optimized: {len(buffer.getvalue())} bytes (original: {len(image_bytes)})")

        prompt = """
        Bạn là chuyên gia mô tả địa điểm du lịch.
        Quan sát ảnh và viết MỘT đoạn văn ngắn gọn, súc tích, giàu tính gợi hình bằng Tiếng Việt.

        YÊU CẦU TUYỆT ĐỐI:
        - Tối đa 50 từ — KHÔNG được vượt quá.
        - Nêu rõ: loại địa điểm, đặc điểm nổi bật nhất, cảm xúc/không khí.
        - Dùng ngôn ngữ biểu cảm, chọn lọc (không liệt kê dài dòng).
        - KHÔNG dùng lời dẫn 'Trong ảnh có...' hay 'Tôi thấy...'.
        - KHÔNG mô tả biển số xe, nhãn hiệu, ngày giờ.
        - Chỉ trả về đoạn văn, không giải thích thêm.
        """

        payload = {
            "model": GROQ_VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    }
                ]
            }],
            "max_tokens": 300,
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            GROQ_API_URL, data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": USER_AGENT,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        logger.info(f"N2 usage: {prompt_tokens} prompt tokens, {completion_tokens} completion tokens.")

        choices = result.get("choices", [])
        if not choices:
            return {"img_desc": "", "error": "Empty response from model"}

        text = choices[0].get("message", {}).get("content", "")
        if not text:
            return {"img_desc": "", "error": "No text returned (possible safety block or invalid image)"}

        metadata = {
            "model": GROQ_VISION_MODEL,
            "usage": {
                "prompt_tokens":     prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens":      prompt_tokens + completion_tokens,
            },
        }

        return {
            "img_desc": text.strip(),
            "metadata": metadata,
        }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        logger.error(f"HTTPError in N2 image processing: {e.code} - {error_body}")
        return {
            "img_desc": "", 
            "error": f"HTTPError: {e.code} - {error_body}",
            "metadata": {"model": GROQ_VISION_MODEL, "usage": {}}
        }
    except Exception as e:
        logger.exception(f"Exception in N2 image processing: {e}")
        return {
            "img_desc": "",
            "error": str(e),
            "metadata": {"model": GROQ_VISION_MODEL, "usage": {}}
        }
