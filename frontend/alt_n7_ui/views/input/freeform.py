import streamlit as st
from PIL import Image
import base64

def on_text_change():
    """Callback to instantly persist the text input to session state."""
    st.session_state["saved_freeform_text"] = st.session_state["freeform_text_input"]

def on_image_change():
    """Callback to instantly persist the uploaded file to session state."""
    st.session_state["saved_uploaded_file"] = st.session_state["freeform_image_uploader"]

def render_text_input_tab():
    st.info("Hãy mô tả chi tiết chuyến du lịch trong mơ của bạn. Hãy đề cập đến những hoạt động bạn muốn tham gia, những địa điểm bạn muốn ghé thăm và bất kỳ yêu cầu đặc biệt nào khác.")
    
    # Initialize the backup variable if not yet set
    if "saved_freeform_text" not in st.session_state:
        st.session_state["saved_freeform_text"] = ""

    user_text = st.text_area(
        "Describe your dream trip",
        value=st.session_state["saved_freeform_text"],
        placeholder="e.g., Tôi muốn thức dậy bằng tiếng sóng vỗ vào bờ, ăn hải sản tươi sống, đi lặn, và tìm một nơi yên tĩnh để đọc sách...",
        label_visibility="collapsed",
        height=250,
        key="freeform_text_input",
        on_change=on_text_change
    )
    return user_text

def render_image_input_tab():
    st.info("Hãy tải lên một bức ảnh mô tả phong cảnh trong mơ của bạn.")

    # Initialize the backup variable if not yet set
    if "saved_uploaded_file" not in st.session_state:
        st.session_state["saved_uploaded_file"] = None

    uploaded = st.file_uploader(
        "Tải lên một bức ảnh",
        type=["png", "jpg", "jpeg"],
        key="freeform_image_uploader",
        accept_multiple_files=False,
        on_change=on_image_change
    )

    # If the user switches away and returns, match widget's internal value to our persistent state
    if uploaded is None and st.session_state["saved_uploaded_file"] is not None:
        uploaded = st.session_state["saved_uploaded_file"]

    image_b64 = ""

    if uploaded is not None:
        # Prevent PIL from throwing errors if the file pointer was exhausted
        uploaded.seek(0)
        img = Image.open(uploaded)
        st.image(img, caption="Phong cảnh trong mơ", width=400)

        # Reset pointer again for reading
        uploaded.seek(0)
        image_b64 = base64.b64encode(uploaded.read()).decode("utf-8")

    return image_b64
