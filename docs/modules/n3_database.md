# Module N3: Lưu trữ và Quản lý Dữ liệu (Database)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-14  

---

## 1. Vai trò của Module N3

Module N3 là lớp lưu trữ dữ liệu (Data Layer) của hệ thống. Nhiệm vụ chính của nó là quản lý thông tin chi tiết về các địa điểm du lịch, bao gồm thông tin mô tả, tọa độ địa lý, hình ảnh và đặc biệt là các **Vector nhúng (Embeddings)** phục vụ cho tìm kiếm ngữ nghĩa.

---

## 2. Công nghệ cốt lõi: PostgreSQL + pgvector

Hệ thống sử dụng **PostgreSQL** kết hợp với extension **pgvector** để xử lý dữ liệu vector một cách hiệu quả ngay trong lòng một database quan hệ.

### Tại sao chọn pgvector?
1.  **Dữ liệu hợp nhất:** Cho phép lưu trữ cả metadata (JSONB) và vector trong cùng một bản ghi.
2.  **Truy vấn vector mạnh mẽ:** Hỗ trợ tính toán khoảng cách Cosine (`<=>`) trực tiếp bằng SQL, giúp tối ưu hóa hiệu suất khi quy mô dữ liệu lớn.
3.  **Tính ổn định:** Tận dụng độ tin cậy của PostgreSQL trong việc quản lý giao dịch và toàn vẹn dữ liệu.

---

## 3. Cấu trúc dữ liệu Địa điểm (Schema)

Mỗi bản ghi địa điểm bao gồm:
-   **Metadata:** Tên, mô tả, danh sách tags đặc trưng.
-   **Địa lý:** Tọa độ GPS (Lat/Lng).
-   **Hình ảnh:** Danh sách URL hình ảnh đại diện.
-   **Vectors:** Các kênh vector đã được tính toán sẵn (Text vector, Tag vector).

---

## 4. Persistence & Sync Strategy

Module N3 đóng vai trò là **Single Source of Truth** cho toàn bộ hệ thống:

- **Atomic Storage:** Toàn bộ dữ liệu (Vectors, Metadata, Geo, Images) được lưu trữ nguyên tử trong PostgreSQL. 
- **Binary Image Persistence:** Hình ảnh được lưu dưới dạng `BYTEA[]`, loại bỏ sự phụ thuộc vào hệ thống file cục bộ của server, cho phép di chuyển DB linh hoạt (Cloud-Native).
- **Smart Fingerprinting:** N3 cung cấp API trả về "Dấu vân tay" (dựa trên Row Count và Max Update Timestamp). Cơ chế này giúp tầng N8 Orchestrator đưa ra quyết định đồng bộ hóa (Sync) chỉ khi dữ liệu thực sự thay đổi.
- **Base64 Decoupling:** Mặc dù lưu trữ nhị phân, N3 vẫn trả về ảnh dạng Base64 qua API để giữ cho các module tiêu thụ (N8, N7) không cần thay đổi logic xử lý hình ảnh.

---

## 5. Cơ chế Dự phòng (Fail-soft Mechanism)

Để đảm bảo hệ thống luôn hoạt động ngay cả trong môi trường không có Database thực (như khi phát triển local hoặc demo nhanh), N3 tích hợp cơ chế **JSON Seed Fallback**:
-   Nếu kết nối PostgreSQL thất bại, hệ thống tự động chuyển sang đọc dữ liệu từ tệp `seeds/locations_with_vectors.json`.
-   Dữ liệu trong tệp seed được cấu trúc giống hệt database, đảm bảo logic của các bước sau không bị ảnh hưởng.

---

## 6. Giao diện (Interface)

Module N3 hoạt động như một nhà cung cấp dữ liệu độc lập:
-   **Input:** Yêu cầu truy vấn hoặc filter (nếu có).
-   **Process:** Kết nối DB (hoặc JSON), trích xuất và định dạng dữ liệu.
-   **Output:** Danh sách các `Location Objects` đầy đủ thông tin metadata và vectors.

---

## 6. Tài liệu tham khảo

| # | Chủ đề | Nguồn tham khảo |
|---|---|---|
| 1 | pgvector GitHub — Open-source vector similarity search for Postgres | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| 2 | pgvector — Distance functions (cosine, L2, inner product) | [github.com/pgvector/pgvector#distance](https://github.com/pgvector/pgvector#distance) |
| 3 | PostgreSQL Documentation — JSONB và GIN Index | [www.postgresql.org/docs](https://www.postgresql.org/docs/) |
| 4 | Supabase — OpenAI Embeddings & Postgres Vector | [supabase.com/blog/openai-embeddings-postgres-vector](https://supabase.com/blog/openai-embeddings-postgres-vector) |
