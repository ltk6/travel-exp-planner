import streamlit as st
from config import setup_logging
logger = setup_logging("N7.header")

MODES = [
    "📋 Trắc nghiệm",
    "✍️ Văn bản tự do",
    "📸 Hình ảnh",
    "📊 Kết quả",
]


def _flush_widget_to_backup(widget_key: str, backup_key: str) -> None:
    """Copy a widget's current session_state value into its backup key."""
    if widget_key in st.session_state:
        st.session_state[backup_key] = st.session_state[widget_key]


def _save_all_input_state() -> None:
    """Snapshot the currently active input channel before switching modes."""
    from views.input.questionnaire_data import QUESTIONNAIRE_CONFIG

    # We use the mode BEFORE it gets updated to decide what to save.
    current_mode = st.session_state.get("mode")
    logger.info(f"Flushing state for mode: {current_mode}")

    # ── Questionnaire ──
    if current_mode == MODES[0]:
        selected_tags: list[str] = []
        selected_keys: list[str] = []
        seen_tags: set[str] = set()

        for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
            # Categories
            for cat_opts in q_data.get("categories", {}).values():
                for opt_name, tag_list in cat_opts.items():
                    key = f"chk_{q_id}_{opt_name}"
                    if st.session_state.get(key, False):
                        selected_keys.append(key)
                        for t in tag_list:
                            if t not in seen_tags:
                                selected_tags.append(t)
                                seen_tags.add(t)
            # Specifics
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
    elif current_mode == MODES[1]:
        _flush_widget_to_backup("freeform_text_input", "saved_freeform_text")

    # ── Image upload ──
    elif current_mode == MODES[2]:
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


def render_header(title: str = "🧭 Travel Planner") -> None:
    """Top nav with mode switcher buttons (not sticky)."""
    st.session_state.setdefault("mode", MODES[0])

    active = st.session_state.mode

    # Title (Non-sticky)
    st.markdown(f'<h1 class="header-title">{title}</h1>', unsafe_allow_html=True)

    # Nav Bar (Sticky)
    with st.container():
        st.markdown('<div class="sticky-header-anchor"></div>', unsafe_allow_html=True)
        cols = st.columns(6)

        mode_column_mapping = {
            MODES[0]: cols[0],
            MODES[1]: cols[1],
            MODES[2]: cols[2],
            MODES[3]: cols[5],
        }

        for mode, col in mode_column_mapping.items():
            with col:
                is_active = active == mode
                label = f"[ {mode} ]" if is_active else mode
                if st.button(
                    label,
                    width='stretch',
                    type="secondary",
                    key=f"nav_{mode}",
                ):
                    if not is_active:
                        logger.info(f"Nav button clicked: switching to {mode}")
                        # Save state of the CURRENT mode before switching to the NEW one
                        _save_all_input_state()
                        st.session_state.mode = mode
                        st.rerun()