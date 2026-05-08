"""
views/input/__init__.py
"""
import base64
import streamlit as st

from .questionnaire import render_questionnaire_ui
from .freeform import render_text_input_tab, render_image_input_tab


def render_input_view() -> dict | None:
    """Render input UI. Returns a payload dict when submitted, else None."""

    # ── PERSISTENCE FIX: Ensure backup state keys always exist ──
    st.session_state.setdefault("saved_freeform_text", "")
    st.session_state.setdefault("saved_uploaded_file", None)
    st.session_state.setdefault("saved_questionnaire_tags", [])

    if "mode" not in st.session_state:
        st.session_state.mode = "📋 Trắc nghiệm"

    mode = st.session_state.mode

    st.markdown(
        "<p style='text-align:center; color:#8b949e; margin-bottom:30px; font-size:1.05rem;'>"
        "Hãy trả lời trắc nghiệm, viết vài dòng hoặc tải lên hình ảnh để bắt đầu.</p>",
        unsafe_allow_html=True,
    )

    # Temporary variable passed by reference to capture active changes
    tags: list[str] = list(st.session_state["saved_questionnaire_tags"])

    _, c_mid, _ = st.columns([1, 3, 1])

    with c_mid:
        if mode == "📋 Trắc nghiệm":
            render_questionnaire_ui(tags)
            _render_tag_summary(tags)
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
                use_container_width=True,
            )
        with col_reset:
            if st.button("🔄 Đặt lại", use_container_width=True, type="secondary"):
                _reset_questionnaire()
                st.rerun()

        if not submit_clicked:
            return None

        # ── PERSISTENCE FIX: Pull all values from the persistent backups ──
        user_text: str = st.session_state.get("saved_freeform_text", "")
        image_b64: str = ""

        uploaded = st.session_state.get("saved_uploaded_file")
        if uploaded is not None:
            uploaded.seek(0)
            image_b64 = base64.b64encode(uploaded.read()).decode("utf-8")

        # Combine both active modifications and backup tags securely
        unique_tags = list(set(tags + st.session_state["saved_questionnaire_tags"]))

        if not user_text and not unique_tags and not image_b64:
            st.warning("⚠️ Vui lòng cung cấp ít nhất một thông tin để tiếp tục.")
            return None

        st.session_state.mode = "📊 Kết quả"

        return {
            "text": user_text,
            "image": image_b64,
            "tags": unique_tags,
            "constraint": [],
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _render_tag_summary(tags: list[str]) -> None:
    """Show selected tags as visual badges so the user sees their choices."""
    unique = list(set(tags))
    if not unique:
        return
    badges = "".join(f'<span class="tag-badge">{t}</span>' for t in sorted(unique))
    st.markdown(
        f"""
        <div style="margin: -10px 0 20px;">
            <span style="font-size:0.8rem; color:#8b949e; margin-right:8px;">
                Đã chọn:
            </span>
            {badges}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _reset_questionnaire() -> None:
    """Clear all questionnaire checkbox states and clear saved inputs."""
    keys_to_delete = [
        k for k in st.session_state
        if k.startswith("chk_")
    ]
    for k in keys_to_delete:
        del st.session_state[k]

    # Reset backups
    st.session_state["saved_freeform_text"] = ""
    st.session_state["saved_uploaded_file"] = None
    st.session_state["saved_questionnaire_tags"] = []

    # Clear temp keys if they exist
    for k in ("freeform_text_input", "freeform_image_uploader"):
        if k in st.session_state:
            del st.session_state[k]
