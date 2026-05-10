"""
N7 — Travel Planner UI (Streamlit + custom design system).

Flow:
  1. Hero + questionnaire (7 questions → tags)
  2. Submit → /recommend → top-5 locations
  3. Parallel /activities per location → top-5 activities mỗi loc

UI polish handled in styles.py:
  - Design tokens (colors / font / spacing)
  - CSS injection
  - Component renderers: hero, section_header, tag_summary, location_card,
    activity_skeleton, activities list, sidebar_brand
"""

import streamlit as st
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import base64

from styles import (
    inject_css,
    render_hero,
    render_section_header,
    render_tag_summary,
    render_location_card,
    render_activity_skeleton,
    render_activities,
    render_sidebar_brand,
)

API_BASE = "http://localhost:5000"
MAX_ACTIVITY_CONCURRENCY = 3  # tránh 429 từ Gemini (15 RPM) / Groq (30 RPM)


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG + CSS
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Travel Planner — AI Recommender",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_brand()

    st.markdown("#### ⚙️ Configuration")
    provider_choice = st.selectbox(
        "LLM Provider",
        options=["auto", "gemini", "groq"],
        index=0,
        help="auto = dùng env LLM_PROVIDER. Chọn cụ thể để so sánh chất lượng 2 model.",
    )

    top_k_locations = st.slider("Số địa điểm gợi ý", 3, 8, 5)
    top_k_activities = st.slider("Số hoạt động mỗi địa điểm", 3, 10, 5)

    st.markdown("---")

    # Live stats từ /health
    with st.expander("📊 System Stats", expanded=False):
        try:
            r = requests.get(f"{API_BASE}/health", timeout=2)
            if r.ok:
                h = r.json()
                cache = h.get("llm_cache", {})
                chain = h.get("llm_chain", [])
                col_a, col_b = st.columns(2)
                col_a.metric("Cache Hits", cache.get("hits", 0))
                col_b.metric("Hit Rate", f"{cache.get('hit_rate', 0):.0%}")
                st.caption(f"Cache size: {cache.get('size', 0)}/{cache.get('maxsize', 0)}")
                if chain:
                    st.caption("**LLM chain:**")
                    for p in chain:
                        st.caption(f"  ◆ {p['name']} ({p['model'][:30]}…)")
            else:
                st.caption("Backend not responding")
        except Exception:
            st.caption("⚠️ Backend offline")

    st.markdown("---")
    st.caption(
        "**Đồ án Tổng hợp 2025 — HCMUS**  \n"
        "Hệ gợi ý địa điểm du lịch dựa trên ngữ nghĩa + thuộc tính, "
        "tích hợp Gemini/Groq cho sinh hoạt động."
    )


# ─────────────────────────────────────────────────────────────
# QUESTIONNAIRE DATA — 7 câu, mỗi câu map vào ALL_TAGS ontology
# ─────────────────────────────────────────────────────────────
QUESTIONS = [
    {
        "q": "🏔️ Landscape",
        "sub": "Bạn thích phong cảnh nào?",
        "type": "radio",
        "tags": {
            "Beach & Coast":    ["beach", "island"],
            "Mountains":        ["mountain"],
            "Countryside":      ["rice terrace", "valley"],
            "River & Delta":    ["river", "delta"],
            "Forest & Nature":  ["forest", "national park"],
            "City":             ["city"],
        },
    },
    {
        "q": "🎯 Activities",
        "sub": "Chọn tối đa 3 hoạt động hấp dẫn bạn",
        "type": "multi",
        "max": 3,
        "tags": {
            "Trekking / Hiking":   ["trekking"],
            "Snorkeling / Diving": ["snorkeling"],
            "Kayaking":            ["kayaking"],
            "Cycling":             ["cycling"],
            "Motorbiking":         ["motorbiking"],
            "Camping":             ["camping"],
            "Boat Cruise":         ["boat cruise"],
            "Photography":         ["photography"],
            "Cooking Class":       ["cooking class"],
            "Spa & Wellness":      ["spa"],
            "Sightseeing":         ["sightseeing"],
            "Surfing":             ["surfing"],
        },
    },
    {
        "q": "✨ Vibe",
        "sub": "Không khí bạn mong muốn (tối đa 2)",
        "type": "multi",
        "max": 2,
        "tags": {
            "Peaceful & Quiet":     ["peaceful"],
            "Adventurous & Wild":   ["adventure"],
            "Romantic & Intimate":  ["romantic"],
            "Vibrant & Lively":     ["vibrant"],
            "Off the Beaten Path":  ["off the beaten path"],
            "Instagrammable":       ["instagrammable"],
            "Cozy & Warm":          ["cozy"],
            "Authentic & Local":    ["authentic"],
        },
    },
    {
        "q": "👥 Companion",
        "sub": "Bạn đi cùng ai?",
        "type": "radio",
        "tags": {
            "Solo":          ["solo"],
            "Couple":        ["couple"],
            "Family":        ["family"],
            "Friends":       ["friends trip"],
            "Group / Team":  ["group"],
        },
    },
    {
        "q": "📅 Duration",
        "sub": "Chuyến đi kéo dài bao lâu?",
        "type": "radio",
        "tags": {
            "Day trip":            ["day trip"],
            "Weekend (2–3 days)":  ["weekend trip"],
            "1 week+":             ["long stay"],
        },
    },
    {
        "q": "💰 Budget",
        "sub": "Phong cách chi tiêu của bạn",
        "type": "radio",
        "tags": {
            "Budget / Backpacker": ["budget"],
            "Mid-range":           ["mid range"],
            "Luxury":              ["luxury"],
            "Homestay / Eco":      ["homestay"],
        },
    },
    {
        "q": "🍜 Food",
        "sub": "Sở thích ẩm thực (tùy chọn)",
        "type": "radio",
        "tags": {
            "Street food":   ["street food"],
            "Seafood":       ["seafood"],
            "Local cuisine": ["local cuisine"],
            "Fine dining":   ["fine dining"],
            "No preference": [],
        },
    },
]


