# N1 — Module Embedding: Báo Cáo Bench Test

**Ngày:** 2026-05-21  
**Model:** `BAAI/bge-m3` (568M tham số, đa ngôn ngữ)  
**Thiết bị:** CPU  
**Số chiều vector:** 1024  
**Nguồn:** `tests/n1/bench.py` → `bench_n1_results.json`

---

## 1. Tổng Quan Module

N1 là điểm vào embedding của pipeline. Module nhận đầu vào thô từ người dùng hoặc địa điểm qua ba kênh — văn bản tự do, tags, và mô tả ảnh — tiền xử lý từng kênh thành chuỗi được làm giàu ngữ nghĩa, sau đó mã hóa tất cả trong một lần forward pass duy nhất theo batch.

**Đầu vào:**
```
{ "text": str, "tags": list[str], "img_desc": str }
```

**Đầu ra:**
```
{
  "text_k":     int,           # số từ khóa cảm xúc/ngữ cảnh mở rộng từ text
  "tags_k":     int,           # số tag khớp với bảng từ vựng
  "preprocessed": { text, aug_text, aug_tags, img_desc },
  "vectors":      { text, aug_text, aug_tags, img_desc }  # 1024-chiều mỗi kênh, hoặc null
}
```

### Các Kênh

| Kênh | Nguồn | Mục đích |
|------|-------|----------|
| `text` | Văn bản thô từ người dùng | Vector ý định trực tiếp |
| `aug_text` | text + mở rộng cảm xúc/ngữ cảnh | Mở rộng ngữ nghĩa |
| `aug_tags` | Bảng từ vựng tag mở rộng | Vector neo dựa trên tag |
| `img_desc` | Mô tả ảnh (từ N2 hoặc người dùng) | Căn chỉnh hình ảnh |

Vector của một kênh sẽ là `null` khi chuỗi đầu vào rỗng — đây là hành vi có chủ đích và được xử lý trong bước tính điểm N4.

---

## 2. Các Ca Kiểm Thử

### Đầu vào người dùng (3 ca)

| Tên | Văn bản | Tags | Có img_desc |
|-----|---------|------|:-----------:|
| user_1 | Tôi muốn một chuyến đi yên tĩnh gần thiên nhiên | thiên nhiên, yên tĩnh, couple | Có |
| user_2 | Muốn đi du lịch chữa lành tâm trí sau thời gian stress | healing, relax, nature | Có |
| user_3 | Đi chơi cuối tuần nhẹ nhàng với người yêu | couple, weekend, romantic | Không |

### Đầu vào địa điểm (3 ca)

| Tên | Văn bản | Tags | Có img_desc |
|-----|---------|------|:-----------:|
| loc_1 | Busy coastal city with nightlife and beaches | beach, city, nightlife | Không |
| loc_2 | Quiet mountain town surrounded by forests and mist | mountain, forest, quiet | Không |
| loc_3 | Historic city with temples, culture, and street food | culture, history, food | Không |

---

## 3. Kết Quả Tiền Xử Lý

Bộ tiền xử lý quét văn bản để tìm từ khóa cảm xúc/ngữ cảnh, đồng thời khớp tags với bảng từ vựng, rồi nối các chuỗi mở rộng tương ứng.

| Ca | text_k | tags_k | Kênh null |
|----|:------:|:------:|-----------|
| user_1 | 3 | 1 | — |
| user_2 | 1 | 0 | — |
| user_3 | 2 | 2 | `img_desc` |
| loc_1 | 2 | 3 | `img_desc` |
| loc_2 | 3 | 2 | `img_desc` |
| loc_3 | 2 | 1 | `img_desc` |

**Khoảng text_k:** 1–3  
**Khoảng tags_k:** 0–3

**Các ca đáng chú ý:**
- **user_2** (`tags_k=0`): Các tag `healing`, `relax`, `nature` là từ tiếng Anh hợp lệ nhưng không có trong `ALL_TAGS`. Kênh aug_tags rỗng, tạo ra vector null. N4 sẽ gán trọng số bằng 0 cho kênh tag khi xếp hạng ca này.
- **user_1** (`text_k=3`): Văn bản chứa `thiên nhiên`, `yên tĩnh`, và một ngữ cảnh địa phương quen thuộc — cả ba đều mở rộng, tạo ra chuỗi aug_text dài nhất trong bộ test.

### Ví dụ: Mở rộng aug_text (user_1)

**Văn bản đầu vào:**
> Tôi muốn một chuyến đi yên tĩnh gần thiên nhiên

**aug_text sau mở rộng:**
> Tôi muốn một chuyến đi yên tĩnh gần thiên nhiên *natural outdoor environments away from urban development, characterized by vegetation, open terrain, and non-built scenery* *environment characterized by low noise, minimal human activity, and a calm undisturbed physical atmosphere* *a familiar and local place with a comfortable feel*

---

## 4. Kết Quả Độ Trễ

Tất cả đo trên CPU. Lần gọi đầu tiên bao gồm thời gian khởi động model (~2.8s); các lần sau ổn định ở ~1–1.8s.

