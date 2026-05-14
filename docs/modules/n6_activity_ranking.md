# Module N6: Xếp hạng Hoạt động (Activity Ranking)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-14  

---

## 1. Vai trò của Module N6

Module N6 là bước tinh chỉnh cuối cùng trong hành trình gợi ý. Sau khi N5 sinh ra một danh sách các hoạt động, N6 sẽ xếp hạng chúng để đảm bảo những hoạt động phù hợp nhất với sở thích và phong cách của người dùng được hiển thị lên đầu.

---

## 2. Phương pháp xếp hạng hỗn hợp (Hybrid Scoring)

N6 kết hợp hai thế giới: **Ngữ nghĩa (Semantic)** và **Thuộc tính (Attributes)** với tỉ lệ 50/50.

### 2.1. Điểm Ngữ nghĩa (Semantic Score - 50%)
Sử dụng Cosine Similarity để so khớp vector yêu cầu của người dùng với nội dung của hoạt động. 
-   Kỹ thuật **Dead-zone scaling**: Vì các embedding thường có điểm số rất cao (~0.8), N6 áp dụng công thức `(sim - 0.5) * 2` để kéo giãn khoảng cách, giúp phân loại rõ rệt hơn.

### 2.2. Điểm Thuộc tính (Attribute Fit Score - 50%)
Hệ thống so khớp 3 chỉ số vận động và xã hội:
-   **Intensity (Cường độ):** Mức độ hào hứng/sôi nổi.
-   **Physical Level (Thể lực):** Mức độ vận động chân tay.
-   **Social Level (Tính xã hội):** Đi một mình hay đi theo nhóm.

---

## 3. Suy luận Sở thích (Preference Inference)

Điểm độc đáo của N6 là khả năng tự suy luận các chỉ số mục tiêu từ tags của người dùng thông qua các quy luật (rules):
-   Nếu người dùng chọn `peaceful`, hệ thống tự hiểu `Intensity` mục tiêu thấp.
-   Nếu người dùng chọn `trekking`, hệ thống tự hiểu `Physical Level` mục tiêu cao.
-   Nếu người dùng chọn `solo`, hệ thống tự hiểu `Social Level` mục tiêu thấp.

Cơ chế này cho phép hệ thống hoạt động chính xác ngay cả khi người dùng không trực tiếp nhập các chỉ số kỹ thuật này.

---

## 4. Quy trình xử lý (Process)

N6 thực hiện xếp hạng dựa trên dữ liệu đầu vào đã được chuẩn hóa:

1.  **Tính điểm Ngữ nghĩa (Semantic Scoring):** Sử dụng các vector đại diện của người dùng và của hoạt động (đã được cung cấp sẵn trong input) để tính toán độ tương đồng Cosine.
2.  **Suy luận Chỉ số Mục tiêu (Inference):** Dựa trên bộ nhãn (tags) của người dùng, N6 tự động xác định các giá trị mục tiêu cho `Physical`, `Intensity`, và `Social`.
3.  **Tính điểm Thuộc tính (Attribute Scoring):** Tính toán khoảng cách giữa chỉ số mục tiêu (suy luận) và chỉ số thực tế của từng hoạt động.
4.  **Kết hợp Hybrid:** Áp dụng công thức 50/50 để tổng hợp điểm Ngữ nghĩa và điểm Thuộc tính thành một điểm số duy nhất.
5.  **Xếp hạng & Reasoning:** Sắp xếp danh sách và tạo ra chuỗi giải thích (reason) dựa trên các tiêu chí có điểm số cao nhất.

---

## 5. Interface (API nội bộ)

-   **Input:** 
    -   `user_vectors`: Bộ vector đặc trưng của người dùng.
    -   `activities`: Danh sách các hoạt động (mỗi hoạt động đã kèm theo metadata và vector riêng).
    -   `tags`: Danh sách sở thích để suy luận chỉ số.
-   **Output:** Danh sách hoạt động đã xếp hạng kèm điểm số và lý do gợi ý.

---

## 5. Giao diện (Interface)

-   **Input:** 
    -   Bộ vector và tags của người dùng.
    -   Danh sách các hoạt động từ N5.
-   **Output:** Danh sách các hoạt động đã được xếp hạng tối ưu.

---

## 6. Tài liệu tham khảo

| # | Chủ đề | Nguồn tham khảo |
|---|---|---|
| 1 | Pinecone — Vector similarity: cosine vs dot product | [pinecone.io/learn/vector-similarity](https://www.pinecone.io/learn/vector-similarity/) |
| 2 | Hệ thống Trọng số Động (Internal Docs) | [docs/dynamic_weighting.md](dynamic_weighting.md) |
| 3 | BGE-M3 — Semantic similarity best practices | [huggingface.co/BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) |