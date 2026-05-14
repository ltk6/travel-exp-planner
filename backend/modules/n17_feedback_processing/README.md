# N17: Feedback Chatbot

Module xử lý phản hồi từ người dùng để cải thiện kết quả gợi ý.

## Chức năng
- Nhận đầu vào hiện tại và phản hồi văn bản của người dùng.
- Sử dụng LLM để phân tích phản hồi.
- Cập nhật yêu cầu tìm kiếm (văn bản và tags) để tinh chỉnh kết quả.

## Luồng xử lý
1. Tiếp nhận `user_input` + `feedback`.
2. LLM trích xuất các ý định mới hoặc thay đổi sở thích.
3. Trả về `refined_input` để N8 thực hiện tìm kiếm lại.
