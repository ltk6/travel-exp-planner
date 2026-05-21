# Module N7: Giao diện Streamlit (Đã chuyển đổi)

**Dự án:** Travel Experience Planner  
**Ngày:** 2026-05-21

---

> [!IMPORTANT]
> Giao diện người dùng của dự án **Travel Experience Planner** đã được chuyển đổi hoàn toàn từ Streamlit sang **Next.js Web App** cao cấp để đạt hiệu năng tối đa, hỗ trợ trải nghiệm bất đồng bộ mượt mà và khả năng lazy loading ảnh vượt trội.

Tài liệu thiết kế kiến trúc UI hiện tại đã được dời sang **N16**.

Vui lòng tham khảo tài liệu phân tích kỹ thuật và kiến trúc Frontend chính thức tại đây:

- 👉 **[Đọc tài liệu Module N16: Giao diện Next.js Web App](n16_nextjs_ui.md)**

---

## Vì sao Streamlit bị loại bỏ?

Streamlit là một công cụ tuyệt vời cho việc tạo prototype nhanh các ứng dụng dữ liệu, nhưng nó bộc lộ giới hạn nghiêm trọng khi dự án tiến lên mức độ ứng dụng tương tác cao (production-like):

1. **Kiến trúc Script-Rerun:** Mỗi lần người dùng nhấp một nút, Streamlit chạy lại toàn bộ mã Python từ trên xuống dưới. Điều này gây lãng phí bộ nhớ và tạo độ trễ rất lớn (lag).
2. **Thiếu khả năng Asynchronous Rendering:** Streamlit không thể "render giao diện trước, gọi API ngầm rồi điền vào sau" (như cơ chế React Suspense/React Query). Điều này bắt người dùng phải nhìn màn hình "Loading..." toàn trang trong 10-20 giây mỗi khi N5 hoặc N8 hoạt động.
3. **Quản lý state khó khăn:** Việc chuyển đổi giữa trang trắc nghiệm, trang kết quả, và trang quản lý tài khoản rất cồng kềnh trong Streamlit.
4. **Không thể Lazy Load:** Base64 ảnh phải được nhúng trực tiếp vào RAM server trước khi gửi xuống client, gây sập server nếu payload ảnh quá lớn.

Vì các giới hạn cứng về mặt kiến trúc trên, N7 đã chính thức được thay thế hoàn toàn bởi N16 (React 19 + Next.js App Router).
