# Travel Experience Planner

Hệ thống lập kế hoạch du lịch sử dụng semantic retrieval, multimodal input và LLM.  
Giao diện người dùng được xây dựng bằng **Next.js**, backend API chạy trên **Flask (N8)**.

## Khởi động nhanh

### Yêu cầu

- Python 3.10+
- Node.js 18+ và npm
- PostgreSQL (với pgvector extension)

### Cấu hình môi trường

```bash
cp .env.example .env
# Mở .env và điền các biến: PG_URI, OPENAI_API_KEY, GEMINI_API_KEY, v.v.
```

### Chạy trên Windows

```bat
run.bat
```

- Tự động tạo và kích hoạt Python venv
- Cài đặt Python dependencies từ `requirements.txt` (bỏ qua nếu đã có)
- Cài đặt Node.js dependencies cho Next.js (bỏ qua nếu đã có)
- Khởi động backend trên `:5000` và frontend trên `:3000`
- Tự động mở trình duyệt tại `http://localhost:3000`
- Fallback Streamlit cũ: `legacy_run.bat`

### Chạy trên Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

- Tương tự `run.bat` nhưng dành cho Unix shell
- Backend log: `backend.log`, Frontend log: `frontend.log`
- Nhấn `Ctrl+C` để dừng toàn bộ services

### Sau khi khởi động

| Service | URL |
|---|---|
| **Frontend (Next.js)** | http://localhost:3000 |
| **Backend API** | http://localhost:5000 |
| **Health check** | http://localhost:5000/health |

## Kiến trúc

Hệ thống được chia thành các module độc lập (N0–N17), mỗi module có contract Pydantic V2 riêng xác định input/output tại ranh giới module:

| Module | Chức năng |
|---|---|
| N1 | Embedding (BGE-M3, multi-channel) |
| N2 | Image processing → text description |
| N3 | PostgreSQL persistence (locations, activities, users, history) |
| N4 | Location ranking (cosine similarity) |
| N5 | Activity generation (LLM fallback) |
| N6 | Activity ranking (semantic + attribute) |
| N8 | API orchestrator (Flask) |
| N16 | Frontend (Next.js + Zustand) |
| N17 | Feedback processing |

## Tài liệu

Tài liệu kỹ thuật được tổ chức trong thư mục [`docs/`](docs/README.md).

Nên bắt đầu từ:

- [docs/README.md](docs/README.md)
- [docs/architecture/system_overview.md](docs/architecture/system_overview.md)

## Thành viên

| Họ và tên | MSSV |
| :--- | :--- |
| Huỳnh Huy Hoàng | 24120181 |
| Nguyễn Thanh Hải | 24120302 |
| Lâm Tuấn Khanh | 24120337 |
| Hoàng Lê Đăng Khoa | 24120343 |
| Phan Lê Thành Nhân | 24120400 |
| Chu Văn Thái | 24120440 |
| Nguyễn Việt Thắng | 24120444 |
| Trương Huệ Trí | 24120472 |
