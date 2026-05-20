# Module N3: Tầng Dữ liệu và Lưu trữ

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-15

---

## 1. Vai trò của Module N3

N3 là tầng persistence của hệ thống. Nếu N1 và N2 chịu trách nhiệm tạo ra biểu diễn ngữ nghĩa, thì N3 là nơi giữ cho toàn bộ các biểu diễn đó tồn tại bền vững và có thể truy xuất lại một cách nhất quán.

Trong dự án này, một bản ghi địa điểm không chỉ là một dòng text mô tả. Nó là một gói dữ liệu tổng hợp gồm:

- vector nhiều kênh
- metadata mô tả
- tọa độ hoặc thông tin địa lý
- ảnh nhị phân

Vì vậy, N3 không thể là một nơi chỉ “lưu vector”, mà phải là một lớp dữ liệu có khả năng mang đồng thời cả dữ liệu quan hệ, dữ liệu JSON và dữ liệu nhị phân.

---

## 2. Tư tưởng thiết kế: Unified Persistence

Một quyết định rất đáng chú ý của N3 là chọn **PostgreSQL + pgvector** thay vì tách dữ liệu thành nhiều hệ thống độc lập.

### 2.1. Vì sao không dùng một vector database riêng?

Về mặt lý thuyết, có thể tách:

- vector sang một vector DB
- metadata sang SQL
- ảnh sang file storage

Nhưng cách đó làm tăng mạnh chi phí đồng bộ và độ phức tạp hệ thống:

- nhiều nơi lưu trữ hơn
- nhiều điểm lỗi hơn
- khó đảm bảo tính nhất quán giữa vector, metadata và ảnh

Trong quy mô bài toán hiện tại, việc tập trung mọi thứ vào PostgreSQL đem lại lợi ích lớn hơn:

- dễ quản trị
- dễ reset
- dễ backup
- dễ đảm bảo một địa điểm luôn đi kèm đúng metadata và đúng ảnh của nó

### 2.2. Ý nghĩa của pgvector trong kiến trúc này

`pgvector` giúp N3 không chỉ lưu được vector mà còn giữ vector như một phần tự nhiên của dữ liệu địa điểm. Nhờ đó, một record có thể đồng thời mang:

- `text`
- `aug_text`
- `aug_tags`
- `img_desc`
- `metadata`
- `geo`
- `images`

Đây là một thiết kế “single source of truth” đúng nghĩa cho dữ liệu địa điểm.

---

## 3. Giao diện công khai

```python
init_db(drop_existing: bool = False) -> None
save_location(location_data: dict[str, Any]) -> dict[str, Any]
get_all_locations(include_images: bool = True) -> dict[str, Any]
get_db_fingerprint() -> str
attach_image_to_location(location_dict: dict[str, Any]) -> dict[str, Any]
```

Ý nghĩa từng hàm:

- `init_db(drop_existing: bool = False)`: khởi tạo lại hoặc tạo mới cấu trúc schema lưu trữ (chỉ xóa bảng cũ nếu `drop_existing=True`)
- `save_location()`: ghi hoặc cập nhật một địa điểm
- `get_all_locations()`: đọc toàn bộ dữ liệu theo cấu trúc API-ready
- `get_db_fingerprint()`: tạo dấu vân tay trạng thái dữ liệu
- `attach_image_to_location()`: helper tương thích cho payload địa điểm đã có ảnh

---

## 4. Cấu trúc lưu trữ

N3 tạo bảng `locations` với các cột chính:

- `location_id`
- `text`
- `aug_text`
- `aug_tags`
- `img_desc`
- `metadata`
- `geo`
- `images`
- `updated_at`

### 4.1. Ý nghĩa của thiết kế nhiều cột vector

Việc giữ riêng từng cột vector là một tiếp nối trực tiếp của tư tưởng multi-channel embedding ở N1. Điều này cho phép:

- truy xuất lại đúng kênh semantic đã được sinh
- giữ được khả năng giải thích nguồn tín hiệu
- hỗ trợ các bước xếp hạng dùng dynamic weighting

Nếu N3 chỉ lưu một vector hợp nhất duy nhất, rất nhiều lợi ích ở phía N1 sẽ bị mất.

### 4.2. Vì sao ảnh được lưu bằng `BYTEA[]`?

Quyết định này phản ánh một lựa chọn rất thực dụng:

- giữ ảnh đi cùng record dữ liệu
- giảm phụ thuộc vào file server ngoài
- giúp backup và reset dữ liệu dễ hơn

Tất nhiên, ở quy mô rất lớn, tách object storage có thể hợp lý hơn. Nhưng với hệ thống hiện tại, lưu trong DB giúp đơn giản hóa kiến trúc mà vẫn đủ mạnh.

---

## 5. Hợp đồng dữ liệu

### 5.1. Đầu vào của `save_location()`

