"""
questionnaire.py — Renders travel preferences with complete progress and state persistence.
"""
import streamlit as st
from .questionnaire_data import QUESTIONNAIRE_CONFIG, EMOJI_MAP
from config import setup_logging
logger = setup_logging("N7.questionnaire")

# ─── Public Entry Point ───────────────────────────────────────────────────────


def render_questionnaire_ui(tags: list) -> None:
    """Renders the full questionnaire. Appends selected tags to `tags` in place."""
    st.session_state.setdefault("saved_questionnaire_tags", [])
    st.session_state.setdefault("saved_questionnaire_keys", [])

    # Always restore on every render. We use setdefault inside the restore
    # function so live checkbox values (already in session_state) are never
    # overwritten — only missing keys get filled from backup. This is safe to
    # call every frame and is the only reliable way to survive mode switches,
    # because Streamlit DOES clear widget keys for unmounted widgets in some
    # execution paths (e.g. st.rerun() triggered from a different component).
    _restore_checkbox_states_from_backup()

    total = len(QUESTIONNAIRE_CONFIG)
    answered = _count_answered_questions()
    _render_progress(answered, total)

    for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
        _render_question(q_id, q_data, tags)


# ─── State Synchronization & Recovery ─────────────────────────────────────────


def _restore_checkbox_states_from_backup() -> None:
    """Write checkbox widget keys from the saved-keys backup."""
    saved_keys = set(st.session_state.get("saved_questionnaire_keys", []))
    logger.info(f"Restoring {len(saved_keys)} checkbox keys from backup")
    if not saved_keys:
        return

    for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
        for cat_opts in q_data.get("categories", {}).values():
            for opt_name, _ in cat_opts.items():
                key = f"chk_{q_id}_{opt_name}"
                st.session_state.setdefault(key, key in saved_keys)

        for section_name, options in q_data.get("specifics", {}).items():
            for opt, _ in options.items():
                key = f"chk_opt_{q_id}_{section_name}_{opt}"
                st.session_state.setdefault(key, key in saved_keys)


def _update_saved_tags() -> None:
    """Re-derive the canonical tag list and keys from live checkbox states."""
    selected_tags: list[str] = []
    selected_keys: list[str] = []
    seen: set[str] = set()

    for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
        for cat_opts in q_data.get("categories", {}).values():
            for opt_name, tag_list in cat_opts.items():
                key = f"chk_{q_id}_{opt_name}"
                if st.session_state.get(key, False):
                    selected_keys.append(key)
                    for t in tag_list:
                        if t not in seen:
                            selected_tags.append(t)
                            seen.add(t)

        for section_name, options in q_data.get("specifics", {}).items():
            for opt, tag_list in options.items():
                key = f"chk_opt_{q_id}_{section_name}_{opt}"
                if st.session_state.get(key, False):
                    selected_keys.append(key)
                    for t in tag_list:
                        if t not in seen:
                            selected_tags.append(t)
                            seen.add(t)

    st.session_state["saved_questionnaire_tags"] = selected_tags
    st.session_state["saved_questionnaire_keys"] = selected_keys
    logger.info(f"Updated saved tags: {len(selected_tags)} tags, {len(selected_keys)} keys")


# ─── Progress ─────────────────────────────────────────────────────────────────


def _count_answered_questions() -> int:
    answered = 0
    for q_id, q_data in QUESTIONNAIRE_CONFIG.items():
        found = False
        for cat_opts in q_data.get("categories", {}).values():
            if any(st.session_state.get(f"chk_{q_id}_{opt}", False) for opt in cat_opts):
                answered += 1
                found = True
                break
        if not found:
            for section_name, options in q_data.get("specifics", {}).items():
                if any(
                    st.session_state.get(f"chk_opt_{q_id}_{section_name}_{opt}", False)
                    for opt in options
                ):
                    answered += 1
                    break
    return answered


def _render_progress(answered: int, total: int) -> None:
    dots_html = "".join(
        f'<div class="progress-dot {"done" if i < answered else ""}"></div>'
        for i in range(total)
    )
    st.markdown(
        f"""
        <div style="margin-bottom: 4px; font-size: 0.8rem; color: #8b949e;">
            Đã trả lời {answered}/{total} câu hỏi
        </div>
        <div class="progress-container">{dots_html}</div>
        """,
        unsafe_allow_html=True,
    )


# ─── Question Renderer ────────────────────────────────────────────────────────


