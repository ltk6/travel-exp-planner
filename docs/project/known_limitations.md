# Hạn Chế Đã Biết (Known Limitations)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-14  

---

## 1. Giới hạn Rate Limit (Groq Free Tier)

Đây là hạn chế lớn nhất ảnh hưởng đến hiệu suất hệ thống trong môi trường thử nghiệm.

*   **Vấn đề:** Groq Free Tier áp dụng giới hạn RPM (Requests Per Minute) và TPM (Tokens Per Minute) khá chặt chẽ cho từng model (ví dụ: 30 RPM).
*   **Hệ quả:** Khi chạy benchmarking hoặc khi nhiều người dùng cùng truy cập, các model đầu chuỗi (như `gpt_120b`) dễ bị lỗi `fail_429`.
*   **Giải pháp hiện tại:** Hệ thống sử dụng **Multi-model Failover Chain** để tự động chuyển sang model tiếp theo trong danh sách. Tuy nhiên, nếu toàn bộ chain bị limit, hệ thống sẽ phải đợi theo cơ chế exponential backoff.

## 2. Rủi ro Truncation và JSON Parsing (N5)

Các model LLM cỡ nhỏ đôi khi không hoàn thành được cấu trúc JSON phức tạp.

*   **Vấn đề:** Các model như `gpt_20b` hoặc `gpt_safeguard` thường bị cắt ngang (truncate) ở ngưỡng 4000 tokens hoặc do giới hạn context window.
*   **Hệ quả:** Output trả về bị thiếu dấu đóng ngoặc `]}` khiến JSON không hợp lệ.
*   **Giải pháp hiện tại:** 
    *   Sử dụng `response_format: {"type": "json_object"}` ở tầng API.
    *   Tích hợp bộ parser **Auto-Repair** để khôi phục các object hợp lệ cuối cùng trước điểm bị cắt.

## 3. Độ trễ Embedding Cục bộ (N1 Latency for Activities)

Khác với các địa điểm đã được nhúng sẵn trong DB, các hoạt động từ N5 được sinh ra theo thời gian thực và cần được nhúng (embed) ngay lập tức để N6 có thể xếp hạng.

*   **Vấn đề:** Model **BGE-M3** là một mô hình lớn (1024D). Việc nhúng cùng lúc 10-20 hoạt động mới (Batch Mode) tiêu tốn đáng kể tài nguyên CPU/RAM.
*   **Hệ quả:** Trong môi trường có cấu hình thấp (như Hugging Face Free CPU), bước nhúng này có thể mất từ 2-5 giây, tạo ra "nút thắt cổ chai" (bottleneck) ngay sau khi LLM đã trả về kết quả.
*   **Giải pháp hiện tại:** 
    *   Sử dụng `embed_batch` để tối ưu hóa việc tính toán song song trên vector engine.
    *   Giới hạn số lượng hoạt động sinh ra (`target_count`) để cân bằng giữa độ phong phú và tốc độ phản hồi.

## Tổng Kết Hạn Chế

| Module | Hạn chế chính | Mức độ ảnh hưởng |
|--------|--------------|-----------------|
| **N5** | Rate limit (429) & Truncation | **Rất Cao** |
| **N1** | Độ trễ khi nhúng hoạt động động | **Trung Bình** |
