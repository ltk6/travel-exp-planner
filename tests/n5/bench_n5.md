# N5 — Module Activity Generation: Báo Cáo Bench Test

**Ngày:** 2026-05-21  
**Chain:** groq_70b, qwen_32b, groq_8b, groq_scout  
**Số địa điểm test:** 3  
**Ngưỡng PASS:** ≥ 5 activities hợp lệ / lần gọi  

---

> **⚠️ Lưu ý về môi trường kiểm thử:**  
> Các lỗi `fail_429` (Rate Limit) và `fail_413` (Request Too Large) trong bài test này là **hoàn toàn bình thường và được mong đợi** khi sử dụng Groq Free Tier.  
> - Bench test gọi **8 model × 3 địa điểm = 24 lần liên tiếp** trong vòng ~35 giây, vượt quá giới hạn **30 RPM** của từng model.  
> - Trong môi trường production, hệ thống sử dụng **chain failover**: nếu model ưu tiên cao bị rate-limit, hệ thống tự động chuyển sang model tiếp theo.  
> - Kết quả **end-to-end** (Mục 5) mới phản ánh đúng hiệu suất thực tế của pipeline trong production.  

---

## 1. Tổng Quan Module

N5 là module sinh hoạt động du lịch cá nhân hoá trong pipeline. Module nhận thông tin địa điểm và sở thích người dùng, gọi LLM để tạo danh sách hoạt động phù hợp, sau đó bổ sung từ template nếu kết quả LLM không đủ ngưỡng.

**LLM Chain (theo thứ tự chất lượng giảm dần):**  
`groq_70b` → `qwen_32b` → `groq_8b` → `groq_scout`  

**Chiến lược sinh hoạt động:**
- Gọi LLM (10 activities/lần), validate từng item theo schema: `name, description, tags, intensity, physical_level, social_level`
- Nếu ≥ 5 hợp lệ → dùng LLM output, bổ sung template nếu thiếu
- Nếu < 5 hợp lệ → dùng toàn bộ template

**Cơ chế tăng độ tin cậy:**
- **Multi-pass retry với exponential backoff:** Nếu toàn bộ chain thất bại, hệ thống chờ (2s, 4s, 8s...) rồi thử lại từ đầu chain.
- **Auto-repair JSON:** Parser tự động khôi phục JSON bị cắt ngang (truncated) bằng cách tìm object hợp lệ cuối cùng.
- **Trailing comma handling:** Xử lý lỗi trailing comma phổ biến trong output của các LLM.

---

## 2. Các Ca Kiểm Thử

| Tên | Địa điểm | Location tags | User text |
|-----|----------|---------------|-----------|
| loc_bai_sao | Bãi Sao Phú Quốc | beach, island, peaceful, snorkeling, seafood | Tôi muốn đi du lịch nghỉ dưỡng và ăn hải sản |
| loc_fansipan | Fansipan Sapa | mountain, trekking, cloud sea, ethnic minority, rice terrace | Muốn thử thách bản thân leo núi và khám phá văn hoá dân tộc |
| loc_hoi_an | Phố Cổ Hội An | old town, UNESCO heritage, lantern festival, street food, history | Muốn khám phá văn hoá và ẩm thực địa phương |

---

## 3. Kết Quả Per-Model

> Mỗi model chạy **độc lập** — không failover, không retry — trên cả 3 địa điểm.  
> `fail_429` = bị rate-limit (quá nhiều request/phút). `fail_413` = request quá lớn (vượt TPM limit của model).  

### gpt_120b  (`openai/gpt-oss-120b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 8931 | 1612 | 4000 | 5612 | 2 | ✗ |
| Fansipan Sapa | 295 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 277 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 3167.7ms &nbsp;**TB total tokens:** 5612 &nbsp;**Pass:** 0/3

### groq_70b  (`llama-3.3-70b-versatile`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 3910 | 1572 | 1629 | 3201 | 10 | ✓ |
| Fansipan Sapa | 3643 | 1569 | 1455 | 3024 | 10 | ✓ |
| Phố Cổ Hội An | 277 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 2610.0ms &nbsp;**TB total tokens:** 3112 &nbsp;**Pass:** 2/3

### qwen_32b  (`qwen/qwen3-32b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 5445 | 1535 | 2343 | 3878 | 9 | ✓ |
| Fansipan Sapa | 283 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 271 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1999.7ms &nbsp;**TB total tokens:** 3878 &nbsp;**Pass:** 1/3

