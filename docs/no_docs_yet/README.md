# TÀI LIỆU CẬP NHẬT KIẾN TRÚC & ĐIỂM MỚI CỦA HỆ THỐNG
*(Dành cho việc cập nhật Báo cáo đồ án / Tài liệu kỹ thuật)*

Tài liệu này hệ thống hóa toàn bộ các cải tiến kỹ thuật, tính năng mới và các bản sửa lỗi (bug fixes) của dự án **Travel Experience Planner** so với phiên bản ban đầu. Tài liệu được biên soạn rõ ràng, trực quan để người viết báo cáo có thể dễ dàng sao chép thông tin hoặc tích hợp vào báo cáo chính thức.

---

## 📌 PHẦN 1: CÁC CẢI TIẾN & BUG FIXES THUẬT TOÁN CỐT LÕI (N4 & N6)

### 1. Tính toán Trọng số động theo Kênh Existing & Missing — `fix(n4, n6)`
* **Vấn đề trước đây**: Khi người dùng cung cấp thiếu thông tin đầu vào (ví dụ: chỉ nhập mô tả Text mà không chọn nhãn Tags lọc, hoặc ngược lại), thuật toán tính điểm tương đồng cũ bị chia đều hoặc giữ nguyên trọng số thô, dẫn đến điểm số bị lệch và làm giảm độ chính xác của gợi ý.
* **Giải pháp Kỹ thuật**:
  * Nâng cấp cơ chế phân bổ trọng số động cho thuật toán N4 (Xếp hạng địa điểm) và N6 (Xếp hạng hoạt động).
  * Nếu một kênh đầu vào (Text, Tags, hoặc Ảnh) bị trống, trọng số của nó sẽ tự động được thu hồi và tái phân bổ tỉ lệ thuận cho các kênh hiện có (Existing Channels).
  * **Công thức phân bổ hiệu dụng**:
    $$\text{Weight}_{\text{effective}}(c) = \frac{\text{Weight}_{\text{raw}}(c) \times \mathbb{I}(c \text{ is active})}{\sum_{k \in \text{Channels}} \text{Weight}_{\text{raw}}(k) \times \mathbb{I}(k \text{ is active})}$$
* **Ý nghĩa Báo cáo**: Tăng tối đa độ chính xác của mô hình xếp hạng trong mọi ngữ cảnh dữ liệu khuyết thiếu.

### 2. Cơ chế Scaling Tự Nhiên & Smoothstep Dead-Zone Scaling — `fix(n4, n6)`
* **Vấn đề trước đây**: Hệ thống ép điểm số cao nhất (Top 1) về giá trị tuyệt đối `1.0` (Min-Max Scaling cưỡng bức). Điều này làm mất đi mức độ tự tin thực tế của mô hình (ví dụ: một gợi ý cực kỳ khớp cũng có điểm 1.0, mà một gợi ý kém khớp nhưng đứng đầu danh sách cũng bị nâng lên 1.0).
* **Giải pháp Kỹ thuật**:
  * Loại bỏ cơ chế Min-Max động trên từng batch.
  * Thay thế bằng thuật toán **Absolute Smoothstep Dead-Zone Scaling** (`0.65 + shaped * 0.30`). Thuật toán sử dụng hàm định hình phi tuyến giúp giữ nguyên phân bố tương đồng thực tế của không gian vector.
* **Ý nghĩa Báo cáo**: Giữ nguyên tính trung thực của không gian vector nhúng, tạo ra khoảng cách trực quan mượt mà giữa các gợi ý xuất sắc (ở mức `90%-95%`) với các gợi ý thông thường (`70%-80%`).

---

## 📌 PHẦN 2: CÁC TÍNH NĂNG MỚI NÂNG CẤP CHIỀU SÂU (MÔ-ĐUN N9 ĐẾN N17)

### 1. Tích Hợp Nguồn Cào Đa Kênh & Lịch Sử JSONB — `feat(n3, n9-n15)`
* **Mô tả Tính năng**: Nâng cấp toàn diện cơ sở dữ liệu để lưu trữ lịch sử người dùng và đồng bộ hóa ngoại tuyến POI đa nguồn phong phú.
* **Chi tiết Kỹ thuật**:
  * **Dữ liệu Đa Nguồn (N9-N14)**: Tích hợp 6 bảng riêng biệt cho 6 nhà cung cấp dữ liệu bản đồ lớn thế giới (`activities_osm`, `activities_goong`, `activities_foursquare`, `activities_overture`, `activities_wikidata`, `activities_geoapify`) cùng bảng theo dõi trạng thái cào dữ liệu `activity_fetch_status`.
  * **Xác thực & Lịch sử Đăng nhập (N15)**: Thiết lập bảng `users` bảo mật và bảng `rec_history` sử dụng kiểu dữ liệu `JSONB` động để lưu trọn vẹn Input/Output của mỗi lượt đề xuất. Người dùng có thể click `"Tải phiên"` để khôi phục chính xác 100% trạng thái cũ về Zustand store mà không cần gọi lại LLM đắt đỏ.

