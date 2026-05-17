# Module N0: Mẫu khởi tạo Module

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-15

---

## 1. Vai trò của Module N0

N0 không phải module nghiệp vụ thật, mà là một module mẫu dùng để chuẩn hóa cách bắt đầu một module mới trong hệ thống. Giá trị của N0 không nằm ở logic tính toán, mà ở việc nó đóng vai trò như một “khung tham chiếu” cho:

- cấu trúc package
- cách export API
- cách validate input
- cách trả response envelope
- cách viết tài liệu module

Trong bối cảnh một dự án nhiều module đánh số, N0 giúp tránh việc mỗi người tạo module theo một phong cách khác nhau.

---

## 2. Tư tưởng thiết kế

Một hệ thống nhiều module dễ bị phân mảnh nếu không có một convention đủ rõ. N0 được tạo ra để giải quyết đúng vấn đề đó.

### 2.1. N0 minh họa điều gì?

N0 minh họa một pattern cơ bản nhưng hữu ích:

1. nhận payload đầu vào dạng `dict`
2. chuẩn hóa dữ liệu về shape an toàn
3. validate các trường tối thiểu
4. trả response có cấu trúc ổn định

### 2.2. Vì sao cần một module mẫu thay vì chỉ viết guideline?

Vì guideline bằng chữ thường khó buộc mọi người làm giống nhau. Một module mẫu có lợi thế:

- copy được ngay
- nhìn thấy cấu trúc thật
- dễ dùng cho onboarding
- giảm chi phí suy nghĩ khi bootstrap module mới

---

## 3. Giao diện công khai

```python
run_sample(data: dict[str, Any]) -> dict[str, Any]
```

### 3.1. Cấu trúc đầu vào

```python
{
    "text": str,
    "tags": list[str],
    "metadata": dict[str, Any],
}
```

### 3.2. Cấu trúc đầu ra

```python
{
    "status": "success" | "error",
    "normalized": {
        "text": str,
        "tags": list[str],
        "metadata": dict[str, Any],
    },
    "metadata": {
        "module": "n0_sample",
        "tag_count": int,
        "has_text": bool,
    },
    "error": str,
}
```

---

## 4. Ý nghĩa của logic mẫu

Mặc dù đơn giản, logic của `run_sample()` thể hiện một số nguyên tắc tốt:

- không tin tuyệt đối vào input
- luôn normalize trước khi xử lý tiếp
- tách phần dữ liệu nghiệp vụ khỏi phần metadata chẩn đoán
- dùng response envelope ổn định cho cả success và error

Đây là các nguyên tắc rất nên được giữ lại khi phát triển các module thật trong dự án.

---

## 5. Cách sử dụng trong thực tế

Khi cần khởi tạo module mới, có thể dùng N0 theo quy trình:

1. copy thư mục mẫu
2. đổi tên module
3. đổi tên hàm public
4. thay logic `run_sample()` bằng nghiệp vụ thật
5. cập nhật README và docs tương ứng

Nhờ đó, các module mới sẽ có:

- cấu trúc quen thuộc
- API surface rõ ràng
- tài liệu dễ đồng bộ

---

## 6. Kết luận

N0 là một module nhỏ nhưng có giá trị tổ chức lớn. Nó giúp biến việc phát triển thêm module mới từ một công việc “tự do tùy ý” thành một công việc có khuôn mẫu, giảm sai khác giữa các phần của codebase và làm cho tài liệu toàn hệ thống đồng đều hơn.