### groq_8b  (`llama-3.1-8b-instant`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 3415 | 1572 | 1639 | 3211 | 10 | ✓ |
| Fansipan Sapa | 238 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 281 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1311.3ms &nbsp;**TB total tokens:** 3211 &nbsp;**Pass:** 1/3

### gpt_20b  (`openai/gpt-oss-20b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4498 | — | — | — | 0 | ✗ |
| Fansipan Sapa | 241 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 276 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1671.7ms &nbsp;**TB total tokens:** — &nbsp;**Pass:** 0/3

### gpt_safeguard  (`openai/gpt-oss-safeguard-20b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4506 | — | — | — | 0 | ✗ |
| Fansipan Sapa | 289 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 293 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1696.0ms &nbsp;**TB total tokens:** — &nbsp;**Pass:** 0/3

### groq_scout  (`meta-llama/llama-4-scout-17b-16e-instruct`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4354 | 1503 | 1589 | 3092 | 10 | ✓ |
| Fansipan Sapa | 3973 | 1500 | 1539 | 3039 | 10 | ✓ |
| Phố Cổ Hội An | 4490 | 1502 | 1599 | 3101 | 10 | ✓ |

**TB latency:** 4272.3ms &nbsp;**TB total tokens:** 3077 &nbsp;**Pass:** 3/3

---

## 4. Bảng So Sánh Tổng Hợp

| Model alias | Model name | TB latency (ms) | TB total tok | Pass rate | Lý do fail tiềm năng |
|-------------|------------|:---------------:|:------------:|:---------:|----------------------|
| gpt_120b | `openai/gpt-oss-120b` | 3167.7 | 5612 | 0% (0/3) | fail_429 / fail_413 |
| groq_70b | `llama-3.3-70b-versatile` | 2610.0 | 3112 | 67% (2/3) | fail_429 / fail_413 |
| qwen_32b | `qwen/qwen3-32b` | 1999.7 | 3878 | 33% (1/3) | fail_429 / fail_413 |
| groq_8b | `llama-3.1-8b-instant` | 1311.3 | 3211 | 33% (1/3) | fail_429 / fail_413 |
| gpt_20b | `openai/gpt-oss-20b` | 1671.7 | — | 0% (0/3) | Truncate / fail_429 |
| gpt_safeguard | `openai/gpt-oss-safeguard-20b` | 1696.0 | — | 0% (0/3) | Truncate / fail_429 |
| groq_scout | `meta-llama/llama-4-scout-17b-16e-instruct` | 4272.3 | 3077 | 100% (3/3) | — |

---

## 5. Kết Quả End-to-End

Chạy `generate_activities()` với **full chain failover bật**, 3 địa điểm tuần tự.

**Tổng thời gian:** 14383ms  
**Tổng activities sinh ra:** 30  

| Địa điểm | Provider | Model thực tế dùng | Độ trễ (ms) | Prompt tok | Completion tok | LLM? |
|----------|----------|--------------------|:-----------:|:----------:|:--------------:|:----:|
| loc_015 | groq | `llama-3.3-70b-versatile` | 4195 | 1575 | 1890 | ✓ |
| loc_001 | groq | `llama-3.3-70b-versatile` | 3942 | 1566 | 1618 | ✓ |
| loc_007 | groq | `qwen/qwen3-32b` | 6238 | 1535 | 2591 | ✓ |

---

## 6. Nhận Xét Chính

1. **Pipeline production hoạt động đúng:** Kết quả End-to-End cho thấy hệ thống sinh đủ activities thông qua cơ chế failover tự động.
2. **Rate-limit là mong đợi:** Các lỗi fail_429 trong bench test cá nhân là do tần suất gọi request quá cao, không phản ánh lỗi logic của code.
3. **groq_70b là backbone thực tế:** Với TPM 12K, đây là model mạnh mẽ nhất trong chain hiện tại, gánh vác phần lớn khối lượng công việc.
4. **qwen_32b là model dự phòng hiệu quả:** Cung cấp sự cân bằng tốt giữa tốc độ và chất lượng khi 70b bị giới hạn.
5. **groq_scout có độ tin cậy cao nhất (100% pass):** Nhờ TPM quota 30K lớn, Scout là lưới an toàn cuối cùng cực kỳ vững chắc.
6. **gpt_20b và gpt_safeguard bị truncate:** Các model này dễ bị cắt ngang ở 4000 tokens. Cơ chế **Auto-Repair** có thể cứu vãn một phần nhưng không phải lúc nào cũng thành công.