```python
{
    "location_id": str,
    "vectors": {
        "text": list[float] | None,
        "aug_text": list[float] | None,
        "aug_tags": list[float] | None,
        "img_desc": list[float] | None,
    },
    "metadata": dict[str, Any],
    "geo": dict[str, Any],
    "images_binary": list[bytes],
}
```

### 5.2. Đầu ra của `save_location()`

```python
{
    "status": "success" | "error",
    "location_id": str,
    "message": str,
    "metadata": {
        "source": "postgresql",
        "latency_ms": int,
    },
}
```

### 5.3. Đầu ra của `get_all_locations()`

```python
{
    "status": "success" | "error",
    "total": int,
    "data": [
        {
            "location_id": str,
            "vectors": {
                "text": list[float] | None,
                "aug_text": list[float] | None,
                "aug_tags": list[float] | None,
                "img_desc": list[float] | None,
            },
            "metadata": dict[str, Any] | None,
            "geo": dict[str, Any] | None,
            "images": list[str],
        }
    ],
    "metadata": {
        "source": "postgresql",
        "latency_ms": int,
    },
}
```

Trong đó, `images` được trả về dưới dạng Base64 data URI. Đây là một quyết định chuyển đổi rất thực dụng: DB vẫn lưu nhị phân, nhưng API trả về định dạng dễ render ở UI.

---

## 6. Các quyết định hành vi quan trọng

### 6.1. `init_db(drop_existing: bool = False)` có chế độ bảo vệ dữ liệu

`init_db()` hiện tại an toàn và không phá hủy dữ liệu theo mặc định:

1. đảm bảo extension `vector` tồn tại
2. tạo bảng `locations` nếu chưa tồn tại
3. chỉ thực hiện xóa bảng `locations` và tạo lại từ đầu khi tham số `drop_existing=True` được truyền vào.

Điều này phù hợp với các giai đoạn:

- seed dữ liệu (cần truyền `drop_existing=True`)
- benchmark
- reset môi trường thí nghiệm
- Bảo vệ dữ liệu trong database khi vận hành thực tế.

### 6.2. Upsert thay vì insert cứng

`save_location()` dùng `ON CONFLICT` theo `location_id`. Quyết định này giúp:

- cập nhật dữ liệu địa điểm mà không cần xóa rồi chèn lại
- làm mới vector, metadata và geo an toàn
- giữ lại ảnh cũ nếu payload mới không cung cấp ảnh

Đây là một quyết định tốt vì ảnh thường là phần nặng nhất và không nhất thiết phải truyền lại mỗi lần update metadata.

### 6.3. Fingerprinting để hỗ trợ đồng bộ

`get_db_fingerprint()` hiện dựa trên:

- tổng số record
- `MAX(updated_at)`

Đây là một cơ chế fingerprint rẻ nhưng hiệu quả. Nó không cần hash toàn bộ dữ liệu, nhưng vẫn đủ mạnh để phát hiện:

- có thêm record mới
- có record vừa bị cập nhật

Về mặt kiến trúc, đây là một lựa chọn cân bằng rất tốt giữa chi phí và khả năng phát hiện thay đổi.

---

## 7. Cấu trúc Schema và Các Luồng truy xuất dữ liệu

### 7.1. Cấu trúc cơ sở dữ liệu phân rã an toàn (Decoupled Database Schemas)
Dưới đây là sơ đồ kiến trúc 3 tầng lưu trữ an toàn của N3, được cô lập hóa độc lập để đảm bảo an toàn dữ liệu người dùng và các thông tin hoạt động:

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false}}}%%
graph TD
    classDef layerLoc fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#000000;
    classDef layerUser fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#000000;
    classDef layerAct fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#000000;
    classDef initBtn fill:#f1f5f9,stroke:#475569,stroke-width:2px,stroke-dasharray:5 5,color:#000000;
    classDef initSafe fill:#d1fae5,stroke:#059669,stroke-width:2px,color:#000000;
    classDef initForce fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#000000;
    
    subgraph "1. Phân khu Địa điểm (Locations Layer)"
        LOC["locations table (location_id, vectors, metadata, geo, images BYTEA[])"]:::layerLoc
    end
    
    subgraph "2. Phân khu Người dùng & Auth (User Profile Layer)"
        USERS["users table (user_id, username, password_hash)"]:::layerUser
        HIST["rec_history table (history_id, user_id, input_data, output_data)"]:::layerUser
        USERS -->|1:N| HIST
    end
    
    subgraph "3. Phân khu Hoạt động (Activities Layer)"
        ACT["6x activities_provider tables (activity_id, location_id, vec_text, vec_tag, place, metadata)"]:::layerAct
        STATUS["activity_fetch_status table (location_id, provider, status, item_count)"]:::layerAct
    end
    
    DB_INIT["Khởi động Database (init_db / init_profile_db / init_activities_db)"]:::initBtn -->|drop_existing = False (Mặc định)| SAFE_INIT["CREATE TABLE IF NOT EXISTS (Bảo vệ dữ liệu, không phá hủy)"]:::initSafe
    DB_INIT -->|drop_existing = True (Chỉ định)| FORCE_INIT["DROP TABLE IF EXISTS & Khởi tạo lại (Reset / Reseed)"]:::initForce
