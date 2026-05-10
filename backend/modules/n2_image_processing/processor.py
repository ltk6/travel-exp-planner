import json
import base64
import urllib.request
from PIL import Image
import io
from config.settings import XAI_API_KEY
import logging

XAI_VISION_MODEL = "grok-2-vision-1212"
XAI_API_URL = "https://api.x.ai/v1/chat/completions"

logger = logging.getLogger("N2")

def process_image(data: dict) -> dict:
    """
    Hàm xử lý ảnh duy nhất (Public API) của Module N2
    Input: {"image": bytes}
    Output: {"img_desc": "..."}
    """
    image_bytes = data.get("image")
    if not image_bytes:
        logger.warning("No image provided to N2")
        return {
            "img_desc": "",
            "error": "No image provided"
        }


    logger.info(f"Processing image ({len(image_bytes)} bytes) via Gemini...")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        prompt = """
        [Context]: Bạn là một chuyên gia phân tích dữ liệu du lịch chuyên nghiệp.
        [Task]: Hãy phân tích hình ảnh được cung cấp để trích xuất các đặc trưng ngữ nghĩa phục vụ cho hệ thống gợi ý điểm đến.

        [Constraints]: Đoạn mô tả phải tập trung vào 3 yếu tố cốt lõi:
        1. Loại hình địa điểm (Ví dụ: bãi biển, đền chùa, quán cafe, công viên...).
        2. Kiến trúc hoặc Cảnh quan (Ví dụ: phong cách hiện đại, cổ kính, rừng nguyên sinh...).
        3. Không khí mang lại (Ví dụ: yên bình, náo nhiệt, hùng vĩ, ấm cúng...).

        [Noise Reduction]:
        - Tuyệt đối KHÔNG mô tả các chi tiết vụn vặt không liên quan đến du lịch như: biển số xe, màu sắc trang phục của người đi đường, nhãn hiệu đồ dùng cá nhân, hoặc các nhiễu động trong khung hình.
        - Không có lời dẫn (ví dụ: "Trong ảnh là...", "Tôi thấy...") và không có lời kết.

        [Format Enforcement]:
        - Kết quả phải là MỘT ĐOẠN VĂN DUY NHẤT.
        - Độ dài tối đa từ 2 ĐẾN 3 CÂU.
        - Ngôn ngữ: Tiếng Việt.
        """

        payload = {
            "model": XAI_VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}",
                            "detail": "high"
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }],
            "max_tokens": 256,
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            XAI_API_URL, data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {XAI_API_KEY}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        choices = result.get("choices", [])
        if not choices:
            return {"img_desc": "", "error": "Empty response from model"}

        text = choices[0].get("message", {}).get("content", "")
        if not text:
            return {"img_desc": "", "error": "No text returned (possible safety block or invalid image)"}

        return {"img_desc": text.strip()}

    except Exception as e:
        logger.exception(f"Exception in N2 image processing: {e}")
        return {
            "img_desc": "",
            "error": str(e)
        }
