"""
freeform.py — Text and Image input tabs with persistent state.
Supports multiple image uploads.
"""
import streamlit as st
from PIL import Image
from config import setup_logging
logger = setup_logging("N7.freeform")


def on_text_change() -> None:
    logger.info("Text input changed, updating backup")
    st.session_state["saved_freeform_text"] = st.session_state["freeform_text_input"]


def on_image_change() -> None:
    """Snapshot both the file objects and their raw bytes for maximum reliability."""
    uploaded_list = st.session_state.get("freeform_image_uploader")
    if uploaded_list:
        logger.info(f"Uploaded {len(uploaded_list)} images")
        st.session_state["saved_uploaded_files"] = uploaded_list
        
        bytes_list = []
        for up in uploaded_list:
            up.seek(0)
            bytes_list.append(up.read())
            up.seek(0)
        st.session_state["saved_images_bytes"] = bytes_list
    else:
        st.session_state["saved_uploaded_files"] = []
        st.session_state["saved_images_bytes"] = []


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
    st.info("Hãy tải lên các bức ảnh mô tả phong cảnh trong mơ của bạn.")

    st.session_state.setdefault("saved_uploaded_files", [])
    st.session_state.setdefault("saved_images_bytes", [])

    st.file_uploader(
        "Tải lên các bức ảnh",
        type=["png", "jpg", "jpeg", "webp", "gif", "bmp"],
        key="freeform_image_uploader",
        accept_multiple_files=True,
        on_change=on_image_change,
    )

    # Resolve display: prefer live widget, fall back to bytes backup
    live_list = st.session_state.get("freeform_image_uploader")
    backup_bytes_list = st.session_state.get("saved_images_bytes")

    display_list = live_list if live_list else backup_bytes_list

    if display_list:
        cols = st.columns(3)
        for i, img_data in enumerate(display_list):
            with cols[i % 3]:
                try:
                    if hasattr(img_data, "seek"):
                        img_data.seek(0)
                    st.image(img_data, width='stretch')
                except Exception:
                    st.warning(f"⚠️ Lỗi hiển thị ảnh {i+1}")