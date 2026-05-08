"""
views/result/__init__.py

Performance improvements:
- Fetches ALL missing activities in a single pass before any rerun
- Eliminates the N-rerun-per-location loop from the original
- Single rerun after all locations are fetched
"""
import streamlit as st
import logging
from .api import fetch_activities

logger = logging.getLogger("alt_n7.result")

_DEFAULT_SHOW = 5


def render_result_view(data: dict) -> None:
    if "activity_results" not in st.session_state:
        st.session_state.activity_results = {}

    locations: list = data.get("locations", [])
    trace: dict = data.get("trace", {})
    user_trace: dict = trace.get("user", {})
    user_input: dict = user_trace.get("input", {})

    user_vectors: dict = user_trace.get("user_vectors", {})
    sig_k: float = user_trace.get("n1_embedding", {}).get("sig_k", 0)
    img_desc: str = user_trace.get("n2_image", {}).get("img_desc", "")
    user_text: str = user_input.get("text", "")
    tags: list = user_input.get("tags", [])
    image_b64: str = user_input.get("image", "")

    # ── Header ──
    st.success(f"✅ Tìm thấy {len(locations)} địa điểm phù hợp")

    # ── Input Summary ──
    with st.container(border=True):
        st.markdown("**📋 Thông tin tìm kiếm của bạn:**")

        # Prioritize local bytes for preview, fall back to backend base64
        local_img = st.session_state.get("saved_image_bytes")
        preview_img = local_img if local_img is not None else (f"data:image/jpeg;base64,{image_b64}" if image_b64 else None)

        if tags:
            badges = "".join(f'<span class="tag-badge">{t}</span> ' for t in tags)
            st.markdown(f'<div style="margin-bottom: 12px;">{badges}</div>', unsafe_allow_html=True)

        col_text, col_img = st.columns([2, 1] if preview_img else [1, 0.001])
        
        with col_text:
            if user_text:
                st.markdown(f"> *\"{user_text}\"*")
            elif not tags and not preview_img:
                st.markdown("> *Không có văn bản mô tả*")
            
            if not user_text and tags:
                st.caption("Dựa trên các từ khóa bạn đã chọn ở phần trắc nghiệm.")

        if preview_img:
            with col_img:
                with st.container():
                    try:
                        st.image(preview_img, caption="Phong cảnh trong mơ", use_container_width=True)
                    except Exception:
                        st.caption("📷 Đã gửi hình ảnh")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("📍 Địa điểm gợi ý")

    if not locations:
        st.info("Không tìm thấy địa điểm nào phù hợp. Hãy thử lại với thông tin khác.")
        return

    # ── Identify which locations still need activity fetching ──
    missing = [
        loc for loc in locations
        if loc.get("location_id", "unknown") not in st.session_state.activity_results
    ]

    # ── Render all location cards (with placeholders for activities) ──
    placeholders: dict[str, st.delta_generator.DeltaGenerator] = {}
    for loc in locations:
        loc_id = loc.get("location_id", "unknown")
        ph = _render_location_card(loc)
        placeholders[loc_id] = ph
        st.divider()

    # ── Fill in already-cached activities immediately ──
    for loc_id, ph in placeholders.items():
        cached = st.session_state.activity_results.get(loc_id)
        if cached is not None:
            _render_activities(ph, cached, loc_id)

    # ── Batch-fetch all missing locations, rendering each as it arrives ──
    if missing:
        logger.info(f"Fetching activities for {len(missing)} missing locations")
        for loc in missing:
            loc_id = loc.get("location_id", "unknown")
            logger.info(f"Fetching activities for: {loc_id}")
            meta = loc.get("metadata", {})
            try:
                activities = fetch_activities(
                    loc_id=loc_id,
                    meta=meta,
                    user_text=user_text,
                    img_desc=img_desc,
                    tags=tags,
                    sig_k=sig_k,
                    user_vectors=user_vectors,
                )
                logger.info(f"Retrieved {len(activities)} activities for {loc_id}")
                st.session_state.activity_results[loc_id] = activities
            except Exception as exc:
                logger.error(f"Error fetching activities for {loc_id}: {exc}")
                st.session_state.activity_results[loc_id] = []
                with placeholders[loc_id].container():
                    st.error(f"Không tải được hoạt động: {exc}")
                continue

            # Render immediately after each fetch — no rerun needed
            _render_activities(placeholders[loc_id], activities, loc_id)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _render_location_card(loc: dict) -> st.delta_generator.DeltaGenerator:
    loc_id: str = loc.get("location_id", "unknown")
    meta: dict = loc.get("metadata", {})
    name: str = meta.get("name", loc_id)
    score: float = loc.get("score", 0)
    reason: str = loc.get("reason", "")
    desc: str = meta.get("description", "")
    img_path: str = loc.get("image_path", "")

    col_loc, col_act = st.columns(2, gap="large")

    with col_loc:
        st.markdown(f"### {name}")
        st.metric("Điểm phù hợp", f"{score:.4f}")
        if reason:
            st.info(f"💡 {reason}")
        if desc:
            st.write(desc)
        if img_path:
            try:
                st.image(img_path, caption=name, use_container_width=True)
            except Exception:
                st.caption("🖼️ Hình ảnh không khả dụng")

    with col_act:
        with st.container(border=True):
            st.markdown("#### 🎯 Hoạt động tại đây")
            placeholder = st.empty()
            with placeholder.container():
                st.caption("⏳ Đang tải…")

    return placeholder


