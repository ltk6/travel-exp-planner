import streamlit as st
import html
from .api import send_feedback, fetch_activities
from config import setup_logging

logger = setup_logging("N7.result")

# --- Design Tokens (Original alt_n7_ui Reddish Theme) ---
COLORS = {
    "primary":     "#ff6b6b",
    "primary_dim": "#cc3333",
    "accent":      "#ff6b6b",
    "surface":     "#161b22",
    "bg":          "#0d1117",
    "border":      "#30363d",
    "text":        "#e6edf3",
    "text_muted":  "#8b949e",
    "success":     "#238636",
    "error":       "#da3633",
}

# --- CSS Injection ---
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Be Vietnam Pro', sans-serif !important;
}}

.stApp {{ background-color: {COLORS["bg"]}; }}

h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, .stText {{
    color: {COLORS["text"]} !important;
}}

.tx-section-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 2rem 0 1rem 0;
}}
.tx-section-header .tx-step {{
    width: 32px; height: 32px;
    border-radius: 50%;
    background: {COLORS["primary"]};
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
}}
.tx-section-header h2 {{
    margin: 0;
    font-size: 1.4rem;
    font-weight: 700;
    color: {COLORS["text"]};
    letter-spacing: -0.01em;
}}

.tx-loc-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    overflow: hidden;
    height: 100%;
    transition: all 0.2s ease;
}}
.tx-loc-card .tx-loc-image {{
    width: 100%;
    height: 375px;
    object-fit: cover;
    display: block;
}}
.tx-loc-card .tx-loc-image-placeholder {{
    width: 100%;
    height: 375px;
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["primary_dim"]} 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 3rem;
}}
.tx-loc-card .tx-loc-body {{ padding: 1.25rem; }}
.tx-loc-card .tx-loc-title {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {COLORS["text"]};
    margin: 0 0 0.35rem 0;
}}
.tx-loc-card .tx-loc-rank {{
    display: inline-block;
    background: {COLORS["accent"]};
    color: white;
    width: 28px; height: 28px;
    border-radius: 50%;
    font-weight: 700;
    font-size: 0.9rem;
    text-align: center;
    line-height: 28px;
    margin-right: 0.5rem;
}}

.tx-score-wrap {{ margin: 0.75rem 0; }}
.tx-score-label {{
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: {COLORS["text_muted"]};
    text-transform: uppercase;
    font-weight: 600;
    margin-bottom: 0.3rem;
}}
.tx-score-bar {{
    background: {COLORS["border"]};
    height: 6px;
    border-radius: 999px;
    overflow: hidden;
}}
.tx-score-fill {{
    height: 100%;
    background: linear-gradient(90deg, {COLORS["primary_dim"]} 0%, {COLORS["primary"]} 100%);
    border-radius: 999px;
}}

.tx-reason {{
    background: #1f1015;
    border-left: 3px solid {COLORS["primary"]};
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    color: {COLORS["text"]};
    margin: 0.5rem 0;
}}

.tx-loc-desc {{
    font-size: 0.9rem;
    color: {COLORS["text_muted"]};
    line-height: 1.5;
}}

.tx-act-list {{ display: flex; flex-direction: column; gap: 0.6rem; margin-top: 0.5rem; }}
.tx-act-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    animation: txFadeIn 0.4s ease;
}}
.tx-act-head {{ display: flex; justify-content: space-between; align-items: baseline; gap: 0.5rem; }}
.tx-act-name {{ font-weight: 600; font-size: 0.95rem; color: {COLORS["text"]}; flex: 1; }}
.tx-act-score {{
    font-size: 0.75rem;
    font-weight: 700;
    color: {COLORS["primary"]};
    background: #1f1015;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
}}
.tx-act-type {{ font-size: 0.7rem; color: {COLORS["text_muted"]}; text-transform: uppercase; font-weight: 600; margin-right: 0.5rem; }}
.tx-act-reason {{ font-size: 0.82rem; color: {COLORS["text_muted"]}; line-height: 1.45; }}

.tx-meta-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
}}
.tx-meta-pill.gemini {{ background: {COLORS["primary_dim"]}; color: white; }}

.tx-feedback-card {{
    background: #1f1015;
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 1rem;
    margin-top: 0.5rem;
}}
.tx-feedback-label {{
    font-size: 0.8rem;
    font-weight: 700;
    color: {COLORS["primary"]};
    text-transform: uppercase;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}}

