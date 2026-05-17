# Hệ thống Gắn thẻ (Tagging System) và Quy tắc Kiểm soát

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-15

---

## 1. Vai trò của hệ thống tags trong toàn bộ pipeline

Trong hệ thống này, tags không chỉ là nhãn hiển thị hay bộ lọc phụ. Chúng là một trong những nguồn semantic quan trọng nhất, đặc biệt khi:

- người dùng viết truy vấn ngắn
- mô tả địa điểm chưa đủ rõ bằng text
- cần ổn định hóa ý nghĩa ở cấp khái niệm

Nói cách khác, tags là lớp “ngữ nghĩa có cấu trúc” của hệ thống. Nếu text đại diện cho diễn đạt tự nhiên, thì tags đại diện cho vocabulary đã được kiểm soát.

---

## 2. Triết lý thiết kế: Từ tag matching sang semantic tagging

Nhiều hệ thống truyền thống dùng tags theo kiểu:

- user có tag nào
- location có tag nào
- đếm số tag trùng nhau

Hệ thống hiện tại không đi theo hướng đó. Thay vào đó, tags được dùng như đầu vào cho semantic embedding, nghĩa là:

- tags không được so khớp bằng ký tự đơn thuần
- tags được mở rộng ngữ nghĩa
- toàn bộ tập tags góp phần tạo nên một vector semantic

Đây là một khác biệt rất quan trọng.

### 2.1. Hệ quả của cách tiếp cận này

Khi tags được nối thành chuỗi mở rộng rồi nhúng thành vector, từng tag không còn là thực thể độc lập tuyệt đối. Chúng bắt đầu “cạnh tranh” ảnh hưởng lên cùng một biểu diễn vector.

Điều này dẫn đến một kết luận thiết kế quan trọng:

> Tagging trong hệ thống semantic không thể làm lỏng tay.  
> Nếu gắn tag bừa bãi, vector sẽ bị pha loãng.

---

## 3. Ontology kiểm soát chặt chẽ

Hệ thống chỉ cho phép dùng tags nằm trong một vocabulary chuẩn đã được định nghĩa trước.

### 3.1. Vì sao phải kiểm soát chặt?

Nếu cho phép tags tự do:

- người dùng và dữ liệu địa điểm sẽ dùng từ vựng khác nhau
- số lượng synonym bùng nổ
- hệ thống khó giữ được ngữ nghĩa ổn định

Ví dụ:

- `quiet`
- `peaceful`
- `relaxing`
- `calm`

có thể gần nhau nhưng không hoàn toàn đồng nghĩa trong mọi ngữ cảnh. Nếu không kiểm soát vocabulary, việc mapping semantic sẽ trở nên nhiễu hơn rất nhiều.

### 3.2. Vai trò của ontology trong quality control

Ontology giúp:

- ép user và location dùng chung một ngôn ngữ semantic
- giảm tag sprawl
- tạo nền cho tag expansion ở N1 và các bước suy luận ở N6

Đây là lý do tags của hệ thống không được xem như “metadata phụ”, mà là một thành phần hạ tầng ngữ nghĩa.

---

## 4. Tag Expansion và ý nghĩa của nó

Một tag ngắn như `trekking` hay `peaceful` khi đứng một mình thường quá ngắn để tận dụng hết sức mạnh của embedding model. Do đó, hệ thống dùng cơ chế **tag expansion**:

- mỗi tag được ánh xạ sang một cụm mô tả giàu ngữ nghĩa hơn
- cụm này mới là thứ được đưa vào embedding

Ví dụ về mặt ý tưởng:

- `trekking` không chỉ là một từ
- nó có thể đại diện cho đường núi, sức bền, thiên nhiên, khám phá, hành trình dài

### 4.1. Lợi ích của tag expansion

Tag expansion giúp:

- tăng semantic density của tín hiệu tag
- làm cho khoảng cách giữa các tag gần nghĩa trở nên liên thông hơn
- giúp retrieval bớt phụ thuộc vào exact wording

Đây chính là bước biến tag từ một “nhãn rời rạc” thành một “neo ngữ nghĩa”.

---

## 5. Hiệu ứng pha loãng (Dilution)

Một trong những rủi ro lớn nhất của tagging trong không gian embedding là **dilution**.

### 5.1. Dilution là gì?

Khi gắn quá nhiều tags vào cùng một đối tượng:

- vector tổng hợp có xu hướng tiến về vùng trung bình
- tính đặc trưng của đối tượng bị mờ đi
- nhiều nơi bắt đầu “hơi giống nhau một chút” thay vì “rất đúng chỗ này”

Trong bài toán recommendation, đây là điều cực kỳ nguy hiểm vì nó làm:

- score clustering mạnh
- top results khó phân biệt
- UI nhìn kém thuyết phục hơn