### 2. Giao Diện Bản Đồ Tương Tác Next.js & Quy Trình Phản Hồi — `feat(n16, n17)`
* **Mô tả Tính năng**: Chuyển đổi toàn diện giao diện từ Streamlit sang **Next.js + Tailwind CSS** cao cấp tích hợp bản đồ khám phá 3D và Feedback Loop để tối ưu điểm số.
* **Chi tiết Kỹ thuật**:
  * **Discovery Map 3D**: Bản đồ tương tác hiển thị tọa độ địa điểm với **cụm hoạt động lan tỏa hình tròn** (bán kính 350m tránh đè marker). Tích hợp sẵn lớp phủ hiển thị rõ ràng và tuân thủ tuyệt đối chủ quyền **Hoàng Sa & Trường Sa** của Việt Nam.
  * **Quy trình Phản hồi (N17)**: Thiết lập Feedback Loop ghi nhận phản hồi Toàn cục (Global) và Cục bộ (Local) trực tiếp vào Postgres để tái cân chỉnh trọng số vector cho các lượt truy vấn sau.
  * **Các tinh chỉnh giao diện nâng cao**:
    * *Tải tuần tự Waterfall*: Sử dụng React Query dependent chain để kích hoạt gọi API hoạt động lần lượt từ Top 1 $\rightarrow$ Top 5, tránh nghẽn luồng Backend.
    * *Phân tách Cache theo Sở thích*: Đưa mã hóa sở thích (`preferenceSignature`) vào `queryKey` của React Query để tự động gọi lại API khi đổi bộ lọc.
    * *Việt hóa nhãn tối giản*: Dịch nghĩa toàn bộ nhãn thô và rút ngắn tối đa **3 từ** (ví dụ: *"Canyoning"* $\rightarrow$ *"Vượt thác"*, *"Fine dining"* $\rightarrow$ *"Fine Dining"*) giúp giao diện gọn gàng, tinh tế.

---

## 📌 PHẦN 3: ĐIỂM SỤP ĐỔ CUỐI CÙNG & CƠ CHẾ CHỐNG SẬP (FINAL POINTS OF FAILURE)

Để hệ thống hoạt động ổn định trong thực tế, dự án được trang bị các cơ chế tự bảo vệ và dự phòng tại hai điểm sụp đổ nhạy cảm nhất của toàn bộ chuỗi xử lý:

### 1. Điểm lỗi Cơ sở dữ liệu (PostgreSQL Connection Failure)
* **Nguy cơ sụp đổ**: Kết nối PostgreSQL (`N3`) bị gián đoạn đột ngột (do nghẽn mạng, sự cố server database hoặc quá tải kết nối) có thể làm crash toàn bộ API hoặc treo luồng xử lý của hệ thống.
* **Cơ chế Chống sập (Mitigation)**:
  * **Circuit-Breaker & Exponential Backoff**: Khi xảy ra lỗi kết nối Postgres, hệ thống tự động kích hoạt tiến trình thử lại tối đa 3 lần với khoảng thời gian chờ tăng dần theo cấp số nhân (exponential delay).
  * **Tự động chuyển hướng JSON Fallback**: Nếu số lần thất bại đạt giới hạn (3 lần), Circuit-Breaker sẽ tự động chuyển sang trạng thái **MỞ (OPEN)** trong 30 giây. Trong thời gian này, mọi yêu cầu đọc/ghi dữ liệu sẽ lập tức được chuyển hướng sang bộ lưu trữ JSON dự phòng (`fallback_db.json` trên bộ nhớ đệm máy chủ) mà không tạo thêm kết nối vật lý nào đến Postgres, giữ cho ứng dụng hoạt động liên tục.

### 2. Điểm lỗi API Mô hình Ngôn ngữ (Groq / LLM Rate Limit & Outage)
* **Nguy cơ sụp đổ**: Groq API (sử dụng cho tạo hoạt động N5, trích xuất ảnh N2) bị giới hạn băng thông (Rate Limit HTTP 429), hết hạn ngạch tài khoản miễn phí, hoặc máy chủ LLM bị sập.
* **Cơ chế Chống sập (Mitigation)**:
  * **Ưu tiên Dữ liệu thật (Pre-seeded DB over LLM)**: Thiết lập lõi N8 ưu tiên truy vấn các hoạt động thực tế từ **N9-N14** đã được cào và lưu trữ sẵn trong Postgres. Gọi API **N5 (LLM)** chỉ được dùng như phương án cứu cánh cuối cùng (fallback) khi cơ sở dữ liệu trả về ít hơn 3 hoạt động cho địa điểm đó.
  * **Tự động phục hồi lỗi HTTP (Retryable Handler)**: Tích hợp bộ xử lý lỗi trong `groq_provider.py` tự động phát hiện và thử lại (retry) với các mã lỗi HTTP có khả năng phục hồi (như 429 rate limit, 500, 503).
  * **Cơ chế dự phòng bằng Mẫu (Templates Fallback)**: Nếu LLM hoàn toàn thất bại hoặc trả về số lượng hoạt động không đạt yêu cầu tối thiểu (`< 5`), mô-đun N5 tự động kích hoạt **Động cơ Sinh hoạt động theo Mẫu Ngoại tuyến (`_expand_templates`)** từ ngân hàng dữ liệu mẫu (`ACTIVITY_TYPE_BANK`). Động cơ này tự động phân tích hồ sơ địa điểm (`LOCATION_PROFILES`) kết hợp với các biến thể điều chỉnh (`VARIATION_MODIFIERS`) để tạo ra các hoạt động đa dạng, chân thực và tùy biến theo tên địa phương mà không gây lỗi ứng dụng.
  * **Fallback List rỗng an toàn**: Nếu tất cả các phương án trên (cả LLM và Template Engine) gặp lỗi nghiêm trọng không mong muốn, hệ thống sẽ tự động bắt ngoại lệ cấp cao nhất và trả về mảng rỗng để luồng tạo lộ trình chính tiếp tục hoạt động mượt mà thay vì báo lỗi hệ thống (HTTP 500).

