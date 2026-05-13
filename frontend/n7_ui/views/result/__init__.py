"""
views/result/__init__.py
Refactored result view to match n7_ui perfectly but using alt_n7_ui original theme.
Uses concurrent fetching (ThreadPoolExecutor) to prevent UI blocking.
"""
import streamlit as st
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from .api import fetch_activities
from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
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
    height: 250px;
    object-fit: cover;
    display: block;
}}
.tx-loc-card .tx-loc-image-placeholder {{
    width: 100%;
    height: 250px;
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
.tx-meta-pill.cache  {{ background: #1f1015; color: {COLORS["primary"]}; border: 1px solid {COLORS["primary"]}; }}
.tx-meta-pill.gemini {{ background: {COLORS["primary_dim"]}; color: white; }}

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

def render_activities_ui(activities_data: dict):
    acts = activities_data.get("activities", [])
    llm_meta = activities_data.get("meta", {})
    meta_html = ""
    if llm_meta.get("cache_hit"):
        meta_html = '<div class="tx-meta-row"><span class="tx-meta-pill cache">⚡ cached instantly</span></div>'
    else:
        p = (llm_meta.get("provider_used") or "ai").lower()
        meta_html = f'<div class="tx-meta-row"><span class="tx-meta-pill gemini">✦ {p}</span></div>'

    if not acts:
        st.markdown(meta_html + '<div class="tx-empty">Không tìm thấy hoạt động phù hợp</div>', unsafe_allow_html=True)
        return

    cards_html = ""
    for act in acts[:5]:
        a_m = act.get("metadata", {})
        a_n = a_m.get("name", "Hoạt động")
        a_s = act.get("score", 0)
        a_r = act.get("reason", "")
        a_t = a_m.get("activity_type", "")
        t_line = f'<span class="tx-act-type">● {html.escape(a_t)}</span>' if a_t else ""
        cards_html += (
            f'<div class="tx-act-card">'
            f'<div class="tx-act-head"><div class="tx-act-name">{html.escape(a_n)}</div>'
            f'<div class="tx-act-score">{a_s:.2f}</div></div>'
            f'{t_line}<div class="tx-act-reason">{html.escape(a_r)}</div></div>'
        )
    st.markdown(meta_html + f'<div class="tx-act-list">{cards_html}</div>', unsafe_allow_html=True)

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

    st.markdown(CSS, unsafe_allow_html=True)

    if not locations:
        st.warning("Không tìm thấy địa điểm nào phù hợp.")
        return

    st.markdown(
        f"""
        <div class="tx-section-header">
            <h2>Top {min(5, len(locations))} địa điểm phù hợp</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    activity_tasks = []
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
            
            st.markdown(
                f"""
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
                """,
                unsafe_allow_html=True,
            )

        with col_act:
            st.markdown(f'<div style="font-size:0.85rem; font-weight:700; color:{COLORS["primary"]}; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.5rem;">🎯 Gợi ý hoạt động</div>', unsafe_allow_html=True)
            ph = st.empty()
            if loc_id in st.session_state.activity_results:
                with ph.container():
                    render_activities_ui(st.session_state.activity_results[loc_id])
            else:
                with ph.container():
                    skel = "".join(['<div class="tx-skel-card"><div class="tx-skeleton tx-skel-line" style="width: 70%;"></div><div class="tx-skeleton tx-skel-line" style="width: 90%; height: 8px;"></div></div>' for _ in range(3)])
                    st.markdown(f'<div class="tx-act-list">{skel}</div>', unsafe_allow_html=True)
                activity_tasks.append({"loc_id": loc_id, "meta": meta, "placeholder": ph})

        st.divider()

    if activity_tasks:
        ctx = get_script_run_ctx()
        provider = st.session_state.get("llm_provider")
        def _fetch_worker(task, provider_val):
            add_script_run_ctx(ctx)
            try:
                res = fetch_activities(
                    loc_id=task["loc_id"], meta=task["meta"], user_text=user_text,
                    img_desc=img_desc, tags=tags, text_k=text_k, tags_k=tags_k,
                    user_vectors=user_vectors, provider=provider_val,
                )
                return task, res
            except Exception as e:
                return task, {"error": str(e)}

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(_fetch_worker, t, provider) for t in activity_tasks]
            for fut in as_completed(futures):
                task, result = fut.result()
                with task["placeholder"].container():
                    if "error" in result:
                        st.error(f"Lỗi: {result['error']}")
                    else:
                        st.session_state.activity_results[task["loc_id"]] = result
                        render_activities_ui(result)