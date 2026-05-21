# Tài liệu Kỹ thuật Dự án

Thư mục `docs/` là bộ tài liệu kỹ thuật trung tâm của dự án **Travel Experience Planner**. Bộ tài liệu này được tổ chức theo hướng phục vụ trực tiếp cho:

- viết báo cáo tổng kết học thuật
- trình bày kiến trúc hệ thống
- phân tích chi tiết từng module
- đối chiếu quyết định thiết kế với hành vi thực tế của code

Thay vì chỉ đóng vai trò “index file”, tài liệu trong thư mục này được sắp xếp theo logic từ tổng quan đến chi tiết, từ nền tảng học thuật đến triển khai kỹ thuật.

---

## 1. Cách đọc tài liệu theo thứ tự hợp lý

Nếu mục tiêu là hiểu hệ thống như một báo cáo hoàn chỉnh, nên đọc theo thứ tự sau:

1. **Tổng quan kiến trúc hệ thống**
   - [Tổng quan kiến trúc](architecture/system_overview.md)
2. **Các ý tưởng nền tảng của semantic pipeline**
   - [Hệ thống gắn thẻ và ontology](architecture/tagging_system.md)
   - [Cơ chế trọng số động](architecture/dynamic_weighting.md)
3. **Các module triển khai cụ thể**
   - [N0: Module mẫu khởi tạo](modules/n0_sample.md)
   - [N1: Nhúng vector đa kênh](modules/n1_embedding.md)
   - [N2: Xử lý hình ảnh (vision-to-text)](modules/n2_image_processing.md)
   - [N3: Tầng dữ liệu và lưu trữ](modules/n3_database.md)
   - [N4: Xếp hạng địa điểm](modules/n4_location_ranking.md)
   - [N5: Sinh hoạt động (LLM-first)](modules/n5_activity_generation.md)
   - [N6: Xếp hạng hoạt động](modules/n6_activity_ranking.md)
   - [N9–N14: Thu thập hoạt động đa nguồn](modules/n9_n14_activity_retrievals.md)
   - [N16: Giao diện Next.js Web App](modules/n16_nextjs_ui.md)
   - [N8: Điều phối API (Orchestrator)](modules/n8_orchestrator.md)
   - [N17: Xử lý phản hồi và tinh chỉnh truy vấn](modules/n17_feedback_processing.md)
4. **Các tài liệu tổng hợp ở mức dự án**
   - [Lý do lựa chọn công nghệ](project/technology_stack.md)
   - [Các hạn chế đã biết](project/known_limitations.md)
   - [Hướng dẫn ghép thành báo cáo hoàn chỉnh](project/report_structure_guide.md)

---

## 2. Cấu trúc tài liệu

### Kiến trúc

Nhóm tài liệu này mô tả tư duy thiết kế hệ thống ở mức vĩ mô:

- [architecture/system_overview.md](architecture/system_overview.md): toàn cảnh kiến trúc, luồng dữ liệu và vai trò các module
- [architecture/tagging_system.md](architecture/tagging_system.md): ontology, tag expansion, dilution và tag budget
- [architecture/dynamic_weighting.md](architecture/dynamic_weighting.md): cách hệ thống điều tiết tín hiệu semantic theo chất lượng đầu vào

### Module

Nhóm tài liệu này đi sâu vào từng thành phần triển khai:

- [modules/n0_sample.md](modules/n0_sample.md): module mẫu dùng làm khuôn chuẩn
- [modules/n1_embedding.md](modules/n1_embedding.md): tiền xử lý, augmentation và multi-channel embedding
- [modules/n2_image_processing.md](modules/n2_image_processing.md): chuyển hình ảnh thành mô tả ngữ nghĩa (vision-to-text)
- [modules/n3_database.md](modules/n3_database.md): persistence layer với PostgreSQL và pgvector
- [modules/n4_location_ranking.md](modules/n4_location_ranking.md): semantic ranking cho địa điểm
- [modules/n5_activity_generation.md](modules/n5_activity_generation.md): sinh ứng viên hoạt động theo chiến lược LLM-first
- [modules/n6_activity_ranking.md](modules/n6_activity_ranking.md): hybrid scoring và suy luận preference
- [modules/n9_n14_activity_retrievals.md](modules/n9_n14_activity_retrievals.md): thu thập hoạt động đa nguồn (OSM, Goong, Foursquare, Overture, Wikidata, Geoapify)
- [modules/n16_nextjs_ui.md](modules/n16_nextjs_ui.md): giao diện Next.js, trạng thái phiên bất đồng bộ, Zustand store, lazy loading ảnh và Auth/Profiles
- [modules/n8_orchestrator.md](modules/n8_orchestrator.md): orchestration, cache và điều phối endpoint
- [modules/n17_feedback_processing.md](modules/n17_feedback_processing.md): query refinement từ phản hồi người dùng

### Dự án

Nhóm tài liệu này phục vụ phần tổng hợp và đánh giá trong báo cáo:

- [project/technology_stack.md](project/technology_stack.md): phân tích lựa chọn công nghệ theo ràng buộc bài toán
- [project/known_limitations.md](project/known_limitations.md): các giới hạn hiện tại và ảnh hưởng của chúng
- [project/report_structure_guide.md](project/report_structure_guide.md): gợi ý ghép các tài liệu thành báo cáo nộp học thuật

### Sơ đồ

Thư mục [diagrams/](diagrams/) chứa các hình minh họa hỗ trợ cho:

- báo cáo tổng quan hệ thống
- phần mô tả pipeline
- phần giải thích từng module

---

## 3. Mục tiêu học thuật của bộ tài liệu

Bộ tài liệu này không chỉ nhằm “giải thích code”, mà còn nhằm thể hiện rõ các lớp tư duy kỹ thuật phía sau hệ thống:

- vì sao cần semantic augmentation
- vì sao cần dynamic weighting thay vì scoring cố định
- vì sao tagging phải có ontology và cơ chế kiểm soát dilution
- vì sao kiến trúc module hóa giúp hệ thống dễ benchmark, dễ giải thích và dễ mở rộng

Do đó, các tài liệu được viết theo văn phong báo cáo kỹ thuật: nhấn mạnh phân tích, lập luận thiết kế, ý nghĩa kiến trúc và mối liên hệ giữa các module, thay vì chỉ liệt kê API hoặc mô tả bề mặt.