### 5.2. Ý nghĩa thực tế

Một địa điểm có 25 tags bao trùm quá nhiều khía cạnh có thể:

- khớp tạm ổn với nhiều truy vấn
- nhưng hiếm khi thật sự xuất sắc với một truy vấn cụ thể

Do đó, nguyên tắc quan trọng là:

> Ít hơn nhưng đúng hơn thường tốt hơn nhiều so với đầy đủ nhưng nhiễu.

---

## 6. Ngân sách tags (Tag Budget)

Để tránh dilution, hệ thống áp dụng tư duy **tag budget**.

### 6.1. Với địa điểm

| Loại địa điểm | Số lượng tags khuyến nghị | Ý nghĩa |
|---|---|---|
| Focused | 8–12 | địa điểm có bản sắc rõ |
| Standard | 13–18 | địa điểm đa trải nghiệm vừa phải |
| Complex | 19–24 | điểm đến lớn, nhiều mặt |
| Giới hạn cứng | 25 | tuyệt đối không nên vượt |

### 6.2. Với hồ sơ người dùng

| Kiểu input | Tags khuyến nghị |
|---|---|
| Truy vấn ngắn / ít câu hỏi | 4–8 |
| Bộ câu hỏi tiêu chuẩn | 8–14 |
| Tối đa | khoảng 20 |

### 6.3. Vì sao cần budget?

Tag budget là một cơ chế kiểm soát chất lượng rất thực dụng:

- tránh việc “tham thông tin”
- giữ vector tập trung
- làm cho từng tag có trọng lượng semantic thật sự

Đây là một nguyên tắc hay cho báo cáo vì nó cho thấy hệ thống không chỉ quan tâm đến “có bao nhiêu dữ liệu”, mà còn quan tâm đến “mỗi tín hiệu có sắc nét hay không”.

---

## 7. Cân bằng theo nhóm ngữ nghĩa

Không chỉ số lượng tags quan trọng, mà cách phân phối tags giữa các nhóm cũng quan trọng.

Các nhóm chính thường gồm:

- địa hình / hệ sinh thái
- hoạt động
- cảm xúc / vibe
- văn hóa
- ẩm thực

### 7.1. Vì sao phải cân bằng?

Nếu một địa điểm có:

- 8 tags hoạt động
- nhưng chỉ 1 tag cảm xúc

thì vector sẽ bị kéo mạnh về khía cạnh “làm gì” mà thiếu khía cạnh “không khí ra sao”. Trong du lịch, đây là một mất mát lớn vì vibe thường là yếu tố quyết định lựa chọn.

Do đó, hệ thống nên phân bổ tag có chủ đích thay vì nhồi tất cả vào nhóm dễ nghĩ ra nhất.

---

## 8. Quy tắc “Lý do duy nhất”

Một kiểm tra rất thực tế được đề xuất là:

> “Liệu người dùng có thể chọn địa điểm này chỉ vì đặc điểm này không?”

Nếu câu trả lời là “có”, tag đó đáng để giữ.  
Nếu chỉ là một thuộc tính phụ, ít quyết định, thì tag đó có thể nên bỏ.

### 8.1. Vì sao quy tắc này hiệu quả?

Vì nó ép người gắn tag phải nghĩ theo góc nhìn recommendation, không phải chỉ theo kiểu mô tả toàn diện.

Tagging trong retrieval không nhằm “ghi hết những gì có”, mà nhằm giữ lại **những gì có sức quyết định đối với sự phù hợp**.

---

## 9. Kết nối với Dynamic Weighting và Ranking

Tags không chỉ hữu ích ở một chỗ duy nhất. Chúng tham gia nhiều tầng:

- ở N1: tạo `aug_tags`
- ở dynamic weighting: tác động qua `tags_k`
- ở N4: làm semantic anchor cho location ranking
- ở N6: góp phần suy luận user preferences

Điều này khiến chất lượng tagging ảnh hưởng lan tỏa đến nhiều module. Một bộ tags tốt sẽ:

- tăng khả năng retrieval
- làm score ổn định hơn
- giúp giải thích kết quả thuyết phục hơn

Ngược lại, một bộ tags kém chất lượng có thể làm sai lệch cả ranking lẫn inference.

---

## 10. Kết luận

Hệ thống tagging trong dự án này không phải lớp nhãn trang trí, mà là một tầng ngữ nghĩa có kiểm soát chặt. Giá trị lớn nhất của nó nằm ở ba điểm:

1. chuẩn hóa vocabulary
2. mở rộng ngữ nghĩa qua tag expansion
3. kiểm soát dilution bằng tag budget và quy tắc gắn thẻ

Đây là nền tảng quan trọng để semantic retrieval của toàn bộ hệ thống hoạt động ổn định và có khả năng giải thích tốt.