```

---

### 7.2. Luồng truy xuất tối ưu: Hybrid Caching + Lazy Image Loading
Hệ thống loại bỏ hoàn toàn việc nạp ảnh nhị phân dung lượng lớn vào cache hoặc trong luồng trả dữ liệu chính. Thay vào đó, ảnh được tải động theo yêu cầu (Lazy Loading):

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false}}}%%
graph TD
    classDef client fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,color:#000000;
    classDef orchestrator fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#000000;
    classDef db fill:#f5f3ff,stroke:#818cf8,stroke-width:2.5px,color:#000000;
    classDef cache fill:#fffbeb,stroke:#f59e0b,stroke-width:2px,color:#000000;

    UI["Client UI (Giao diện)"]:::client

    %% Luồng Dữ liệu Slim
    UI -->|"1. Yêu cầu địa điểm"| N8_SLIM["N8 Orchestrator"]:::orchestrator
    N8_SLIM -->|"2. Lấy dữ liệu slim (không ảnh)"| N3_SLIM["N3 Database (PostgreSQL)"]:::db
    N3_SLIM -->|"3. Trả về metadata & vectors"| N8_SLIM
    N8_SLIM -.->|"4. Đọc/Ghi cache"| CACHE["RAM / Disk Cache"]:::cache
    N8_SLIM -->|"5. Trả JSON slim + lazy-url"| UI

    %% Luồng Lazy Load Ảnh
    UI -->|"6. Cuộn tới vùng hiển thị"| N8_IMG["N8: GET /api/images/:id_idx"]:::orchestrator
    N8_IMG -->|"7. Truy vấn BYTEA ảnh"| N3_IMG["N3 Database (PostgreSQL)"]:::db
    N3_IMG -->|"8. Trả nhị phân ảnh"| N8_IMG
    N8_IMG -->|"9. Giải mã & trả JPEG thô"| UI
```

---

### 7.3. Luồng lưu trữ địa điểm an toàn (Upsert Location Flow)
Hành vi lưu trữ sử dụng cơ chế PostgreSQL `ON CONFLICT` để upsert thông minh, không ghi đè mất ảnh cũ nếu payload mới chỉ cập nhật metadata hoặc vector:

```mermaid
%%{init: {'flowchart': {'useMaxWidth': false}}}%%
graph TD
    classDef db fill:#f5f3ff,stroke:#818cf8,stroke-width:3px,color:#000000;
    classDef flow fill:#f1f5f9,stroke:#475569,stroke-width:1px,color:#000000;
    classDef check fill:#fff1f2,stroke:#ef4444,stroke-width:2px,color:#000000;
    
    A["Yêu cầu lưu địa điểm"]:::flow --> B{"Đã tồn tại ID?"}:::check
    B -- "Chưa" --> C["Thêm bản ghi locations mới"]:::flow
    B -- "Rồi" --> D["Cập nhật bản ghi hiện có"]:::flow
    D --> E{"Có mảng ảnh mới?"}:::check
    E -- "Không" --> F["Giữ nguyên mảng ảnh cũ (Postgres Fallback)"]:::flow
    E -- "Có" --> G["Ghi đè mảng BYTEA[] mới"]:::flow
    
    C --> H[("PostgreSQL Database")]:::db
    F --> H
    G --> H

Luồng này cho thấy rõ vai trò “adapter” của N3:

- bên trong là dữ liệu DB-native
- bên ngoài là dữ liệu API-native

---

## 8. Ghi chú vận hành

- kết nối dùng `psycopg2` với `RealDictCursor`
- `register_vector()` được gọi trên từng kết nối mới
- vector được trả về dưới dạng list Python để thuận tiện cho các module phía trên
- logging và chuỗi kết nối lấy từ cấu hình dự án

---

## 9. Kết luận

N3 không chỉ là nơi lưu dữ liệu. Nó là tầng đảm bảo rằng mọi tài sản semantic của hệ thống:

- được lưu bền vững
- được truy xuất có cấu trúc
- và có thể đồng bộ hiệu quả với lớp điều phối

Giá trị lớn nhất của N3 nằm ở sự thống nhất: cùng một record địa điểm có thể chứa đầy đủ vector, metadata, geo và ảnh. Đây là một quyết định kiến trúc gọn, thực dụng và rất phù hợp với hệ thống recommendation quy mô học thuật nhưng đủ nghiêm túc để benchmark và demo end-to-end.

---

## 10. Tài liệu tham khảo

| # | Chủ đề | Nguồn tham khảo |
|---|---|---|
| 1 | pgvector GitHub | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| 2 | PostgreSQL Documentation | [www.postgresql.org/docs](https://www.postgresql.org/docs/) |
| 3 | Psycopg2 Documentation | [www.psycopg.org/docs/](https://www.psycopg.org/docs/) |
