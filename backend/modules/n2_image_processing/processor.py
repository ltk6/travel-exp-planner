import google.generativeai as genai
from PIL import Image
import io
from config.settings import GEMINI_API_KEY
import logging

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

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
        # Xử lý ảnh
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')

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
        
        result = model.generate_content([prompt, img])
        
        # Trả về đúng định dạng dict yêu cầu
        if not result:
            logger.error("Empty response from Gemini")
            return {
                "img_desc": "",
                "error": "Empty response from model"
            }

        if not hasattr(result, "text") or not result.text:
            logger.error("No text returned from Gemini (possible safety block)")
            return {
                "img_desc": "",
                "error": "No text returned (possible safety block or invalid image)"
            }

        img_desc = result.text.strip()
        logger.info(f"Gemini image description: {img_desc[:100]}...")
        return {
            "img_desc": img_desc
        }

    except Exception as e:
        logger.exception(f"Exception in N2 image processing: {e}")
        return {
            "img_desc": "",
            "error": str(e)
        }