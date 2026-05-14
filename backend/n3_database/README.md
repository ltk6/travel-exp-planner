# N3 — Database Layer (Cloud-Native Edition)

Module này quản lý việc lưu trữ bền vững cho toàn bộ hệ thống. N3 không chỉ lưu trữ văn bản và vector mà còn đóng vai trò là một **Binary Asset Server** lưu trữ hình ảnh trực tiếp trong PostgreSQL.

## 🌟 Tính năng chính
- **Atomic Image Persistence:** Hình ảnh được lưu dưới dạng mảng `BYTEA[]` trực tiếp trong Database, đảm bảo tính nhất quán dữ liệu tuyệt đối.
- **Smart Fingerprinting:** Cung cấp cơ chế "Dấu vân tay" để N8 Orchestrator kiểm tra phiên bản dữ liệu cực nhanh mà không cần query nặng.
- **pgvector Integration:** Lưu trữ và hỗ trợ tìm kiếm vector 1024 chiều phục vụ cho Semantic Search.
- **Distributed Simulation Ready:** Thiết kế sẵn sàng cho việc tách Server hoặc triển khai lên các nền tảng Cloud như Hugging Face.

## 🛠️ APIs Quan trọng
- `init_db()`: Khởi tạo Schema và Extension.
- `save_location(data)`: Lưu địa điểm kèm ảnh nhị phân (`images_binary`).
- `get_all_locations(include_images=True)`: Truy xuất dữ liệu, tự động chuyển đổi Binary sang Base64 cho tầng điều phối.
- `get_db_fingerprint()`: Trả về hash trạng thái hiện tại của DB.

---
**Ghi chú:** Khi triển khai Cloud, chỉ cần một file Backup SQL duy nhất là có thể khôi phục toàn bộ hệ thống bao gồm cả hình ảnh.