.tx-skeleton {{
    background: linear-gradient(90deg, #161b22 0%, #21262d 50%, #161b22 100%);
    background-size: 200% 100%;
    animation: txShimmer 1.4s ease-in-out infinite;
    border-radius: 8px;
}}
.tx-skel-line {{ height: 12px; margin: 0.35rem 0; }}
.tx-skel-card {{ border: 1px solid {COLORS["border"]}; border-radius: 10px; padding: 0.75rem 0.9rem; margin-bottom: 0.6rem; }}

@keyframes txShimmer {{ 0% {{ background-position: 200% 0; }} 100% {{ background-position: -200% 0; }} }}
@keyframes txFadeIn {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
"""

def _handle_feedback(endpoint: str, fb_text: str, current_body: dict):
    with st.spinner("AI đang xử lý yêu cầu..."):
        body = current_body.copy()
        body["feedback"] = fb_text
        new_results = send_feedback(endpoint, body)
        
        if "error" in new_results:
            st.error(f"Lỗi: {new_results['error']}")
        else:
            st.toast("✅ Đã cập nhật!")
            if endpoint == "recommend":
                st.session_state.results = new_results
                st.session_state.activity_results = {}
            else:
                final_loc_id = new_results.get("location_id") or current_body.get("location", {}).get("location_id")
                if final_loc_id:
                    st.session_state.activity_results[final_loc_id] = new_results
            st.rerun()

def render_activities_ui(activities_data: dict):
    acts = activities_data.get("activities", [])
    llm_meta = activities_data.get("meta", {})
    p = (llm_meta.get("provider_used") or "ai").lower()
    m = (llm_meta.get("model_used") or "").split("/")[-1]
    model_text = f"{p} · {m}" if m else p
    
    st.markdown(f'<div class="tx-meta-row"><span class="tx-meta-pill gemini">✦ {model_text}</span></div>', unsafe_allow_html=True)
    if not acts:
        st.write("Không tìm thấy hoạt động phù hợp.")
        return

    cards_html = ""
    for act in acts[:5]:
        a_m = act.get("metadata", {})
        a_n = a_m.get("name", "Hoạt động")
        a_d = a_m.get("description", "")
        a_s = act.get("score", 0)
        a_r = act.get("reason", "")
        a_t = a_m.get("activity_type", "")
        t_line = f'<span class="tx-act-type">● {html.escape(a_t)}</span>' if a_t else ""
        cards_html += (
            f'<div class="tx-act-card">'
            f'<div class="tx-act-head"><div class="tx-act-name">{html.escape(a_n)}</div>'
            f'<div class="tx-act-score">{a_s:.2f}</div></div>'
            f'{t_line}'
            f'<div class="tx-act-reason">💡 {html.escape(a_r)}</div>'
            f'<div class="tx-act-desc">{html.escape(a_d)}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="tx-act-list">{cards_html}</div>', unsafe_allow_html=True)

def render_result_view(data: dict = None):
    if data:
        st.session_state.results = data
    else:
        data = st.session_state.get("results", {})

    if "activity_results" not in st.session_state:
        st.session_state.activity_results = {}

    locations = data.get("locations", [])
    trace = data.get("trace", {})
    user_trace = trace.get("user", {})
    user_input = user_trace.get("input", {})
    
    user_text = user_input.get("text", "")
    tags = user_input.get("tags", [])
    img_desc = user_trace.get("n2_image", {}).get("img_desc", "")
    user_vectors = user_trace.get("user_vectors", {})
    text_k = user_trace.get("n1_embedding", {}).get("text_k", 0)
    tags_k = user_trace.get("n1_embedding", {}).get("tags_k", 0)
    constraints = user_input.get("constraints", {})
    context_data = user_input.get("context", {})

    st.markdown(CSS, unsafe_allow_html=True)
    
    if not locations:
        st.warning("Không có kết quả nào.")
        return

    st.markdown(f'<div class="tx-section-header"><div class="tx-step">5</div><h2>Top {min(5, len(locations))} địa điểm phù hợp</h2></div>', unsafe_allow_html=True)

    # --- PASS 1: RENDER ALL LOCATIONS FIRST ---
    for rank, loc in enumerate(locations[:5], 1):
        loc_id = loc.get("location_id", "unknown")
        meta = loc.get("metadata", {})
        name = meta.get("name", loc_id)
        score = loc.get("score", 0)
        reason = loc.get("reason", "")
        desc = meta.get("description", "")
        img_list = loc.get("images", [])
        img_path = img_list[0] if img_list else ""
        
        col_loc, col_act = st.columns([5, 4], gap="medium")
        
        with col_loc:
            pct = max(0, min(100, round(float(score) * 100)))
            img_html = f'<img src="{html.escape(img_path)}" class="tx-loc-image" />' if img_path else '<div class="tx-loc-image-placeholder">🌏</div>'
            reason_html = f'<div class="tx-reason">💡 {html.escape(reason)}</div>' if reason else ""
            st.markdown(f'''
                <div class="tx-loc-card">
                    {img_html}
                    <div class="tx-loc-body">
                        <h3 class="tx-loc-title"><span class="tx-loc-rank">{rank}</span>{html.escape(name)}</h3>
                        <div class="tx-score-wrap">
                            <div class="tx-score-label"><span>Match Score</span><span>{score:.2f}</span></div>
                            <div class="tx-score-bar"><div class="tx-score-fill" style="width: {pct}%"></div></div>
                        </div>
                        {reason_html}
                        <p class="tx-loc-desc">{html.escape(desc)}</p>
                    </div>
                </div>
            ''', unsafe_allow_html=True)

        with col_act:
            st.markdown(f'<div style="font-size:0.85rem; font-weight:700; color:{COLORS["primary"]}; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">🎯 Gợi ý hoạt động</div>', unsafe_allow_html=True)
            
            if loc_id in st.session_state.activity_results:
                render_activities_ui(st.session_state.activity_results[loc_id])
            else:
                # Placeholder Skeleton
                skel = "".join(['<div class="tx-skel-card"><div class="tx-skeleton tx-skel-line" style="width: 70%;"></div><div class="tx-skeleton tx-skel-line" style="width: 90%; height: 8px;"></div></div>' for _ in range(3)])
                st.markdown(f'<div class="tx-act-list">{skel}</div>', unsafe_allow_html=True)
            
            # Local feedback box (Always visible)
            st.markdown('<div class="tx-feedback-card"><div class="tx-feedback-label">✨ Tinh chỉnh hoạt động</div>', unsafe_allow_html=True)
            fb_key = f"fb_act_{loc_id}"
            fb_val = st.text_area("Thay đổi?", placeholder="Ví dụ: 'Tìm thêm các quán cafe có view thung lũng', 'Thêm hoạt động trekking nhẹ nhàng cho gia đình', hoặc 'Đổi sang các món ăn đặc sản địa phương'...", key=fb_key, label_visibility="collapsed", height=80)
            if st.button("🚀 Cập nhật", key=f"btn_act_{loc_id}", use_container_width=True):
                if fb_val:
                    fb_body = {
                        "text": user_text, "tags": tags, "img_desc": img_desc,
                        "text_k": text_k, "tags_k": tags_k, "user_vectors": user_vectors,
                        "location": {"location_id": loc_id, "metadata": meta}
                    }
                    _handle_feedback("activities", fb_val, fb_body)
            st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

    # --- PASS 2: SEQUENTIAL FETCHING (Bottom of script) ---
    for loc in locations[:5]:
        loc_id = loc.get("location_id")
        if loc_id not in st.session_state.activity_results:
            try:
                # Use a global spinner at the bottom while fetching missing data
                with st.spinner(f"Đang tìm hoạt động cho {loc.get('metadata', {}).get('name', loc_id)}..."):
                    result = fetch_activities(
                        loc_id=loc_id, 
                        meta=loc.get("metadata", {}), 
                        user_text=user_text,
                        img_desc=img_desc, 
                        tags=tags, 
                        text_k=text_k, 
                        tags_k=tags_k,
                        user_vectors=user_vectors, 
                        provider=st.session_state.get("llm_provider"),
                    )
                    st.session_state.activity_results[loc_id] = result
                    st.rerun()
            except Exception as e:
                st.error(f"Lỗi tải hoạt động: {e}")
                break

    # --- Global Feedback ---
    all_loaded = all(loc.get("location_id") in st.session_state.activity_results for loc in locations[:5])
    if all_loaded:
        st.markdown('<div style="margin-top: 5rem;"></div>', unsafe_allow_html=True)
        st.markdown(f'''
            <div class="tx-section-header">
                <div class="tx-step" style="background: {COLORS["accent"]}">🔄</div>
                <h2>Bạn muốn thay đổi toàn bộ lộ trình?</h2>
            </div>
            <div style="background: {COLORS["surface"]}; border: 1px solid {COLORS["border"]}; border-radius: 12px; padding: 0.75rem 1.25rem; margin-top: 0.75rem;">
                <p style="font-size: 0.9rem; color: {COLORS["text_muted"]}; margin-bottom: 0.5rem; line-height: 1.4;">
                    💡 <b>Lưu ý:</b> Việc gửi yêu cầu mới sẽ xóa lộ trình hiện tại để AI tính toán lại toàn bộ theo gu của bạn.
                </p>
        ''', unsafe_allow_html=True)
        
        fb_g = st.text_area("Yêu cầu thay đổi tổng thể:", placeholder="Ví dụ: 'Tôi muốn tìm những nơi yên tĩnh và ít khách du lịch hơn', 'Đổi sang các điểm đến gần biển', hoặc 'Tối ưu lộ trình với ngân sách tiết kiệm'...", key="fb_global_rec", label_visibility="collapsed", height=120)
        
        st.markdown('<div style="margin-top: 1rem;"></div>', unsafe_allow_html=True)
        if st.button("🚀 Cập nhật toàn bộ lộ trình", key="btn_global_rec", type="primary", use_container_width=True):
            if fb_g:
                _handle_feedback("recommend", fb_g, {
                    "user_input": {"text": user_text, "tags": tags, "img_desc": img_desc},
                    "image": st.session_state.get("search_image_b64", ""),
                    "constraints": constraints, "context": context_data
                })
        st.markdown('</div>', unsafe_allow_html=True)