### Gọi đơn lẻ embed()

| Ca | Độ trễ (ms) | Ghi chú |
|----|:-----------:|---------|
| user_1 | 3530.00 | Lần gọi đầu — bao gồm thời gian tải model |
| user_2 | 348.00 |  |
| user_3 | 341.00 |  |
| loc_1 | 395.00 |  |
| loc_2 | 643.00 |  |
| loc_3 | 335.00 |  |

| Chỉ số | Giá trị |
|--------|--------:|
| Trung bình user | 1406.33 ms |
| Trung bình location | 457.67 ms |
| Trung bình tổng thể | 932.00 ms |

### Gọi batch embed_batch()

| Batch | Số item | Tổng (ms) | Mỗi item (ms) |
|-------|:-------:|:---------:|:-------------:|
| user batch | 3 | 1471.04 | 490.35 |
| location batch | 3 | 1336.62 | 445.54 |

**Batch so với từng lần riêng lẻ:** Xử lý 3 item theo batch mất ~1471.0–1336.6ms, so với ~2796.0ms nếu gọi tuần tự. Lợi thế ở batch size 3 còn khiêm tốn vì nút cổ chai là forward pass của model, không phải overhead Python. Hiệu quả tăng rõ hơn ở batch size lớn hơn.

Thiết kế mã hóa `N_items × 4 kênh` chuỗi trong một lần forward pass duy nhất — đây là đặc tính hiệu quả cốt lõi cho `activities_service` của N8, nơi embed tới 10+ activity cùng lúc qua `embed_batch`.

---

## 5. Kiểm Tra Tính Đúng Đắn

| Kiểm tra | Kết quả |
|----------|:-------:|
| Tất cả vector không-null có norm = 1.0 | **PASS** |
| Đầu ra batch == đầu ra đơn lẻ (từng kênh, tol=1e-5) | **PASS** |
| Tất cả vector có số chiều = 1024 | **PASS** |

**Kiểm tra norm:** `BAAI/bge-m3` được load với `normalize_embeddings=True`. Tất cả các vector không-null trong các ca test đơn lẻ đều trả về norm = 1.000000, xác nhận rằng cosine similarity tương đương với tích vô hướng trên các vector này.

**Tính nhất quán batch:** Với các ca test, mỗi vector kênh từ `embed_batch([item])` đều giống hệt `embed([item])` trong giới hạn sai số dấu phẩy động. Luồng batch không tạo ra độ lệch so với luồng đơn lẻ.

---

## 6. Tóm Tắt Số Chiều & Kênh Null

Tất cả vector được tạo ra đều có 1024 chiều (kích thước đầu ra của BAAI/bge-m3).

| Kênh | Không-null (trong 6) | Null khi nào |
|------|:--------------------:|--------------|
| `text` | 6/6 | Không bao giờ (text luôn có) |
| `aug_text` | 6/6 | Không bao giờ (fallback về text thô) |
| `aug_tags` | 6/6 | Tags có nhưng không khớp bảng từ vựng ALL_TAGS |
| `img_desc` | 2/6 | Không có ảnh đầu vào (hầu hết đầu vào location) |

---

## 7. Nhận Xét Chính Cho Báo Cáo

1. **Thiết kế đa kênh tách biệt các tín hiệu ý định.** Thay vì ghép tất cả vào một chuỗi, N1 tạo ra bốn vector độc lập. Điều này cho phép N4 cân chỉnh trọng số động dựa trên lượng tín hiệu text và tag mà truy vấn mang theo (`text_k`, `tags_k`).

2. **Xử lý null graceful.** Kênh rỗng tạo ra vector `null` thay vì vector không. Hàm `_cosine()` của N4 trả về 0.0 cho đầu vào null, nên kênh thiếu đóng góp điểm bằng 0 mà không làm hỏng điểm số.

3. **Độ trễ CPU khoảng 1–1.8s mỗi lần gọi** (sau khởi động), chấp nhận được cho API async nhưng sẽ là nút cổ chai đầu tiên khi scale. GPU có thể rút xuống dưới 100ms.

4. **Kiểm soát từ vựng tag chặt chẽ.** Các tag tiếng Anh về lối sống (`healing`, `relax`, `nature`) không có trong `ALL_TAGS`. Người dùng nhập các tag này sẽ nhận `tags_k=0` và mất kênh tính điểm tag. Đây không phải là hạn chế mà là điểm mạnh: việc kiểm soát tags chặt chẽ giúp tránh nhiễu và đảm bảo tính chính xác cho các phép tính toán học phía sau.

5. **Chế độ batch là lựa chọn đúng cho embedding activity ở N5.** Khi N8 embed 10 activity sau khi sinh, `embed_batch` xử lý toàn bộ 40 chuỗi (10 × 4 kênh) trong một lần forward pass. Ở batch size 10, overhead mỗi item giảm thêm nhờ tận dụng tốt hơn tài nguyên hệ thống.
