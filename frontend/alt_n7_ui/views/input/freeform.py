"""
freeform.py — Text and Image input tabs with persistent state.
"""
import streamlit as st
from PIL import Image


def on_text_change() -> None:
    st.session_state["saved_freeform_text"] = st.session_state["freeform_text_input"]


def on_image_change() -> None:
    """Snapshot both the file object and its raw bytes for maximum reliability."""
    uploaded = st.session_state.get("freeform_image_uploader")
    if uploaded is not None:
        st.session_state["saved_uploaded_file"] = uploaded
        # Read bytes once and store them; this is the most reliable way to 
        # persist an image across widget unmounts in Streamlit.
        uploaded.seek(0)
        st.session_state["saved_image_bytes"] = uploaded.read()
        uploaded.seek(0) # Reset for others


def render_text_input_tab() -> None:
    st.info(
        "Hãy mô tả chi tiết chuyến du lịch trong mơ của bạn. Hãy đề cập đến những hoạt động "
        "bạn muốn tham gia, những địa điểm bạn muốn ghé thăm và bất kỳ yêu cầu đặc biệt nào khác."
    )

    st.session_state.setdefault("saved_freeform_text", "")

    st.text_area(
        "Describe your dream trip",
        value=st.session_state["saved_freeform_text"],
        placeholder=(
            "e.g., Tôi muốn thức dậy bằng tiếng sóng vỗ vào bờ, ăn hải sản tươi sống, "
            "đi lặn, và tìm một nơi yên tĩnh để đọc sách..."
        ),
        label_visibility="collapsed",
        height=250,
        key="freeform_text_input",
        on_change=on_text_change,
    )


def render_image_input_tab() -> None:
    st.info("Hãy tải lên một bức ảnh mô tả phong cảnh trong mơ của bạn.")

    st.session_state.setdefault("saved_uploaded_file", None)
    st.session_state.setdefault("saved_image_bytes", None)

    st.file_uploader(
        "Tải lên một bức ảnh",
        type=["png", "jpg", "jpeg"],
        key="freeform_image_uploader",
        accept_multiple_files=False,
        on_change=on_image_change,
    )

    # Resolve display: prefer live widget, fall back to bytes backup
    live = st.session_state.get("freeform_image_uploader")
    backup_bytes = st.session_state.get("saved_image_bytes")

    if live is not None:
        try:
            live.seek(0)
            st.image(live, caption="Phong cảnh bạn vừa chọn", width=400)
        except Exception:
            st.warning("⚠️ Không thể hiển thị ảnh.")
    elif backup_bytes is not None:
        st.caption("📎 Ảnh đã tải trước đó vẫn được giữ lại.")
        try:
            st.image(backup_bytes, caption="Phong cảnh trong mơ (đã lưu)", width=400)
        except Exception:
            st.warning("⚠️ Không thể hiển thị ảnh đã lưu.")