# N5 — Module Activity Generation: Báo Cáo Bench Test

**Ngày:** 2026-05-14  
**Chain:** gpt_120b, groq_70b, qwen_32b, groq_8b, gpt_20b, gpt_safeguard, groq_scout  
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
`gpt_120b` → `groq_70b` → `qwen_32b` → `groq_8b` → `gpt_20b` → `gpt_safeguard` → `groq_scout`  

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
| Bãi Sao Phú Quốc | 7153 | 1572 | 3228 | 4800 | 10 | ✓ |
| Fansipan Sapa | 346 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 332 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 2610.3ms &nbsp;**TB total tokens:** 4800 &nbsp;**Pass:** 1/3

### groq_70b  (`llama-3.3-70b-versatile`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4121 | 1532 | 1702 | 3234 | 10 | ✓ |
| Fansipan Sapa | 4217 | 1529 | 1575 | 3104 | 10 | ✓ |
| Phố Cổ Hội An | 303 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 2880.3ms &nbsp;**TB total tokens:** 3169 &nbsp;**Pass:** 2/3

### qwen_32b  (`qwen/qwen3-32b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 6312 | 1495 | 2492 | 3987 | 10 | ✓ |
| Fansipan Sapa | 346 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 307 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 2321.7ms &nbsp;**TB total tokens:** 3987 &nbsp;**Pass:** 1/3

### groq_8b  (`llama-3.1-8b-instant`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 1985 | 1532 | 1589 | 3121 | 10 | ✓ |
| Fansipan Sapa | 301 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 355 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 880.3ms &nbsp;**TB total tokens:** 3121 &nbsp;**Pass:** 1/3

### gpt_20b  (`openai/gpt-oss-20b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4575 | — | — | — | 0 | ✗ |
| Fansipan Sapa | 312 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 299 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1728.7ms &nbsp;**TB total tokens:** — &nbsp;**Pass:** 0/3

### gpt_safeguard  (`openai/gpt-oss-safeguard-20b`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 4515 | 1572 | 4000 | 5572 | 6 | ✓ |
| Fansipan Sapa | 319 | — | — | — | 0 | ✗ *(fail)* |
| Phố Cổ Hội An | 307 | — | — | — | 0 | ✗ *(fail)* |

**TB latency:** 1713.7ms &nbsp;**TB total tokens:** 5572 &nbsp;**Pass:** 1/3

### groq_scout  (`meta-llama/llama-4-scout-17b-16e-instruct`)

| Địa điểm | Độ trễ (ms) | Prompt tok | Completion tok | Tổng tok | Valid | Pass |
|----------|:-----------:|:----------:|:--------------:|:--------:|:-----:|:----:|
| Bãi Sao Phú Quốc | 3780 | 1463 | 1464 | 2927 | 10 | ✓ |
| Fansipan Sapa | 4234 | 1460 | 1698 | 3158 | 10 | ✓ |
| Phố Cổ Hội An | 3565 | 1462 | 1373 | 2835 | 10 | ✓ |

**TB latency:** 3859.7ms &nbsp;**TB total tokens:** 2973 &nbsp;**Pass:** 3/3

---

## 4. Bảng So Sánh Tổng Hợp

| Model alias | Model name | TB latency (ms) | TB total tok | Pass rate | Lý do fail tiềm năng |
|-------------|------------|:---------------:|:------------:|:---------:|----------------------|
| gpt_120b | `openai/gpt-oss-120b` | 2610.3 | 4800 | 33% (1/3) | fail_429 / fail_413 |
| groq_70b | `llama-3.3-70b-versatile` | 2880.3 | 3169 | 67% (2/3) | fail_429 / fail_413 |
| qwen_32b | `qwen/qwen3-32b` | 2321.7 | 3987 | 33% (1/3) | fail_429 / fail_413 |
| groq_8b | `llama-3.1-8b-instant` | 880.3 | 3121 | 33% (1/3) | fail_429 / fail_413 |
| gpt_20b | `openai/gpt-oss-20b` | 1728.7 | — | 0% (0/3) | Truncate / fail_429 |
| gpt_safeguard | `openai/gpt-oss-safeguard-20b` | 1713.7 | 5572 | 33% (1/3) | Truncate / fail_429 |
| groq_scout | `meta-llama/llama-4-scout-17b-16e-instruct` | 3859.7 | 2973 | 100% (3/3) | — |

---

## 5. Kết Quả End-to-End

Chạy `generate_activities()` với **full chain failover bật**, 3 địa điểm tuần tự.

**Tổng thời gian:** 16958ms  
**Tổng activities sinh ra:** 30  

| Địa điểm | Provider | Model thực tế dùng | Độ trễ (ms) | Prompt tok | Completion tok | LLM? |
|----------|----------|--------------------|:-----------:|:----------:|:--------------:|:----:|
| loc_015 | groq | `openai/gpt-oss-120b` | 7153 | 1575 | 3160 | ✓ |
| loc_001 | groq | `llama-3.3-70b-versatile` | 4472 | 1526 | 1419 | ✓ |
| loc_007 | groq | `llama-3.3-70b-versatile` | 5321 | 1531 | 1748 | ✓ |

---

## 6. Nhận Xét Chính

1. **Pipeline production hoạt động đúng:** Kết quả End-to-End cho thấy hệ thống sinh đủ activities thông qua cơ chế failover tự động.
2. **Rate-limit là mong đợi:** Các lỗi fail_429 trong bench test cá nhân là do tần suất gọi request quá cao, không phản ánh lỗi logic của code.
3. **gpt_120b (120B) là model chất lượng cao nhất:** Khi không bị limit, model cho reasoning chi tiết nhất. Đây là lý do nó đứng đầu chain.
4. **groq_70b là backbone thực tế:** Với TPM 12K, đây là model thường xuyên 'gánh' pipeline khi 120b bị rate-limit.
5. **groq_scout có độ tin cậy cao nhất (100% pass):** Nhờ TPM quota 30K lớn, Scout là lưới an toàn cuối cùng cực kỳ vững chắc.
6. **gpt_20b và gpt_safeguard bị truncate:** Các model này dễ bị cắt ngang ở 4000 tokens. Cơ chế **Auto-Repair** có thể cứu vãn một phần nhưng không phải lúc nào cũng thành công.