"""
views/input/__init__.py

Renders the active input mode and handles submission.
Supports multiple images.
"""
import base64
import streamlit as st
from config import setup_logging
logger = setup_logging("N7.input")

from .questionnaire import render_questionnaire_ui
from .questionnaire_data import QUESTIONNAIRE_CONFIG
from .freeform import render_text_input_tab, render_image_input_tab


def _save_all_input_state() -> None:
    """Snapshot the currently active input channel into session_state backups."""
    current_mode = st.session_state.get("mode")
    logger.info(f"Snapshotting state for mode: {current_mode}")

    # ── Questionnaire ──
    if current_mode == "📋 Trắc nghiệm":
        selected_tags: list[str] = []
        selected_keys: list[str] = []
        seen_tags: set[str] = set()

        for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
            for cat_opts in q_data.get("categories", {}).values():
                for opt_name, tag_list in cat_opts.items():
                    key = f"chk_{q_id}_{opt_name}"
                    if st.session_state.get(key, False):
                        selected_keys.append(key)
                        for t in tag_list:
                            if t not in seen_tags:
                                selected_tags.append(t)
                                seen_tags.add(t)

            for section_name, options in q_data.get("specifics", {}).items():
                for opt, tag_list in options.items():
                    key = f"chk_opt_{q_id}_{section_name}_{opt}"
                    if st.session_state.get(key, False):
                        selected_keys.append(key)
                        for t in tag_list:
                            if t not in seen_tags:
                                selected_tags.append(t)
                                seen_tags.add(t)

        st.session_state["saved_questionnaire_tags"] = selected_tags
        st.session_state["saved_questionnaire_keys"] = selected_keys

    # ── Freeform text ──
    elif current_mode == "✍️ Văn bản tự do":
        if "freeform_text_input" in st.session_state:
            st.session_state["saved_freeform_text"] = st.session_state["freeform_text_input"]

    # ── Image upload ──
    elif current_mode == "📸 Hình ảnh":
        raw_list = st.session_state.get("freeform_image_uploader")
        if raw_list:
            st.session_state["saved_uploaded_files"] = raw_list
            bytes_list = []
            for up in raw_list:
                try:
                    up.seek(0)
                    bytes_list.append(up.read())
                    up.seek(0)
                except Exception:
                    pass
            st.session_state["saved_images_bytes"] = bytes_list
        else:
            st.session_state["saved_uploaded_files"] = []
            st.session_state["saved_images_bytes"] = []


def render_input_view() -> dict | None:
    """Render input UI. Returns a payload dict when submitted, else None."""

    # Ensure all backup keys exist
    st.session_state.setdefault("saved_freeform_text", "")
    st.session_state.setdefault("saved_uploaded_files", [])
    st.session_state.setdefault("saved_images_bytes", [])
    st.session_state.setdefault("saved_questionnaire_tags", [])
    st.session_state.setdefault("saved_questionnaire_keys", [])
    st.session_state.setdefault("mode", "📋 Trắc nghiệm")

    mode = st.session_state.mode

    st.markdown(
        "<p style='text-align:center; color:#8b949e; margin-bottom:30px; font-size:1.05rem;'>"
        "Hãy trả lời trắc nghiệm, viết vài dòng hoặc tải lên hình ảnh để bắt đầu.</p>",
        unsafe_allow_html=True,
    )

    tags_buffer: list[str] = []

    _, c_mid, _ = st.columns([1, 3, 1])

    with c_mid:
        if mode == "📋 Trắc nghiệm":
            render_questionnaire_ui(tags_buffer)
            _render_tag_summary(tags_buffer)
        elif mode == "✍️ Văn bản tự do":
            render_text_input_tab()
        elif mode == "📸 Hình ảnh":
            render_image_input_tab()

        st.markdown("<br>", unsafe_allow_html=True)

        col_submit, col_reset = st.columns([4, 1])
        with col_submit:
            submit_clicked = st.button(
                "🗺️ Gợi ý trải nghiệm du lịch",
                type="primary",
                width='stretch',
            )
        with col_reset:
            if st.button("🔄 Đặt lại", width='stretch', type="secondary"):
                _reset_questionnaire()
                st.rerun()

    if not submit_clicked:
        return None

    # ── SUBMIT PRESSED ──
    logger.info("Submit button clicked")
    _save_all_input_state()

    user_text: str = st.session_state.get("saved_freeform_text", "")
    all_tags: list[str] = st.session_state.get("saved_questionnaire_tags", [])

    images_b64: list[str] = []
    # Use saved_images_bytes for maximum reliability
    img_bytes_list = st.session_state.get("saved_images_bytes", [])
    for b in img_bytes_list:
        try:
            images_b64.append(base64.b64encode(b).decode("utf-8"))
        except Exception:
            pass

    if not user_text and not all_tags and not images_b64:
        st.warning("⚠️ Vui lòng cung cấp ít nhất một thông tin để tiếp tục.")
        return None

    st.session_state.mode = "📊 Kết quả"

    logger.info(f"Payload aggregation: {len(all_tags)} tags, {len(user_text)} chars text, images={len(images_b64)}")

    return {
        "text": user_text,
        "images": images_b64,
        "tags": all_tags,
        "constraint": [],
    }


def _render_tag_summary(tags: list[str]) -> None:
    unique = list(set(tags))
    if not unique:
        return
    badges = "".join(f'<span class="tag-badge">{t}</span>' for t in sorted(unique))
    st.markdown(
        f"""
        <div style="margin: -10px 0 20px;">
            <span style="font-size:0.8rem; color:#8b949e; margin-right:8px;">Đã chọn:</span>
            {badges}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _reset_questionnaire() -> None:
    logger.info("Resetting all questionnaire and freeform state")
    for k in [k for k in st.session_state if k.startswith("chk_")]:
        del st.session_state[k]

    st.session_state["saved_freeform_text"] = ""
    st.session_state["saved_uploaded_files"] = []
    st.session_state["saved_images_bytes"] = []
    st.session_state["saved_questionnaire_tags"] = []
    st.session_state["saved_questionnaire_keys"] = []

    for k in ("freeform_text_input", "freeform_image_uploader"):
        st.session_state.pop(k, None)