# N2 — Module Image Understanding: Báo Cáo Bench Test

**Ngày:** 2026-05-15  
**Model:** `meta-llama/llama-4-scout-17b-16e-instruct`  
**Số ảnh test:** 3  
**Ngưỡng PASS:** 20–60 từ, ≥ 2 keyword hits (tối đa 50 từ yêu cầu trong prompt)  

---

## 1. Tổng Quan Module

N2 là module Vision Layer của pipeline. Nhận ảnh thô (bytes), gọi Groq Vision API (Llama 4 Scout Multimodal), và trả về một đoạn mô tả văn học giàu tính gợi hình bằng Tiếng Việt. Kết quả được sử dụng để tạo embedding ngữ nghĩa (N1) và làm phong phú thêm metadata địa điểm.

**Luồng xử lý:**
1. Nhận `image_bytes` → Chuyển sang JPEG/base64 (chuẩn hóa định dạng)
2. Gọi Groq Vision API với prompt Travel Blogger (3 trụ cột: Loại hình, Kiến trúc, Cảm xúc)
3. Trả về `{"img_desc": str}` — đoạn văn thuần túy, không markdown, không nhiễu

**Giới hạn kỹ thuật:**
- `max_tokens`: 150 (mục tiêu ≤ 50 từ, chất lượng cao, tiết kiệm token)
- Timeout: 60 giây
- Không retry tại tầng N2 — retry được xử lý ở tầng gọi cao hơn (API route)

---

## 2. Các Ca Kiểm Thử

| Tên | Loại cảnh | File size | Keyword kỳ vọng |
|-----|-----------|-----------|-----------------|
| Bãi Biển Nhiệt Đới | coastal / nature | ~1332 KB | biển, cát, sóng, cây cọ, nhiệt đới |
| Thành Phố Đô Thị | urban / architecture | ~1169 KB | tòa nhà, đường phố, đô thị, ánh sáng, hiện đại |
| Hồ Núi Thiên Nhiên | mountain / lake | ~2411 KB | hồ, núi, rừng, thiên nhiên, yên bình |

---

## 3. Kết Quả Per-Ảnh

### Bãi Biển Nhiệt Đới (`beach.png`)

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 1943 ms |
| Prompt tokens | 2055 |
| Completion tokens | 63 |
| Total tokens | 2118 |
| Số từ | 51 |
| Số đoạn văn | 1 |
| Keyword hits | 2/5 |
| Đánh giá | ✓ **PASS** |

**Preview (300 ký tự đầu):**
> Bãi biển tuyệt đẹp với những cây dừa xanh tươi nghiêng mình bên bờ cát trắng mịn, nước biển trong xanh dưới bầu trời rạng rỡ. Không khí trong lành, yên bình tạo nên một bức tranh thiên nhiên hoàn hảo, khiến lòng ai cũng cảm thấy thư thái, dễ chịu....

### Thành Phố Đô Thị (`city.png`)

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 1288 ms |
| Prompt tokens | 2055 |
| Completion tokens | 69 |
| Total tokens | 2124 |
| Số từ | 51 |
| Số đoạn văn | 1 |
| Keyword hits | 2/5 |
| Đánh giá | ✓ **PASS** |

**Preview (300 ký tự đầu):**
> Cảm giác sảng khoái của hoàng hôn buổi chiều đông, thành phố nhộn nhịp bừng sáng. Những tòa nhà chọc trời sừng sững giữa khung cảnh đường xá rộng lớn, sặc sỡ ánh đèn nền hòa quyện tạo nên bức tranh thành thị lung linh, hiện đại và đầy sức sống....

### Hồ Núi Thiên Nhiên (`lake.png`)

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 1850 ms |
| Prompt tokens | 2490 |
| Completion tokens | 66 |
| Total tokens | 2556 |
| Số từ | 50 |
| Số đoạn văn | 1 |
| Keyword hits | 4/5 |
| Đánh giá | ✓ **PASS** |

**Preview (300 ký tự đầu):**
> Hồ núi cao giữa khung cảnh thiên nhiên hùng vĩ, nước trong vắt, xanh ngắt. Những dãy núi nhấp nhô, phủ đầy cây xanh và một ít tuyết trắng xen kẽ tạo nên bức tranh tuyệt mỹ. Không khí trong lành, yên bình, khiến du khách không thể rời mắt....

---

## 4. Bảng So Sánh Tổng Hợp

| Ảnh | Độ trễ (ms) | Prompt tok | Completion tok | Total tok | Số từ | KW hits | Đánh giá |
|-----|:-----------:|:----------:|:--------------:|:---------:|:-----:|:-------:|:---------:|
| Bãi Biển Nhiệt Đới | 1943 | 2055 | 63 | 2118 | 51 | 2/5 | ✓ PASS |
| Thành Phố Đô Thị | 1288 | 2055 | 69 | 2124 | 51 | 2/5 | ✓ PASS |
| Hồ Núi Thiên Nhiên | 1850 | 2490 | 66 | 2556 | 50 | 4/5 | ✓ PASS |

**TB latency:** 1693.7ms &nbsp;**TB total tokens:** 2266 &nbsp;**TB word count:** 51 từ &nbsp;**Pass:** 3/3

---

## 5. Nhận Xét Chính

1. **Model:** `meta-llama/llama-4-scout-17b-16e-instruct` — Llama 4 Scout Multimodal được sử dụng. Đây là model vision duy nhất trong pipeline, có TPM quota 30K/phút trên Groq Free Tier.
2. **Chất lượng mô tả:** Output đạt chuẩn Travel Blogger — văn phong giàu tính gợi hình, tuân thủ 3 trụ cột (Loại hình, Kiến trúc, Cảm xúc). Không có lời dẫn 'Trong ảnh có...' hay 'Tôi thấy...'.
3. **Độ dài hợp lý:** Trung bình ~200 từ/ảnh phù hợp với `max_tokens=1000`. Không bị truncate trong điều kiện bình thường.
4. **Keyword recall:** Model nhận diện đúng loại cảnh (biển, đô thị, núi/hồ) và sử dụng từ vựng ngữ nghĩa phù hợp để downstream N1 embedding hoạt động chính xác.
5. **Rate limit:** N2 không có retry riêng. Nếu bị 429, tầng gọi (N8 API) cần xử lý retry. Khuyến nghị thêm exponential backoff ở tầng API nếu số lượng ảnh xử lý tăng cao.