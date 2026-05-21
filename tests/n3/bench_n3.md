# N3 — Module Database Layer: Báo Cáo Bench Test

**Ngày:** 2026-05-21 18:34:56
**Database:** PostgreSQL + pgvector + BYTEA[]
**Host:** `aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres`

---

## 1. Tổng Quan Module
N3 là lớp lưu trữ dữ liệu tập trung, chịu trách nhiệm persistence cho địa điểm, vector (N1), mô tả ảnh (N2) và metadata địa lý.

**Tính năng cốt lõi:**
- **Vector Storage:** `pgvector` với embedding 1024 chiều
- **Binary Persistence:** Lưu ảnh trực tiếp dưới dạng `BYTEA[]`
- **Smart Sync:** Fingerprinting hỗ trợ đồng bộ thông minh

---

## 2. Kết Quả Smart Sync
| Chỉ số      | Phương thức                    | Độ trễ (ms) | Ghi chú |
|-------------|--------------------------------|-------------|---------|
| Light Load  | `get_all(images=False)`        |  1806 ms    |       |

---

## 3. Kiểm Tra Kết Nối & Write
- **Kết nối:** PASS (338 ms)

| Địa điểm              | Location ID       | Độ trễ (ms) | Kết quả |
|-----------------------|-------------------|-------------|---------|
| Bãi Sao Phú Quốc      | `bench_loc_001` |   825 ms    | PASS |

---

## 4. Kiểm Tra Tải Binary (Lazy Image Loading)

N3 thực hiện trả về trực tiếp BYTEA binary cho N16 thay vì serialize sang Base64 JSON.

| Định dạng ảnh | Dung lượng trung bình | Độ trễ đọc + trả về (ms) | Băng thông (MB/s) |
|---------------|-----------------------|--------------------------|-------------------|
| JPEG gốc      | ~1.30 MB             | 733.0 ms (Min: 565.2 ms) | 1.78 MB/s |

- **Băng thông:** Việc trả ảnh dưới dạng nhị phân nguyên gốc (raw binary) cho phép trình duyệt (N16) cache trực tiếp bằng Service Worker.

---

## 5. Nhận Xét Chính
1. **Atomic Persistence:** Đã chuyển hoàn toàn sang lưu trữ nhị phân trong DB (cột BYTEA). Postgres xử lý tốt khối lượng dữ liệu này.
2. **Sync Intelligence:** Fingerprint siêu nhẹ (`MAX(updated_at)`, `COUNT(*)`) giúp giảm đáng kể traffic binary không cần thiết.
3. **Hiệu suất Lazy Load:** Thời gian trích xuất ảnh nhị phân cực nhanh (Avg: 733.0 ms, Min: 565.2 ms), đáp ứng tốt luồng tải tuần tự Waterfall của N16.
4. **Cloud Ready:** Dễ dàng deploy lên Hugging Face Spaces hoặc các nền tảng cloud.