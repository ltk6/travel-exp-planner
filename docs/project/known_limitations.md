# Hạn chế Đã biết (Known Limitations)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-15

---

## 1. Mục đích của phần này

Một báo cáo kỹ thuật tốt không chỉ trình bày điểm mạnh mà còn phải chỉ ra rõ:

- giới hạn hiện tại của hệ thống
- nguyên nhân gốc của các giới hạn đó
- mức độ ảnh hưởng thực tế

Phần này tổng hợp các hạn chế quan trọng nhất đang ảnh hưởng đến độ ổn định, hiệu năng hoặc khả năng mở rộng của hệ thống hiện tại.

---

## 2. Hạn chế từ hạ tầng LLM miễn phí

### 2.1. Vấn đề rate limit

Hạn chế lớn nhất hiện tại đến từ free-tier của hạ tầng LLM. Các model dùng trong generation và feedback đều có thể gặp:

- giới hạn RPM
- giới hạn TPM
- tải chia sẻ không ổn định

### 2.2. Ảnh hưởng đến hệ thống

Khi gặp rate limit:

- request generation có thể chậm hơn đáng kể
- chain model phải failover nhiều lần
- trải nghiệm feedback loop kém mượt
- benchmark không ổn định giữa các lần chạy

### 2.3. Giải pháp hiện tại và giới hạn của nó

Hệ thống đã có:

- multi-model failover chain
- retry theo exponential backoff

Tuy nhiên, đây chỉ là cơ chế giảm thiệt hại chứ không loại bỏ hoàn toàn nguyên nhân. Nếu toàn bộ chain cùng bị nghẽn, độ trễ vẫn tăng mạnh.

---

## 3. Hạn chế của generation theo LLM

### 3.1. Rủi ro output không ổn định

Dù đã dùng structured output, LLM vẫn có thể:

- trả JSON thiếu trường
- trả output bị truncate
- sinh tags không nằm trong vocabulary
- tạo mô tả nghe hợp lý nhưng không thật sự nhất quán

### 3.2. Hệ quả

Điều này ảnh hưởng trực tiếp tới:

- chất lượng activities ở N5
- độ ổn định của ranking ở N6
- độ tin cậy của feedback processing ở N17

### 3.3. Cơ chế giảm thiểu hiện tại

Hệ thống hiện dùng:

- structured output
- parser có khả năng repair một phần
- validation và filtering sau parse
- template fallback ở N5

Tuy nhiên, cần thừa nhận rằng bản chất của LLM generation vẫn là một nguồn biến thiên xác suất.

---

## 4. Độ trễ và khó khăn của nguồn dữ liệu hoạt động

### 4.1. Sự thiếu vắng API chuẩn từ các nguồn bản đồ
Dữ liệu hoạt động (N9-N14) thu thập từ 6 nguồn khác nhau (OSM, Goong, Foursquare...) tồn tại vấn đề phân mảnh mạnh về Schema. Rất nhiều nguồn thiếu thông tin rating, hình ảnh, hoặc giờ mở cửa, dẫn đến việc xếp hạng bị nhiễu do khuyết tín hiệu (missing signals).

### 4.2. Độ trễ do Fallback LLM (N5)
Dù đã chuyển sang Database-first, đối với các điểm đến chưa được seed dữ liệu bản đồ, hệ thống sẽ gọi dự phòng LLM (N5) để sinh hoạt động theo thời gian thực (real-time). Khi đó, hệ thống phải:
1. sinh text hoạt động qua API
2. gọi model nhúng cục bộ (N1)
3. xếp hạng

Quá trình fallback này tốn khoảng 3-5 giây, tạo sự đứt gãy về trải nghiệm so với < 0.5s khi đọc dữ liệu có sẵn từ N9-N14 DB.

### 4.3. Giải pháp hiện tại
- Khuyến khích cào (seed) trước offline càng rộng càng tốt để giảm tỉ lệ chạy fallback.
- Dùng `embed_batch()` để giảm overhead cục bộ.
- Dùng Waterfall sequential loading ở N16 UI để che giấu độ trễ.

---

## 5. Hạn chế của semantic retrieval đa kênh

### 5.1. Sự phụ thuộc vào chất lượng tagging và augmentation

Hệ thống semantic hiện tại phụ thuộc nhiều vào:

- chất lượng tags
- độ đúng của ontology
- chất lượng augmentation ở N1

Nếu các tầng này kém:

- dynamic weighting sẽ bị điều khiển sai
- retrieval sẽ ít sắc nét hơn
- ranking explanations sẽ kém thuyết phục hơn

### 5.2. Ý nghĩa của giới hạn này

Đây không phải lỗi code, mà là giới hạn tự nhiên của mọi hệ thống semantic dựa trên biểu diễn trung gian. Chất lượng cuối cùng phụ thuộc rất mạnh vào chất lượng semantic preprocessing.

---

## 6. Hạn chế của frontend hiện tại (N16 Next.js Web App)

Dù việc nâng cấp sang Next.js 15 (N16) đã khắc phục triệt để các hạn chế về đơ giao diện của Streamlit, N16 vẫn có một số giới hạn thực tiễn cần lưu ý:

- **Áp lực lên PostgreSQL Connection Pool khi lazy-load ảnh:** Vì hình ảnh nhị phân được tải bất đồng bộ trực tiếp từ cột BYTEA trong DB qua endpoint `/api/images/{location_id}_{idx}.jpg`, khi người dùng cuộn xem hàng loạt địa điểm cùng lúc sẽ kích hoạt hàng chục request song song, gây áp lực tức thì lên kết nối cơ sở dữ liệu.
- **Trạng thái Zustand Store bị xóa khi hard-refresh:** Do lưu trữ trạng thái Questionnaire Wizard và kết quả gợi ý trong RAM (Zustand Store), nếu người dùng vô tình bấm F5 (refresh trình duyệt), toàn bộ trạng thái phiên hiện tại sẽ bị mất trừ khi tích hợp thêm Middleware lưu trữ vào LocalStorage.
- **Độ phức tạp khi deploy:** Đòi hỏi chạy một máy chủ NodeJS NodeJS-run độc lập ở frontend thay vì chỉ chạy script Python đơn giản như prototype trước đây.

---

## 7. Hạn chế của lớp orchestration hiện tại

N8 hiện vận hành tốt ở quy mô đồ án và demo, nhưng vẫn có một số giới hạn kiến trúc:

- orchestration phần lớn theo hướng synchronous
- cache hiện tối ưu tốt cho dữ liệu địa điểm, nhưng chưa phải distributed cache thực thụ
- chưa có hàng đợi tác vụ tách biệt cho generation nặng

Điều này có nghĩa là hệ thống hiện phù hợp cho:

- đồ án
- demo
- nhóm người dùng vừa phải

nhưng chưa phải kiến trúc tối ưu cho tải production lớn.

---

## 8. Kết luận

Các hạn chế hiện tại của hệ thống tập trung ở ba vùng chính:

1. **hạ tầng AI bên ngoài**: rate limit, variability của LLM
2. **chi phí semantic runtime**: đặc biệt ở nhánh activity embedding
3. **giới hạn kiến trúc mở rộng**: tải kết nối song song khi lazy loading ảnh ở N16 và orchestration đồng bộ ở N8

Điểm tích cực là phần lớn các giới hạn này đã được:

- nhận diện rõ
- cô lập được nguyên nhân
- có cơ chế giảm thiểu bước đầu

Điều này cho thấy hệ thống không chỉ được xây để “chạy được”, mà còn được quan sát và đánh giá một cách có phương pháp.