# ═════════════════════════════════════════════════════════════
# INPUT SECTION — hero + form
# ═════════════════════════════════════════════════════════════
render_hero()

# Section 1: free text + image
render_section_header("1", "Kể chúng tôi về chuyến đi mơ ước")

col_text, col_image = st.columns([3, 2])
with col_text:
    user_text = st.text_area(
        "Mô tả chuyến đi lý tưởng (tùy chọn)",
        placeholder="Ví dụ: Mình muốn chuyến đi biển thư giãn, có hải sản ngon và ít đông người...",
        height=130,
    )

with col_image:
    uploaded_image = st.file_uploader(
        "Ảnh cảm hứng (tùy chọn)",
        type=["png", "jpg", "jpeg"],
        help="Upload ảnh bạn thích — hệ thống sẽ phân tích để tìm địa điểm tương tự.",
    )
    image_b64 = ""
    if uploaded_image:
        uploaded_image.seek(0)
        image_b64 = base64.b64encode(uploaded_image.read()).decode("utf-8")
        img = Image.open(uploaded_image)
        st.image(img, use_container_width=True)

# Section 2: questionnaire grid
render_section_header("2", "Sở thích của bạn")

tags = []
# 2-col grid: i%2 == 0 cột trái, i%2 == 1 cột phải
col_left, col_right = st.columns(2, gap="medium")
for i, item in enumerate(QUESTIONS):
    target_col = col_left if i % 2 == 0 else col_right
    with target_col:
        st.markdown(
            f'<div class="tx-q-card">'
            f'<div class="tx-q-title">{item["q"]}</div>'
            f'<div class="tx-q-sub">{item["sub"]}</div>',
            unsafe_allow_html=True,
        )
        if item["type"] == "radio":
            ans = st.radio(
                item["q"], list(item["tags"].keys()),
                key=f"q{i}", label_visibility="collapsed", horizontal=False,
            )
            tags += item["tags"].get(ans, [])
        else:
            max_sel = item.get("max", 3)
            ans = st.multiselect(
                item["q"], list(item["tags"].keys()),
                key=f"q{i}", max_selections=max_sel, label_visibility="collapsed",
                placeholder="Chọn một hoặc nhiều...",
            )
            for a in ans:
                tags += item["tags"].get(a, [])
        st.markdown("</div>", unsafe_allow_html=True)

# Dedupe giữ thứ tự
seen = set()
tags = [t for t in tags if not (t in seen or seen.add(t))]

render_tag_summary(tags)

# Section 3: submit
submit = st.button(
    "🚀 Tìm điểm đến hoàn hảo",
    use_container_width=True,
    type="primary",
)

st.divider()

