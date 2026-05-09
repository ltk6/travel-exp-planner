"""
views/result/__init__.py

Performance improvements:
- Fetches ALL missing activities in a single pass before any rerun
- Eliminates the N-rerun-per-location loop from the original
- Single rerun after all locations are fetched
- Supports multiple images with a carousel in location cards
"""
import streamlit as st
import logging
import base64
from .api import fetch_activities

logger = logging.getLogger("alt_n7.result")

def _safe_image(img_data, **kwargs):
    """Safely handle base64 data URIs and raw bytes for st.image."""
    if 'width' in kwargs and kwargs['width'] == 'stretch':
        kwargs.pop('width')
        kwargs['use_container_width'] = True
        
    if isinstance(img_data, str) and img_data.startswith("data:image"):
        try:
            _, b64_str = img_data.split(",", 1)
            img_bytes = base64.b64decode(b64_str)
            st.image(img_bytes, **kwargs)
            return
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            pass
    st.image(img_data, **kwargs)

_DEFAULT_SHOW = 5

def render_result_view(data: dict) -> None:
    if "activity_results" not in st.session_state:
        st.session_state.activity_results = {}

    locations: list = data.get("locations", [])
    trace: dict = data.get("trace", {})
    user_trace: dict = trace.get("user", {})
    user_input: dict = user_trace.get("input", {})

    user_vectors: dict = user_trace.get("user_vectors", {})
    text_k: int = user_trace.get("n1_embedding", {}).get("text_k", 0)
    tags_k: int = user_trace.get("n1_embedding", {}).get("tags_k", 0)
    img_desc: str = user_trace.get("n2_image", {}).get("img_desc", "")
    user_text: str = user_input.get("text", "")
    tags: list = user_input.get("tags", [])
    # Now expecting a list of images (from the new backend contract)
    images_b64: list[str] = user_input.get("images", [])

    # ── Header ──
    st.success(f"✅ Tìm thấy {len(locations)} địa điểm phù hợp")

    # ── Input Summary ──
    with st.container(border=True):
        st.markdown("**📋 Thông tin tìm kiếm của bạn:**")

        # Prioritize local bytes for preview, fall back to backend base64
        local_images = st.session_state.get("saved_images_bytes", [])
        
        preview_images = []
        if local_images:
            preview_images = local_images
        elif images_b64:
            preview_images = [f"data:image/jpeg;base64,{img}" for img in images_b64]

        if tags:
            badges = "".join(f'<span class="tag-badge">{t}</span> ' for t in tags)
            st.markdown(f'<div style="margin-bottom: 12px;">{badges}</div>', unsafe_allow_html=True)

        col_text, col_img = st.columns([2, 1] if preview_images else [1, 0.001])
        
        with col_text:
            if user_text:
                st.markdown(f"> *\"{user_text}\"*")
            elif not tags and not preview_images:
                st.markdown("> *Không có văn bản mô tả*")
            
            if not user_text and tags:
                st.caption("Dựa trên các từ khóa bạn đã chọn ở phần trắc nghiệm.")

        if preview_images:
            with col_img:
                # Show first image or a small grid if multiple
                if len(preview_images) == 1:
                    _safe_image(preview_images[0], caption="Phong cảnh trong mơ", use_container_width=True)
                else:
                    st.caption(f"🖼️ {len(preview_images)} hình ảnh đã tải lên")
                    # Show a tiny grid for the summary
                    mini_cols = st.columns(3)
                    for i, img in enumerate(preview_images[:3]):
                        with mini_cols[i]:
                            _safe_image(img, use_container_width=True)

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
                    text_k=text_k,
                    tags_k=tags_k,
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
    
    # Support multiple images
    images: list[str] = loc.get("images", [])

    col_loc, col_act = st.columns(2, gap="large")

    with col_loc:
        st.markdown(f"### {name}")
        st.metric("Điểm phù hợp", f"{score:.4f}")
        if reason:
            st.info(f"💡 {reason}")
        if desc:
            st.write(desc)
        
        if images:
            # Image Carousel State
            idx_key = f"img_idx_{loc_id}"
            if idx_key not in st.session_state:
                st.session_state[idx_key] = 0
            
            curr_idx = st.session_state[idx_key]
            if curr_idx >= len(images):
                curr_idx = 0
                st.session_state[idx_key] = 0

            # Carousel UI with "arrow heads" inside columns
            st.markdown('<div class="carousel-container">', unsafe_allow_html=True)
            c_prev, c_img, c_next = st.columns([1, 10, 1])
            
            def _change_idx(delta, key=idx_key, total=len(images)):
                old_val = st.session_state[key]
                st.session_state[key] = (old_val + delta) % total
                logger.info(f"Carousel {loc_id} index changed: {old_val} -> {st.session_state[key]} (total={total})")

            with c_prev:
                st.button("<", key=f"prev_{loc_id}", on_click=_change_idx, args=(-1,))
            
            with c_img:
                try:
                    _safe_image(images[curr_idx], caption=f"{name} ({curr_idx + 1}/{len(images)})", use_container_width=True)
                except Exception:
                    st.caption("🖼️ Hình ảnh không khả dụng")
            
            with c_next:
                st.button(">", key=f"next_{loc_id}", on_click=_change_idx, args=(1,))
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.caption("🖼️ Không có hình ảnh")

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

        def _toggle_all(val, k=show_all_key):
            st.session_state[k] = val

        if len(filtered) > _DEFAULT_SHOW:
            hidden = len(filtered) - _DEFAULT_SHOW
            if not st.session_state[show_all_key]:
                st.button(
                    f"Xem thêm {hidden} hoạt động ▾",
                    key=f"more_{loc_id}_{selected_type}",
                    width='stretch',
                    on_click=_toggle_all,
                    args=(True,)
                )
            else:
                st.button(
                    "Thu gọn ▴",
                    key=f"less_{loc_id}_{selected_type}",
                    width='stretch',
                    on_click=_toggle_all,
                    args=(False,)
                )