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
        [Context]: Bạn là một Travel Blogger chuyên nghiệp và chuyên gia văn hóa du lịch. 
        [Task]: Hãy quan sát hình ảnh và viết một bài mô tả giàu tính gợi hình, chi tiết và đầy cảm hứng để giới thiệu địa điểm này cho hệ thống gợi ý du lịch thông minh.

        [Guidelines]: Hãy viết văn thật dài, lôi cuốn và đi sâu vào từng ngóc ngách của bức ảnh theo 3 trụ cột:
        1. Loại hình & Bối cảnh: Xác định rõ địa danh (ví dụ: bãi biển thơ mộng, đền đài cổ kính, con phố hiện đại...). Hãy tả về quy mô và sự sắp đặt của các vật thể trong không gian.
        2. Kiến trúc & Cảnh quan: Phân tích sâu về phong cách thiết kế, đường nét kiến trúc, chất liệu, màu sắc chủ đạo và sự giao thoa giữa con người với thiên nhiên.
        3. Cảm xúc & Linh hồn: Tả về 'vibe' (không khí) mà nơi này mang lại. Là sự tĩnh mịch của thời gian, sự hùng vĩ của tạo hóa hay nhịp sống hối hả, năng động?

        [Narrative Enhancement]: 
        - Hãy dùng những từ ngữ giàu tính biểu cảm, ví von (ví dụ: 'như một viên ngọc ẩn mình', 'trầm mặc dưới làn sương', 'bừng sáng giữa lòng đô thị').
        - Loại bỏ hoàn toàn lời dẫn 'Trong ảnh có...' hay 'Tôi thấy...'. Hãy bắt đầu bài viết một cách trực diện và nghệ thuật.

        [Noise Reduction]: 
        - Tuyệt đối KHÔNG mô tả các chi tiết rác như: biển số xe, nhãn hiệu đồ dùng cá nhân, ngày giờ in trên ảnh, hoặc các nhiễu động kỹ thuật.

        [Format Enforcement]: 
        - Kết quả phải là một bài văn hoàn chỉnh, chia làm nhiều đoạn văn (tối thiểu 3 đoạn).
        - KHÔNG giới hạn số câu. Viết càng chi tiết, sâu sắc càng tốt (Khuyến khích trên 200 từ).
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
