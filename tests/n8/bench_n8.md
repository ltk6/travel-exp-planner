# N8 - Module Orchestrator: Báo Cáo Bench Test

**Ngày:** 2026-05-21  
**Chế độ bench:** Mocked downstream modules (N1, N2, N3, N4, N5, N6, N17) để đo dung lượng overhead của N8  
**Mục tiêu:** Cache behavior, service orchestration, endpoint routing, feedback loop  

---

## 1. Tổng Quan Module

N8 là lớp điều phối trung tâm của hệ thống. Giá trị cần bench ở đây không nằm ở chất lượng model mà nằm ở việc:
- Gọi đúng module theo thứ tự pipeline
- Giảm latency bằng hybrid cache
- Duy trì contract JSON ổn định cho frontend
- Hỗ trợ feedback loop mà không bắt frontend tự xử lý logic refine

Bài bench này mock toàn bộ module bên dưới để loại bỏ noise từ embedding, database thật, và LLM API.

---

## 2. Cache Benchmark

| Giai đoạn | Latency (ms) | DB fetch trước | DB fetch sau | Bản ghi | Trạng thái |
|-----------|:------------:|:--------------:|:------------:|:-------:|:---------:|
| cold_fetch | 0 | 0 | 1 | 3 | PASS |
| warm_ram | 0 | 1 | 1 | 3 | PASS |
| warm_disk | 1 | 1 | 1 | 3 | PASS |
| force_refresh | 1 | 1 | 2 | 3 | PASS |

- Cache file tạo thành công: **True**
- Số file ảnh cache tạo được: **0**
- Kết quả tổng: **PASS**

---

## 3. Endpoint Benchmark

| Test | Route | Code | Latency (ms) | Status | Module deltas |
|------|-------|:----:|:------------:|:------:|---------------|
| health | `GET /health` | 200 | 2 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 0, 'embed_calls': 0, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 0, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 0}` |
| fingerprint | `GET /cache/fingerprint` | 200 | 0 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 1, 'embed_calls': 0, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 0, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 0}` |
| recommend_cold | `POST /recommend` | 200 | 1 | PASS | `{'db_fetches': 1, 'fingerprint_calls': 0, 'embed_calls': 1, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 1, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 0}` |
| recommend_warm | `POST /recommend` | 200 | 0 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 0, 'embed_calls': 1, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 1, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 0}` |
| activities | `POST /activities` | 200 | 0 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 0, 'embed_calls': 1, 'embed_batch_calls': 1, 'n2_calls': 0, 'rank_location_calls': 0, 'n5_calls': 1, 'rank_activity_calls': 1, 'feedback_calls': 0}` |
| feedback_recommend | `POST /feedback/recommend` | 200 | 0 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 0, 'embed_calls': 1, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 1, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 1}` |
| feedback_activities | `POST /feedback/activities` | 200 | 0 | PASS | `{'db_fetches': 0, 'fingerprint_calls': 0, 'embed_calls': 1, 'embed_batch_calls': 1, 'n2_calls': 0, 'rank_location_calls': 0, 'n5_calls': 1, 'rank_activity_calls': 1, 'feedback_calls': 1}` |
| cache_reset | `POST /cache/reset` | 200 | 1 | PASS | `{'db_fetches': 1, 'fingerprint_calls': 0, 'embed_calls': 0, 'embed_batch_calls': 0, 'n2_calls': 0, 'rank_location_calls': 0, 'n5_calls': 0, 'rank_activity_calls': 0, 'feedback_calls': 0}` |

**Pass endpoint tests:** 8/8

---

## 4. Nhận Xét Chính

1. **Hybrid cache hoạt động đúng đường đi:** Lần đầu gọi N3, lần sau hit RAM, xóa RAM thì hit Disk, force refresh mới gọi lại N3.
2. **Recommend pipeline của N8 gọn và đúng hợp đồng:** 1 lần embed + 1 lần rank_locations, trong khi warm cache không phát sinh thêm DB fetch.
3. **Activities pipeline hợp lý cho presentation:** N8 thực sự là cầu nối N5 -> N1 batch -> N6, thay vì chỉ là một route wrapper mỏng.
4. **Feedback loop có giá trị kiến trúc rõ ràng:** Feedback routes kích hoạt N17 rồi chạy lại workflow chính, giữ response shape ổn định cho UI.
5. **Bench này đo đúng N8:** Vì downstream đã được mock, các con số latency ở đây phản ánh orchestration overhead và cache behavior thay vì model latency.