---

## 📌 PHẦN 4: CÁC CẢI TIẾN KỸ THUẬT & DEVOPS KHÁC

### 1. Tối ưu hóa Bộ nhớ RAM trên N8 Orchestrator — `feat(n8)`
* **Lazy Image Loading**: Loại bỏ dữ liệu ảnh nhị phân (Base64) cồng kềnh khỏi cache đệm RAM. Ảnh địa điểm được tách riêng và tải động qua API `/api/images/{location_id}_{idx}.jpg` chỉ khi hiển thị trên màn hình.
* **Database Fingerprint TTL**: Thiết lập bộ đệm trạng thái (Cache TTL 10 giây) để kiểm tra dấu vân tay của Postgres, hạn chế tối đa các truy vấn kiểm tra đệm liên tục xuống đĩa cứng.
* **Bảo mật & Phòng chống Đúp Request**: Sử dụng `hmac.compare_digest` để bảo vệ mã khóa API nội bộ (`X-Internal-Key`) chống timing attack; chặn người dùng click đúp nút tìm kiếm bằng bộ lọc Request Fingerprint luồng an toàn (thread-safe lock), trả về lỗi `409 Conflict`.

### 2. Bộ Khởi động Đa Nền tảng Siêu Tương thích (PowerShell-Free) — `feat(devops)`
* **Tập lệnh run.bat (Windows)**: Loại bỏ hoàn toàn PowerShell, thay thế bằng các lệnh Python một dòng siêu nhẹ để so sánh ngày sửa đổi file (`os.path.getmtime`), kiểm tra cổng mạng bằng thư viện `socket` và kiểm tra HTTP bằng `urllib.request`. Tránh bị chính sách bảo mật hệ thống chặn.
* **Tập lệnh run.sh (Linux & macOS)**: Tự động phát hiện phiên bản Python (`python3`/`python`). Sử dụng bộ bẫy tín hiệu `trap` trong Bash để khi bấm Ctrl+C ở terminal chính, script sẽ tự động quét và dừng triệt để các tiến trình chạy ngầm Next.js và Flask, giải phóng cổng mạng sạch sẽ.

---

## 📌 PHẦN 5: BẢN TÓM TẮT ĐỐI CHIẾU NHANH (MÃ HÓA CHO BÁO CÁO)

| Phân Loại | Module | Tên Cải Tiến | Trạng Thế | Mô tả chi tiết kỹ thuật |
| :--- | :--- | :--- | :--- | :--- |
| **Bug Fix** | **N4 / N6** | Trọng số kênh động | **Hoàn thành** | Tái phân bổ trọng số khi khuyết thiếu kênh thông tin đầu vào. |
| **Bug Fix** | **N4 / N6** | Smoothstep Scaling | **Hoàn thành** | Giữ nguyên độ tương đồng thực tế thay vì Min-Max ép buộc. |
| **Feature** | **N3 / N9-N14**| Seed DB đa nguồn | **Hoàn thành** | Tích hợp 6 bảng cào bản đồ và bảng lưu lịch sử `JSONB` của Postgres. |
| **Feature** | **N15** | Tải/Khôi phục phiên | **Hoàn thành** | Tải lại chính xác lộ trình cũ về Zustand từ bảng lịch sử `rec_history`. |
| **Feature** | **N16 / N17**| Giao diện Next.js & Feedback|**Hoàn thành**| Discovery Map 3D, chủ quyền biển đảo, waterfall sequential load, và Feedback loop. |
| **Feature** | **N8** | Lazy Image Load | **Hoàn thành** | Loại bỏ ảnh khỏi cache đệm RAM, tải động ảnh qua API phụ riêng. |
| **Feature** | **N8** | Chống sập Postgres | **Hoàn thành** | Circuit-Breaker tự động chuyển sang JSON dự phòng khi mất kết nối DB. |
| **Feature** | **N5 / N8** | Chống sập Groq LLM | **Hoàn thành** | Ưu tiên dữ liệu cào thật, retry thông minh, fallback templates ngoại tuyến, mảng rỗng an toàn. |
| **Feature** | **DevOps** | Run Script không PowerShell|**Hoàn thành**| Thay thế bằng Python một dòng tương thích tuyệt đối Win 10/11 & Linux/macOS. |
