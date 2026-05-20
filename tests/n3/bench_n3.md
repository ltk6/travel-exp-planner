# N3 — Module Database Layer: Báo Cáo Bench Test

**Ngày:** 2026-05-19 17:20:44
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
| Light Load  | `get_all(images=False)`        |  7526 ms    |       |

---

## 3. Kiểm Tra Kết Nối & Write
- **Kết nối:** PASS (1454 ms)

| Địa điểm              | Location ID       | Độ trễ (ms) | Kết quả |
|-----------------------|-------------------|-------------|---------|
| Bãi Sao Phú Quốc      | `bench_loc_001` |  1302 ms    | PASS |

---

## 4. Nhận Xét Hệ Thống
1. **Atomic Persistence:** Đã chuyển hoàn toàn sang lưu trữ nhị phân trong DB.
2. **Sync Intelligence:** Fingerprint giúp giảm đáng kể traffic binary.
3. **Cloud Ready:** Dễ dàng deploy lên Hugging Face Spaces hoặc các nền tảng cloud.