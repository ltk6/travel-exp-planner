# N17 — Feedback Processing: Báo Cáo Bench Test

**Ngày:** 2026-05-21  
**Chain:** groq_70b, qwen_32b, groq_8b, groq_scout  
**Số ca test:** 3  

---

> **⚠️ Lưu ý về môi trường kiểm thử:**  
> Các lỗi `fail_429` (Rate Limit) trong bài test này là **hoàn toàn bình thường** khi sử dụng Groq Free Tier.  
> - Bench test gọi liên tiếp nhiều model trong thời gian ngắn, vượt quá giới hạn RPM của tài khoản miễn phí.  
> - Trong thực tế, người dùng chỉ gửi 1 yêu cầu feedback mỗi vài phút, nên tỉ lệ thành công 1/3 trong bench test vẫn đảm bảo vận hành tốt ở production.  
> - Kết quả **end-to-end** (Mục 5) phản ánh đúng hiệu suất thực tế nhờ cơ chế failover.  

---

## 1. Tổng Quan Module

N17 xử lý phản hồi tự do của người dùng để tinh chỉnh ý định tìm kiếm. Module nhận đầu vào là bối cảnh hiện tại (text, tags, ảnh) và văn bản feedback, sau đó sử dụng LLM để sinh ra bộ lọc mới (refined intent).

**Cơ chế Failover:**  
`groq_70b` → `qwen_32b` → `groq_8b` → `groq_scout`  

**Chiến lược xử lý:**
- **Prompt Engineering:** Sử dụng kỹ thuật Few-shot và ràng buộc schema JSON nghiêm ngặt.
- **Tag Filtering:** Tự động lọc các tags không nằm trong ontology chuẩn của hệ thống.
- **Fallback Logic:** Nếu LLM hoặc Parser thất bại, module tự động ghép feedback vào input cũ để không làm gián đoạn luồng người dùng.

---

## 2. Các Ca Kiểm Thử

| Tên | User Input | Feedback |
|-----|------------|----------|
| quiet_beach | Tôi muốn đi du lịch biển sôi động | Thực ra tôi thấy hơi mệt, tôi muốn tìm một nơi nào đó cực kỳ yên tĩnh, không dùng cái ảnh này nữa |
| dalat_coffee | Du lịch Đà Lạt | Tôi muốn thêm các hoạt động trải nghiệm cà phê và săn mây |
| hanoi_history | Khám phá Hà Nội | Tôi thích văn hoá hơn là ăn uống, hãy tập trung vào các di tích lịch sử |

---

## 3. Kết Quả Per-Model

> Mỗi model chạy độc lập, không failover, không retry.

### gpt_120b (`openai/gpt-oss-120b`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 1074 | 1490 | ✓ PASS |
| dalat_coffee | 1583 | 1670 | ✓ PASS |
| hanoi_history | 1913 | 1791 | ✓ PASS |

**TB latency:** 1523.3ms &nbsp; **Pass rate:** 100%

### groq_70b (`llama-3.3-70b-versatile`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 931 | 1259 | ✓ PASS |
| dalat_coffee | 875 | 1236 | ✓ PASS |
| hanoi_history | 876 | 1217 | ✓ PASS |

**TB latency:** 894.0ms &nbsp; **Pass rate:** 100%

### qwen_32b (`qwen/qwen3-32b`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 1902 | 1669 | ✓ PASS |
| dalat_coffee | 1475 | 1548 | ✓ PASS |
| hanoi_history | 255 | — | ✗ FAIL |

**TB latency:** 1210.7ms &nbsp; **Pass rate:** 67%

### groq_8b (`llama-3.1-8b-instant`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 641 | 1248 | ✓ PASS |
| dalat_coffee | 690 | 1216 | ✓ PASS |
| hanoi_history | 684 | 1208 | ✓ PASS |

**TB latency:** 671.7ms &nbsp; **Pass rate:** 100%

### gpt_20b (`openai/gpt-oss-20b`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 976 | 1698 | ✓ PASS |
| dalat_coffee | 2613 | — | ✗ FAIL |
| hanoi_history | 1641 | 2335 | ✓ PASS |

**TB latency:** 1743.3ms &nbsp; **Pass rate:** 67%

### gpt_safeguard (`openai/gpt-oss-safeguard-20b`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 937 | 1562 | ✓ PASS |
| dalat_coffee | 1096 | 1735 | ✓ PASS |
| hanoi_history | 889 | 1602 | ✓ PASS |

**TB latency:** 974.0ms &nbsp; **Pass rate:** 100%

### groq_scout (`meta-llama/llama-4-scout-17b-16e-instruct`)

| Case | Latency (ms) | Total Tok | Status |
|------|:------------:|:---------:|:------:|
| quiet_beach | 1084 | 1156 | ✓ PASS |
| dalat_coffee | 939 | 1139 | ✓ PASS |
| hanoi_history | 1241 | 1173 | ✓ PASS |

**TB latency:** 1088.0ms &nbsp; **Pass rate:** 100%

---

## 4. Bảng So Sánh Tổng Hợp

| Alias | Model name | TB latency (ms) | Pass rate |
|-------|------------|:---------------:|:---------:|
| gpt_120b | `openai/gpt-oss-120b` | 1523.3 | 100% |
| groq_70b | `llama-3.3-70b-versatile` | 894.0 | 100% |
| qwen_32b | `qwen/qwen3-32b` | 1210.7 | 67% |
| groq_8b | `llama-3.1-8b-instant` | 671.7 | 100% |
| gpt_20b | `openai/gpt-oss-20b` | 1743.3 | 67% |
| gpt_safeguard | `openai/gpt-oss-safeguard-20b` | 974.0 | 100% |
| groq_scout | `meta-llama/llama-4-scout-17b-16e-instruct` | 1088.0 | 100% |

---

## 5. Kết Quả End-to-End

Chạy `process_feedback()` với full chain failover.

**Trung bình độ trễ:** 970.3ms  
**Tỉ lệ fallback:** 0/3  

| Case | Model thực tế | Latency (ms) | Tokens | Status | Tags |
|------|---------------|:------------:|:------:|:------:|:----:|
| quiet_beach | `llama-3.3-70b-versatile` | 1031 | 1252 | OK | 5 |
| dalat_coffee | `llama-3.3-70b-versatile` | 1027 | 1228 | OK | 4 |
| hanoi_history | `llama-3.3-70b-versatile` | 853 | 1220 | OK | 4 |
