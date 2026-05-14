# Hệ Thống Gắn Thẻ (Tagging System) và Quy Tắc Kiểm Soát

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-14  

---

## 1. Triết lý "Single-Vector Tagging"

Trong hệ thống của chúng ta, toàn bộ danh sách tags của một địa điểm (hoặc người dùng) không được xử lý riêng rẽ mà được nối lại thành một chuỗi văn bản mở rộng (expanded string) và chuyển thành **một vector duy nhất** thông qua model BGE-M3.

**Hệ quả cực kỳ quan trọng:** Mọi tag trong chuỗi đều "cạnh tranh" để giành lấy tầm ảnh hưởng trong vector cuối cùng. Nếu kiểm soát tags lỏng lẻo, chất lượng xếp hạng (ranking) sẽ sụt giảm nghiêm trọng.

---

## 2. Các Quy Luật Cốt Lõi

### Quy luật 1: Sự pha loãng (Dilution is real)
Càng nhiều tags, vector càng bị kéo về phía trung bình của không gian nhúng (embedding space). 
- Một địa điểm gắn 25 tags sẽ có vector nằm ở "giữa", dẫn đến kết quả: khớp "tạm ổn" với mọi thứ nhưng không khớp "xuất sắc" với bất kỳ yêu cầu cụ thể nào.
- **Giải pháp:** Chỉ gắn tags cho những đặc trưng thực sự nổi bật.

### Quy luật 2: Cân bằng danh mục (Category Balance)
Nếu bạn gắn 8 tags về hoạt động nhưng chỉ 1 tag về cảm xúc (vibe), vector sẽ bị thiên kiến nặng nề về phía hoạt động.
- **Giải pháp:** Phân bổ tags đều qua các nhóm: Địa hình, Hoạt động, Cảm xúc, Văn hóa.

### Quy luật 3: Bài kiểm tra "Lý do duy nhất"
Trước khi thêm bất kỳ tag nào, hãy tự hỏi: *"Liệu một du khách có chọn địa điểm này CHỈ VÌ đặc điểm này không?"*
- **Có:** Gắn thẻ.
- **Cũng có thể, nhưng không phải chính:** Bỏ qua.

---

## 3. Chuyển đổi từ "Khớp Thẻ" sang "Ngữ Nghĩa" (Semantic Innovation)

Thay vì đi theo hướng tiếp cận truyền thống là **Tag Matching** (khớp chính xác tên thẻ) và vật lộn với việc quản lý danh sách thẻ ngày càng phình to (tag sprawl), hệ thống của chúng ta sử dụng một chiến lược hiện đại hơn:

### Hệ thống Ontology kiểm soát chặt chẽ
Chúng ta không cho phép gắn thẻ tùy tiện. Mọi thẻ phải nằm trong một **Ontology** (bộ từ vựng) được định nghĩa sẵn. Điều này đảm bảo tính nhất quán giữa input của người dùng và dữ liệu của địa điểm.

### Cơ chế Mở rộng Thẻ (Tag Expansion)
Đây là điểm mấu chốt để tận dụng sức mạnh của **BGE-M3**:
- Mỗi từ khóa đơn giản như `trekking` không đứng một mình.
- Hệ thống sẽ tự động "giải nén" nó thành một chuỗi mô tả giàu ngữ nghĩa: *"multi-day trekking mountain trail jungle endurance rewarding"*.
- **Mục tiêu:** Cung cấp cho model nhúng (embedding model) nhiều ngữ cảnh hơn để nó có thể tính toán toán học sự tương đồng một cách chính xác nhất.

**Lợi ích:** Hệ thống có thể hiểu được rằng một người thích `trekking` cũng sẽ có sự tương đồng nhất định với địa điểm gắn thẻ `hiking` hoặc `nature`, ngay cả khi các từ khóa này không khớp nhau hoàn toàn về mặt ký tự.

---

## 4. Ngân Sách Tags (Tag Budget)

Để đảm bảo độ nhạy của hệ thống, chúng ta áp dụng định mức nghiêm ngặt:

### Đối với Địa điểm (Locations)
| Loại địa điểm | Số lượng Tags | Ghi chú |
|---------------|---------------|---------|
| **Focused** | **8–12** | Đặc trưng rõ ràng (ví dụ: Bãi Sao, Đỉnh Fansipan) |
| **Standard** | **13–18** | Đa trải nghiệm (ví dụ: Hội An, Nha Trang) |
| **Complex** | **19–24** | Trung tâm lớn (ví dụ: Đà Nẵng, Phú Quốc) |
| **Giới hạn cứng** | **25** | **Tuyệt đối không vượt quá.** |

### Đối với Người dùng (User Profile)
Dựa trên bảng câu hỏi (Questionnaire):
- **Câu hỏi ngắn (3–5 câu):** 4–8 tags.
- **Tiêu chuẩn (6–10 câu):** 8–14 tags.
- **Tối đa:** 20 tags.

---

## 4. Kiểm Soát Chặt Chẽ và Tránh Trùng Lặp

Hệ thống yêu cầu tags phải được kiểm soát chặt chẽ để tránh "nhiễu" semantic:

### Tránh trùng lặp ngữ nghĩa
Một số cặp tags có không gian vector gần như trùng nhau. Gắn cả hai chỉ làm lãng phí ngân sách tags và gây thiên kiến ảo.
- **KHÔNG dùng:** `peaceful` + `slow travel` (chọn 1).
- **KHÔNG dùng:** `luxury` + `resort` + `boutique` (chọn 1 đặc trưng nhất).
- **KHÔNG dùng:** `trekking` + `hiking` (chọn theo độ khó).

### Phân bổ theo danh mục (Per-location)
- **Địa hình / Hệ sinh thái:** Tối đa 4 tags.
- **Hoạt động (Quan trọng nhất):** Tối đa 6 tags.
- **Cảm xúc / Vibe (Yếu tố quyết định):** 1–3 tags.
- **Ẩm thực:** Tối đa 3 tags.

---

## 5. Tại sao cần kiểm soát "Tightly Controlled"?

1. **Độ chính xác của Cosine Similarity:** Khi vector của User và Location đều "sắc nét" (sparse and focused), góc giữa chúng sẽ phản ánh đúng ý định. Nếu cả hai đều "tù" (do quá nhiều tags), điểm số sẽ bị cụm lại ở vùng 0.8-0.9, khiến việc phân loại trở nên bất khả thi.
2. **Hiệu ứng "Dead-zone":** Việc kiểm soát tags giúp đẩy các địa điểm không phù hợp ra xa, tạo ra khoảng cách điểm số rõ rệt (spread) để UI có thể hiển thị kết quả thuyết phục.
3. **Logic Fallback (N6):** Trong ranking hoạt động, tags được dùng để suy luận sở thích (preferences). Nếu input tags quá hỗn loạn, hệ thống sẽ suy luận sai về cường độ vận động (physical) hoặc tính xã hội (social) của người dùng.

---

## Tổng Kết Hướng Dẫn

- **Ít hơn là tốt hơn:** Ưu tiên sự chính xác hơn là sự đầy đủ.
- **Ngôn ngữ chung:** User và Location phải dùng chung bộ từ vựng trong `ALL_TAGS`.
- **Vibe là chìa khóa:** Hoạt động trả lời câu hỏi "Làm gì?", Vibe trả lời câu hỏi "Tại sao chọn chỗ này thay vì chỗ kia?". Hãy luôn có ít nhất 1-2 vibe tags.
