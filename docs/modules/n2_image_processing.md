# Module N2: Xử lý Hình ảnh (Image Processing)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-14  

---

## 1. Vai trò của Module N2

Module N2 đóng vai trò là "đôi mắt" của hệ thống. Thay vì chỉ dựa vào văn bản người dùng nhập, hệ thống cho phép người dùng tải lên hình ảnh minh họa cho địa điểm hoặc không khí mà họ mong muốn. N2 có nhiệm vụ chuyển đổi thông tin thị giác từ hình ảnh thành một mô tả văn bản giàu ngữ nghĩa để đưa vào pipeline tìm kiếm.

---

## 2. Công nghệ cốt lõi: Groq Vision

N2 tận dụng sức mạnh của **Llama 3.2 Vision** thông qua hạ tầng của **Groq**. 

### Tại sao chọn Groq Vision?
1.  **Tốc độ xử lý:** Khả năng inference của Groq giúp việc phân tích hình ảnh diễn ra gần như tức thì, giảm thiểu thời gian chờ đợi của người dùng.
2.  **Khả năng hiểu ngữ cảnh:** Llama 3.2 Vision không chỉ liệt kê các vật thể (như "cái cây", "bãi cát") mà còn hiểu được không khí và loại hình du lịch (như "nghỉ dưỡng sang trọng", "khám phá mạo hiểm").

---

## 3. Chiến lược Tối ưu hóa: Concise Prompting

Một điểm đặc trưng của dự án là việc áp dụng chiến lược **Concise Prompting** (Mô tả súc tích). 

### Quy tắc "Tối đa 50 từ":
Chúng ta ép buộc model chỉ trả về một đoạn văn duy nhất không quá 50 từ. Điều này mang lại 3 lợi ích lớn:
-   **Tiết kiệm Token:** Giảm chi phí API và tăng tốc độ xử lý.
-   **Tăng mật độ ngữ nghĩa (Semantic Density):** Khi bị giới hạn số từ, model buộc phải chọn lọc những từ ngữ đắt giá nhất, giúp vector được tạo ra ở bước N1 "sắc nét" hơn.
-   **Tránh nhiễu:** Loại bỏ các câu dẫn rườm rà (ví dụ: "Trong bức ảnh này tôi thấy...") vốn không mang lại giá trị cho việc tìm kiếm.

---

## 4. Quy trình xử lý Kỹ thuật
 
-   **Tiền xử lý (Pillow):** Tự động chuyển đổi các định dạng ảnh lạ sang **RGB** và nén thành **JPEG** để đảm bảo tương thích và tối ưu băng thông.
-   **Inference (urllib):** Sử dụng thư viện `urllib` thuần (không dependency) để thực hiện request POST tới Groq API.
-   **Concise Prompting:** Áp dụng hệ thống Prompt "Tuyệt đối" để ép model chỉ trả về đoạn văn bản không quá 50 từ, loại bỏ hoàn toàn các lời dẫn thừa.
 
 ---
 
 ## 5. Interface (API nội bộ)
 
 -   **Input:** `{"image": bytes}` — Nhận dữ liệu ảnh dưới dạng nhị phân.
 -   **Output:** `{"img_desc": "...", "usage": {...}}` — Trả về mô tả văn bản và thông tin tiêu tốn token.
 
 ---
 
 ## 6. Các quy tắc "Vàng" trong Prompting
 
 N2 tuân thủ các quy tắc nghiêm ngặt trong System Prompt:
 -   **Không lời dẫn:** Cấm các câu như "Đây là..." hay "Tôi thấy...".
 -   **Không nhiễu:** Cấm mô tả các chi tiết kỹ thuật như biển số xe, nhãn hiệu, ngày tháng.
 -   **Tập trung vào "Vibe":** Ưu tiên các từ ngữ mô tả không khí và loại hình du lịch (Ví dụ: "sang trọng", "hoang sơ").

Module N2 được thiết kế như một đơn vị độc lập với giao diện đơn giản:

-   **Input:** Nhận dữ liệu hình ảnh dưới dạng `bytes`.
-   **Output:** Trả về một `JSON object` chứa mô tả văn bản (`img_desc`) và thông tin sử dụng token.

Thiết kế này cho phép N2 có thể được tích hợp vào bất kỳ pipeline nào mà không phụ thuộc vào logic của các module xử lý phía sau. Mô tả văn bản trả về là một chuỗi ký tự (string) thuần túy, có tính ứng dụng cao cho cả việc hiển thị trực tiếp và xử lý dữ liệu ở các bước tiếp theo.

---

## 7. Tài liệu tham khảo

| # | Chủ đề | Nguồn tham khảo |
|---|---|---|
| 1 | Groq — Vision Documentation | [console.groq.com/docs/vision](https://console.groq.com/docs/vision) |
| 2 | Groq — Danh sách model Vision (Llama-3.2-11b-vision-preview) | [console.groq.com/docs/models](https://console.groq.com/docs/models) |
| 3 | Meta AI — Llama 3.2 Vision | [llama.meta.com/llama3_2](https://llama.meta.com/llama3_2) |
| 4 | Pillow (PIL) — Thư viện xử lý hình ảnh Python | [pillow.readthedocs.io](https://pillow.readthedocs.io/) |