def _render_activities(
    placeholder: st.delta_generator.DeltaGenerator,
    activities: list,
    loc_id: str,
) -> None:
    """Render up to _DEFAULT_SHOW activities per filter with show-more toggle."""
    if not activities:
        with placeholder.container():
            st.caption("Không có hoạt động nào được gợi ý.")
        return

    # Pre-compute type set once
    all_types = sorted(
        {a.get("metadata", {}).get("activity_type", "") for a in activities} - {""}
    )

    show_all_key = f"show_all_{loc_id}"
    st.session_state.setdefault(show_all_key, False)

    with placeholder.container():
        if all_types:
            selected_type = st.selectbox(
                "Lọc theo loại",
                options=["Tất cả"] + all_types,
                key=f"filter_{loc_id}",
                label_visibility="collapsed",
            )
            filter_key = f"filter_{loc_id}_prev"
            if st.session_state.get(filter_key) != selected_type:
                st.session_state[show_all_key] = False
                st.session_state[filter_key] = selected_type
        else:
            selected_type = "Tất cả"

        filtered = (
            activities
            if selected_type == "Tất cả"
            else [a for a in activities if a.get("metadata", {}).get("activity_type", "") == selected_type]
        )

        visible = filtered if st.session_state[show_all_key] else filtered[:_DEFAULT_SHOW]

        for act in visible:
            a_meta = act.get("metadata", {})
            a_type = a_meta.get("activity_type", "")
            a_name = a_meta.get("name", "Unknown")
            a_score = act.get("score", 0)
            a_reason = act.get("reason", "")
            with st.container(border=True):
                label = f"**{a_name}**"
                if a_type:
                    label += f" `{a_type}`"
                st.markdown(label)
                st.caption(f"Điểm: {a_score:.2f} — {a_reason}")

        if len(filtered) > _DEFAULT_SHOW:
            hidden = len(filtered) - _DEFAULT_SHOW
            if not st.session_state[show_all_key]:
                if st.button(
                    f"Xem thêm {hidden} hoạt động ▾",
                    key=f"more_{loc_id}_{selected_type}",
                    use_container_width=True,
                ):
                    st.session_state[show_all_key] = True
                    st.rerun()
            else:
                if st.button(
                    "Thu gọn ▴",
                    key=f"less_{loc_id}_{selected_type}",
                    use_container_width=True,
                ):
                    st.session_state[show_all_key] = False
                    st.rerun()