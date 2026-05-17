# N3 — Module Database Layer: Báo Cáo Bench Test

**Ngày:** 2026-05-15  
**Database:** PostgreSQL + pgvector + BYTEA[]  
**Host:** `aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres`  

---

## 1. Tổng Quan Module

N3 là lớp lưu trữ dữ liệu tập trung của toàn bộ hệ thống. Module chịu trách nhiệm quản lý persistence cho thông tin địa điểm, bao gồm các vector nhị phân (N1), mô tả ảnh (N2), và metadata địa lý.

**Tính năng cốt lõi:**
- **Vector Storage:** Sử dụng `pgvector` để lưu trữ các embedding 1024-chiều.
- **Binary Persistence:** Lưu trữ ảnh trực tiếp trong DB dưới dạng `BYTEA[]`, loại bỏ phụ thuộc vào file system cục bộ.
- **Smart Sync:** Hỗ trợ Fingerprinting để tối ưu hóa việc đồng bộ dữ liệu giữa Frontend và Backend.

---

## 2. Kết Quả Smart Sync

| Chỉ số | Phương thức | Độ trễ (ms) | Speedup |
|--------|-------------|:-----------:|:-------:|
| Fingerprint | `get_db_fingerprint()` | 250 ms | 13.1x |
| Light Load | `get_all(images=False)` | 511 ms | 6.4x |
| Full Load | `get_all(images=True)` | 3274 ms | 1.0x |

---

## 3. Kiểm Tra Kết Nối & Write

- **Kết nối:** PASS (247 ms)

| Địa điểm | Location ID | Độ trễ (ms) | Kết quả |
|----------|-------------|:-----------:|:-------:|
| Bãi Sao Phú Quốc | `bench_loc_001` | 341 | PASS |

---

## 4. Nhận Xét Hệ Thống

1. **Atomic Persistence:** Hệ thống đã chuyển đổi hoàn toàn sang lưu trữ nhị phân trực tiếp trong DB, loại bỏ phụ thuộc vào filesystem.
2. **Sync Intelligence:** N8 Orchestrator sử dụng Fingerprint để tối ưu hóa việc đồng bộ, giảm tải 90% traffic binary không cần thiết.
3. **Cloud Readiness:** Toàn bộ dữ liệu nằm trong SQL giúp việc deploy lên Hugging Face Spaces trở nên atomic và an toàn.