def _render_question(q_id: str, q_data: dict, tags: list) -> None:
    is_multi = q_data.get("multi", False)
    max_select = q_data.get("max_select") if is_multi else None
    categories = q_data.get("categories", {})
    specifics = q_data.get("specifics", {})

    st.markdown(f"### {q_data['question']}")

    all_keys = [
        f"chk_{q_id}_{opt}"
        for cat_opts in categories.values()
        for opt in cat_opts
    ]

    if categories:
        if is_multi and max_select:
            count = sum(st.session_state.get(k, False) for k in all_keys)
            remaining = max_select - count
            msg = (
                f"Còn {remaining} lựa chọn"
                if remaining > 0
                else f"✅ Đã chọn đủ {max_select} lựa chọn"
            )
            st.caption(msg)

        if len(categories) == 1:
            _, cat_options = list(categories.items())[0]
            _render_option_row(q_id, cat_options, all_keys, is_multi, max_select, tags)
        else:
            cols = st.columns(len(categories))
            for col, (cat_name, cat_options) in zip(cols, categories.items()):
                with col:
                    _render_category_header(cat_name)
                    _render_option_column(q_id, cat_options, all_keys, is_multi, max_select, tags)

    if specifics:
        total_spec_selected = sum(
            st.session_state.get(f"chk_opt_{q_id}_{section_name}_{opt}", False)
            for section_name, options in specifics.items()
            for opt in options
        )
        badge = f" · {total_spec_selected} đã chọn" if total_spec_selected > 0 else ""
        with st.popover(f"▸ Tùy chọn chi tiết{badge}", width='stretch'):
            use_expander = len(specifics) > 1
            for section_name, options in specifics.items():
                _render_specifics_section(q_id, section_name, options, tags, use_expander)

    _render_divider()


# ─── Option Renderers ─────────────────────────────────────────────────────────


def _render_option_row(q_id, cat_options, all_keys, is_multi, max_select, tags):
    cols = st.columns(len(cat_options))
    for col, (opt_name, tag_list) in zip(cols, cat_options.items()):
        key = f"chk_{q_id}_{opt_name}"
        st.session_state.setdefault(key, False)
        with col:
            _render_checkbox(key, opt_name, all_keys, q_id, is_multi, max_select)
        if st.session_state[key]:
            tags.extend(tag_list)


def _render_option_column(q_id, cat_options, all_keys, is_multi, max_select, tags):
    for opt_name, tag_list in cat_options.items():
        key = f"chk_{q_id}_{opt_name}"
        st.session_state.setdefault(key, False)
        _render_checkbox(key, opt_name, all_keys, q_id, is_multi, max_select)
        if st.session_state[key]:
            tags.extend(tag_list)


def _render_checkbox(key, opt_name, all_keys, q_id, is_multi, max_select):
    emoji = EMOJI_MAP.get(opt_name, "✨")
    label = f"{emoji} {opt_name}"
    is_checked = st.session_state[key]

    if is_multi:
        count = sum(st.session_state.get(k, False) for k in all_keys)
        disabled = bool(max_select and count >= max_select and not is_checked)
        st.checkbox(label, key=key, disabled=disabled, on_change=_multi_select_callback)
    else:
        st.checkbox(
            label,
            key=key,
            on_change=_exclusive_select,
            kwargs={"selected_key": key, "all_keys": all_keys},
        )


def _exclusive_select(selected_key: str, all_keys: list) -> None:
    if st.session_state[selected_key]:
        for k in all_keys:
            if k != selected_key:
                st.session_state[k] = False
    _update_saved_tags()


def _multi_select_callback() -> None:
    _update_saved_tags()


# ─── Specifics Section ─────────────────────────────────────────────────────────


def _cap_spec_selection(changed_key: str, spec_keys: list, max_spec: int) -> None:
    if st.session_state.get(changed_key, False):
        current_count = sum(st.session_state.get(k, False) for k in spec_keys)
        if current_count > max_spec:
            st.session_state[changed_key] = False
    _update_saved_tags()


def _render_specifics_section(q_id, section_name, options, tags, use_expander=True):
    spec_keys = [f"chk_opt_{q_id}_{section_name}_{opt}" for opt in options]
    max_spec = 3

    current_count = sum(st.session_state.get(k, False) for k in spec_keys)

    def _render_content():
        remaining = max_spec - current_count
        msg = f"Còn {remaining} lựa chọn" if remaining > 0 else f"✅ Đã chọn đủ {max_spec}"
        st.caption(msg)

        for opt, tag_list in options.items():
            key = f"chk_opt_{q_id}_{section_name}_{opt}"
            st.session_state.setdefault(key, False)
            is_checked = st.session_state[key]
            disabled = (current_count >= max_spec) and not is_checked
            emoji = EMOJI_MAP.get(opt, "✨")
            st.checkbox(
                f"{emoji} {opt}",
                key=key,
                disabled=disabled,
                on_change=_cap_spec_selection,
                kwargs={"changed_key": key, "spec_keys": spec_keys, "max_spec": max_spec},
            )
            if st.session_state[key]:
                tags.extend(tag_list)

    if use_expander:
        badge = f" · {current_count}/{max_spec} đã chọn" if current_count > 0 else ""
        with st.expander(f"{section_name}{badge}"):
            _render_content()
    else:
        st.markdown(
            f"<div style='font-weight:700; font-size:0.85rem; color:#ff6b6b;"
            f"margin: 10px 0 4px 0; padding-bottom: 4px; border-bottom: 1px solid #30363d;'>"
            f"{section_name}</div>",
            unsafe_allow_html=True,
        )
        _render_content()


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _render_category_header(cat_name: str) -> None:
    st.markdown(
        f"""<div style="text-align: center; font-weight: 700; font-size: 1rem;
            color: #e6edf3; margin-bottom: 10px; padding-bottom: 5px;
            border-bottom: 2px solid #ff6b6b;">{cat_name}</div>""",
        unsafe_allow_html=True,
    )


def _render_divider() -> None:
    st.markdown(
        "<div style='margin-bottom: 50px; border-bottom: 1px solid #30363d;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)