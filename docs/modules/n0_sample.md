# Module N0: Khởi tạo Module (Mẫu tham chiếu)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-21

---

## 1. Vai trò của Module N0

N0 không phải là một module chứa logic nghiệp vụ thực tế của hệ thống. Đây là một **module mẫu (boilerplate/reference)** được thiết kế để chuẩn hóa cách khởi tạo các module mới.

Giá trị của N0 không nằm ở logic tính toán, mà ở việc nó đóng vai trò như một "khung tham chiếu kiến trúc" cho:

- Cấu trúc thư mục chuẩn
- Cách export API công khai (`__init__.py`)
- Cơ chế xác thực đầu vào bằng Pydantic
- Khung phản hồi dữ liệu (response envelope) thống nhất
- Cách viết tài liệu module

Trong bối cảnh một hệ thống module hóa phân tán, N0 giúp giữ cho các thành phần do nhiều người phát triển không bị phân mảnh về phong cách code.

---

## 2. Tư tưởng thiết kế: Convention over Configuration

### 2.1. Vì sao cần module mẫu thay vì tài liệu hướng dẫn?

Tài liệu bằng văn bản (guideline) thường khó đảm bảo tính tuân thủ tuyệt đối và dễ bị lạc hậu. Một module mẫu bằng code thật mang lại lợi thế:

- **Có thể sao chép ngay lập tức:** giảm thao tác thủ công, tiết kiệm thời gian bootstrap
- **Minh họa bằng hành động:** code mẫu tự giải thích rõ ràng cấu trúc dữ liệu
- **Dễ dàng onboarding:** người mới có thể đọc N0 để hiểu nhanh về contract của hệ thống

### 2.2. N0 minh họa mẫu thiết kế nào?

N0 hiện thực hóa một vòng đời chuẩn của một API chức năng:

1. Nhận payload từ bên ngoài (thường là `dict`)
2. Validate và chuẩn hóa ngay tại biên giới module (Pydantic models)
3. Xử lý nghiệp vụ bên trong
4. Gói kết quả vào envelope (`status`, `data`, `metadata`, `error`)

---

## 3. Cấu trúc module

```
backend/modules/n0_sample/
├── __init__.py          # Export hàm API chính `run_sample`
├── sample_logic.py      # Nơi chứa logic nghiệp vụ cốt lõi
└── requirements.txt     # Các thư viện phụ thuộc cục bộ
```

---

## 4. API công khai

```python
from modules.n0_sample import run_sample

run_sample(data: dict[str, Any]) -> dict[str, Any]
```

---

## 5. Contract đầu vào và đầu ra

### 5.1. Đầu vào (Minh họa)

```python
class N0SampleInput(BaseModel):
    text: str = ""
    tags: List[str] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

Sử dụng Pydantic V2 giúp xác thực kiểu dữ liệu nghiêm ngặt và xử lý tự động các giá trị mặc định thiếu.

### 5.2. Đầu ra (Envelope chuẩn)

```python
{
    "status": "success",
    "normalized": {
        "text": "normalized string",
        "tags": ["tag1", "tag2"],
        "metadata": {}
    },
    "metadata": {
        "module": "n0_sample",
        "latency_ms": 12,
        "tag_count": 2
    },
    "error": None
}
```

Mọi module (như N1, N2, N4, N6) đều tuân theo dạng thức có payload nghiệp vụ song song với object `metadata` dành cho việc benchmark và debug hệ thống.

---

## 6. Cách tái sử dụng trong thực tế

Khi cần khởi tạo một module mới (ví dụ `N18_New_Feature`), lập trình viên sẽ làm theo quy trình:

1. Sao chép thư mục `n0_sample` và đổi tên thành `n18_new_feature`
2. Cập nhật `__init__.py` để expose hàm mới (ví dụ `run_feature`)
3. Sửa lại contract Pydantic trong `backend/shared/contracts/n18_contracts.py`
4. Thay thế logic trong file Python bên trong bằng nghiệp vụ thực
5. Cập nhật README của module

Nhờ N0, module N18 sẽ tự động kế thừa bộ khung kiểm tra, bắt lỗi và phản hồi tương thích 100% với chuẩn của Orchestrator N8.

---

## 7. Kết luận

N0 tuy không chạy trên production, nhưng đóng vai trò như bản vẽ tiêu chuẩn kiến trúc cho mã nguồn. Nó là minh chứng cho một hệ thống được thiết kế hướng tới bảo trì dài hạn, nơi tính đồng nhất giữa các thành phần được coi trọng ngang với độ phức tạp của thuật toán bên trong.

---

## 8. Tài liệu tham khảo

| # | Chủ đề | Nguồn tham khảo |
|---|---|---|
| 1 | Pydantic V2 Documentation | [docs.pydantic.dev](https://docs.pydantic.dev/) |
| 2 | Python Project Structure | [realpython.com/python-application-layouts/](https://realpython.com/python-application-layouts/) |
