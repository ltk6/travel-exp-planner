import streamlit as st

# --- Phỏng vấn bảng màu và CSS từ ứng dụng chính ---
COLORS = {
    "primary":     "#ff6b6b",
    "primary_dim": "#cc3333",
    "accent":      "#ff6b6b",
    "surface":     "#161b22",
    "bg":          "#0d1117",
    "border":      "#30363d",
    "text":        "#e6edf3",
    "text_muted":  "#8b949e",
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Be Vietnam Pro', sans-serif !important;
}}

.stApp {{ background-color: {COLORS["bg"]}; }}

.tx-section-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 2rem 0 1rem 0;
}}
.tx-section-header .tx-step {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: {COLORS["primary"]};
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
}}
.tx-section-header h2 {{
    margin: 0;
    font-size: 1.4rem;
    font-weight: 700;
    color: {COLORS["text"]};
    letter-spacing: -0.01em;
}}
</style>
""", unsafe_allow_html=True)

# --- Thành phần Preview ---
st.title("Preview: Global Feedback Component")

st.markdown('<div style="margin-top: 5rem;"></div>', unsafe_allow_html=True)
st.markdown(f'''
    <div class="tx-section-header">
        <div class="tx-step" style="background: {COLORS["accent"]}">🔄</div>
        <h2>Bạn muốn thay đổi toàn bộ lộ trình?</h2>
    </div>
    <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 12px; padding: 0.75rem 1.25rem; margin-top: 0.75rem;">
        <p style="font-size: 0.9rem; color: {COLORS["text_muted"]}; margin-bottom: 0.5rem; line-height: 1.4;">
            💡 <b>Lưu ý:</b> Việc gửi yêu cầu mới sẽ xóa lộ trình hiện tại để AI tính toán lại toàn bộ theo gu của bạn.
        </p>
''', unsafe_allow_html=True)

fb_g = st.text_area("Yêu cầu thay đổi tổng thể:", 
                    placeholder="Ví dụ: 'Tôi muốn tìm những nơi yên tĩnh và ít khách du lịch hơn', 'Đổi sang các điểm đến gần biển', hoặc 'Tối ưu lộ trình với ngân sách tiết kiệm'...", 
                    key="fb_global_rec_preview", 
                    label_visibility="collapsed", 
                    height=120)

st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
if st.button("🚀 Cập nhật toàn bộ lộ trình", key="btn_global_rec_preview", type="primary", use_container_width=True):
    if fb_g:
        st.success(f"Đã nhận phản hồi: {fb_g}")
st.markdown('</div>', unsafe_allow_html=True)