# ═════════════════════════════════════════════════════════════
# OUTPUT SECTION — locations + activities
# ═════════════════════════════════════════════════════════════
if submit:
    if not user_text and not tags:
        st.warning("⚠️ Vui lòng trả lời ít nhất 1 câu hỏi hoặc mô tả chuyến đi.")
        st.stop()

    payload = {
        "text": user_text,
        "image": image_b64,
        "tags": tags,
        "constraints": {},
        "top_k_locations": top_k_locations,
    }

    # Summary strip trước khi call API
    st.markdown(
        f"""
        <div style="background:#f1f5f9; border-radius:10px; padding:0.6rem 1rem;
                    margin:0.5rem 0; font-size:0.85rem; color:#475569;
                    display:flex; gap:1.25rem; flex-wrap:wrap;">
            <span>📝 <b>{len(user_text)}</b> ký tự</span>
            <span>🏷️ <b>{len(tags)}</b> tags</span>
            <span>🖼️ ảnh: <b>{"có" if image_b64 else "không"}</b></span>
            <span>🎯 top-<b>{top_k_locations}</b> địa điểm</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Call /recommend
    try:
        with st.spinner("🔍 Đang phân tích sở thích và tìm địa điểm…"):
            res = requests.post(f"{API_BASE}/recommend", json=payload, timeout=60)
    except Exception as e:
        st.error(f"❌ Không kết nối được backend: {e}")
        st.stop()

    if res.status_code != 200:
        st.error(f"❌ Backend lỗi: {res.text[:300]}")
        st.stop()

    data = res.json()
    locations = data.get("locations", [])
    if not locations:
        st.warning("😕 Không tìm thấy địa điểm phù hợp. Thử đổi câu trả lời nhé.")
        st.stop()

    trace        = data.get("trace", {})
    user_trace   = trace.get("user", {})
    user_vectors = user_trace.get("user_vectors", {})
    text_k       = user_trace.get("n1_embedding", {}).get("text_k", 0)
    tags_k       = user_trace.get("n1_embedding", {}).get("tags_k", 0)
    img_desc     = user_trace.get("n2_image", {}).get("img_desc", "")

    render_section_header("3", f"Top {len(locations)} địa điểm phù hợp")

    # ── Render location cards + activity placeholders ──────────
    placeholders = []
    for rank, loc in enumerate(locations, 1):
        loc_id   = loc.get("location_id", "unknown")
        meta     = loc.get("metadata", {})
        name     = meta.get("name", loc_id)
        score    = loc.get("score", 0)
        reason   = loc.get("reason", "")
        desc     = meta.get("description", "")
        img_path = loc.get("image_path", "")

        # Mỗi location: 2 cột [loc card | activities]
        col_loc, col_act = st.columns([5, 4], gap="medium")
        with col_loc:
            render_location_card(rank, name, score, reason, desc, img_path)

        with col_act:
            st.markdown(
                '<div style="font-size:0.85rem; font-weight:700; color:#0369a1; '
                'text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">'
                '🎯 Gợi ý hoạt động</div>',
                unsafe_allow_html=True,
            )
            ph = st.empty()
            with ph.container():
                render_activity_skeleton(min(3, top_k_activities))

            placeholders.append({
                "placeholder": ph,
                "loc_id": loc_id,
                "meta": meta,
                "name": name,
            })

        st.markdown("<div style='margin:1.25rem 0;'></div>", unsafe_allow_html=True)

    # ── Fetch activities in parallel ───────────────────────────
    def _fetch_activities(item):
        loc_id = item["loc_id"]
        meta   = item["meta"]
        payload = {
            "text":         user_text,
            "img_desc":     img_desc,
            "tags":         tags,
            "text_k":       text_k,
            "tags_k":       tags_k,
            "user_vectors": user_vectors,
            "constraints":  {},
            "context":      {},
            "location":     {"location_id": loc_id, "metadata": meta},
            "top_k_activities": top_k_activities,
            "provider":     None if provider_choice == "auto" else provider_choice,
        }
        try:
            r = requests.post(f"{API_BASE}/activities", json=payload, timeout=120)
            if r.status_code == 200:
                resp = r.json()
                return item, resp.get("activities", []), resp.get("meta", {}), None
            return item, None, {}, f"HTTP {r.status_code}"
        except Exception as exc:
            return item, None, {}, str(exc)

    with ThreadPoolExecutor(max_workers=MAX_ACTIVITY_CONCURRENCY) as pool:
        futures = [pool.submit(_fetch_activities, it) for it in placeholders]
        for fut in as_completed(futures):
            item, activities, llm_meta, err = fut.result()
            ph = item["placeholder"]

            if err:
                with ph.container():
                    st.error(f"❌ Lỗi tải hoạt động cho {item['name']}: {err}")
                continue

            with ph.container():
                render_activities(activities or [], llm_meta or {})

    # ── Debug panel ─────────────────────────────────────────────
    with st.expander("🔬 Debug trace (advanced)"):
        tab1, tab2, tab3 = st.tabs(["Pipeline", "User vectors", "Raw"])
        with tab1:
            st.json({
                "n2_image_desc": user_trace.get("n2_image", {}).get("img_desc", ""),
                "n1_embedding":  user_trace.get("n1_embedding", {}),
                "n4_ranking":    trace.get("ranking", {}),
                "debug":         trace.get("debug", {}),
            })
        with tab2:
            st.json(user_trace.get("vector_dims", {}))
        with tab3:
            st.json(data)
