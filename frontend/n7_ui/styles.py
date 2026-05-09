"""
styles.py — Design system cho Travel Planner UI.

Chứa 2 thứ:
  1. CSS tùy biến tiêm vào Streamlit qua st.markdown(unsafe_allow_html=True)
  2. Helper render các component tái sử dụng (location card, activity card,
     hero section, skeleton loader, chips)

Design principles:
  - Clean, modern, professional — phù hợp đồ án IT năm 2
  - Palette: sky blue (primary) + amber (accent) + neutral grays
  - Font: Plus Jakarta Sans (sans-serif hiện đại, dễ đọc)
  - Microinteractions: hover lift, fade-in, skeleton shimmer
  - Layout: grid-based, không lạm dụng divider
"""

import html
import streamlit as st


# =============================================================================
# DESIGN TOKENS
# =============================================================================

COLORS = {
    "primary":     "#0369a1",   # sky-700
    "primary_dim": "#0ea5e9",   # sky-500
    "accent":      "#f59e0b",   # amber-500
    "surface":     "#ffffff",
    "bg":          "#f8fafc",   # slate-50
    "border":      "#e2e8f0",   # slate-200
    "text":        "#0f172a",   # slate-900
    "text_muted":  "#64748b",   # slate-500
    "success":     "#10b981",
    "error":       "#ef4444",
}


# =============================================================================
# CSS INJECTION
# =============================================================================

CSS = f"""
<style>
/* ── Font ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
}}

/* ── Streamlit container tweaks ───────────────────────────────── */
.main .block-container {{
    padding-top: 1.5rem;
    max-width: 1280px;
}}

/* ── Hero section ─────────────────────────────────────────────── */
.tx-hero {{
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["primary_dim"]} 100%);
    color: white;
    padding: 2.5rem 2rem;
    border-radius: 20px;
    margin-bottom: 1.5rem;
    box-shadow: 0 10px 30px rgba(3, 105, 161, 0.25);
    position: relative;
    overflow: hidden;
}}
.tx-hero::after {{
    content: "";
    position: absolute;
    top: -60px; right: -60px;
    width: 240px; height: 240px;
    background: radial-gradient(circle, rgba(245, 158, 11, 0.35) 0%, transparent 70%);
}}
.tx-hero h1 {{
    font-size: 2.25rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.02em;
}}
.tx-hero p {{
    font-size: 1.05rem;
    opacity: 0.95;
    margin: 0;
    max-width: 640px;
}}
.tx-hero .tx-hero-badge {{
    display: inline-block;
    background: rgba(255, 255, 255, 0.2);
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    backdrop-filter: blur(10px);
}}

/* ── Section header ───────────────────────────────────────────── */
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

/* ── Question card (trong questionnaire) ─────────────────────── */
.tx-q-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 14px;
    padding: 1.25rem 1.25rem 0.25rem 1.25rem;
    margin-bottom: 0.75rem;
    transition: all 0.15s ease;
}}
.tx-q-card:hover {{
    border-color: {COLORS["primary_dim"]};
    box-shadow: 0 2px 12px rgba(14, 165, 233, 0.08);
}}
.tx-q-card .tx-q-title {{
    font-size: 1rem;
    font-weight: 600;
    color: {COLORS["text"]};
    margin-bottom: 0.5rem;
}}
.tx-q-card .tx-q-sub {{
    font-size: 0.8rem;
    color: {COLORS["text_muted"]};
    margin-bottom: 0.75rem;
}}

/* ── Tag summary ──────────────────────────────────────────────── */
.tx-tags-box {{
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 1px solid #fbbf24;
    border-radius: 12px;
    padding: 0.85rem 1rem;
    margin: 0.75rem 0;
}}
.tx-tags-box .tx-tags-label {{
    font-size: 0.75rem;
    font-weight: 700;
    color: #78350f;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.5rem;
}}
.tx-chip {{
    display: inline-block;
    background: rgba(255, 255, 255, 0.75);
    color: #78350f;
    padding: 0.2rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin: 0.15rem 0.3rem 0.15rem 0;
    border: 1px solid rgba(120, 53, 15, 0.15);
}}

/* ── Location card ────────────────────────────────────────────── */
.tx-loc-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    overflow: hidden;
    height: 100%;
    transition: all 0.2s ease;
}}
.tx-loc-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    border-color: {COLORS["primary_dim"]};
}}
.tx-loc-card .tx-loc-image {{
    width: 100%;
    height: 200px;
    object-fit: cover;
    display: block;
}}
.tx-loc-card .tx-loc-image-placeholder {{
    width: 100%;
    height: 200px;
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["primary_dim"]} 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 3rem;
}}
.tx-loc-card .tx-loc-body {{
    padding: 1.25rem;
}}
.tx-loc-card .tx-loc-title {{
    font-size: 1.35rem;
    font-weight: 700;
    color: {COLORS["text"]};
    margin: 0 0 0.35rem 0;
    letter-spacing: -0.01em;
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

/* Score bar */
.tx-score-wrap {{
    margin: 0.75rem 0;
}}
.tx-score-label {{
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: {COLORS["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 0.06em;
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
    background: linear-gradient(90deg, {COLORS["primary_dim"]} 0%, {COLORS["accent"]} 100%);
    border-radius: 999px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}}

.tx-reason {{
    background: #f0f9ff;
    border-left: 3px solid {COLORS["primary_dim"]};
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    font-size: 0.85rem;
    color: {COLORS["text"]};
    margin: 0.5rem 0;
    font-style: italic;
}}

.tx-loc-desc {{
    font-size: 0.9rem;
    color: {COLORS["text_muted"]};
    line-height: 1.5;
    margin: 0.5rem 0 0 0;
}}

/* ── Activity card ────────────────────────────────────────────── */
.tx-act-list {{
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-top: 0.5rem;
}}
.tx-act-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    transition: all 0.15s ease;
    animation: txFadeIn 0.4s ease;
}}
.tx-act-card:hover {{
    border-color: {COLORS["primary_dim"]};
    transform: translateX(4px);
}}
.tx-act-head {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}}
.tx-act-name {{
    font-weight: 600;
    font-size: 0.95rem;
    color: {COLORS["text"]};
    flex: 1;
    line-height: 1.3;
}}
.tx-act-score {{
    font-size: 0.75rem;
    font-weight: 700;
    color: {COLORS["primary"]};
    background: #e0f2fe;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    white-space: nowrap;
}}
.tx-act-type {{
    display: inline-block;
    font-size: 0.7rem;
    color: {COLORS["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
    margin-right: 0.5rem;
}}
.tx-act-reason {{
    font-size: 0.82rem;
    color: {COLORS["text_muted"]};
    line-height: 1.45;
    margin-top: 0.15rem;
}}

/* ── Provider meta badge ──────────────────────────────────────── */
.tx-meta-row {{
    display: flex;
    gap: 0.4rem;
    align-items: center;
    margin-bottom: 0.5rem;
    flex-wrap: wrap;
}}
.tx-meta-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    letter-spacing: 0.02em;
}}
.tx-meta-pill.cache  {{ background: #dcfce7; color: #166534; }}
.tx-meta-pill.gemini {{ background: #e0e7ff; color: #3730a3; }}
.tx-meta-pill.groq   {{ background: #fef3c7; color: #92400e; }}
.tx-meta-pill.latency {{ background: #f1f5f9; color: #475569; }}

/* ── Skeleton loader ──────────────────────────────────────────── */
.tx-skeleton {{
    background: linear-gradient(
        90deg,
        #f1f5f9 0%,
        #e2e8f0 50%,
        #f1f5f9 100%
    );
    background-size: 200% 100%;
    animation: txShimmer 1.4s ease-in-out infinite;
    border-radius: 8px;
}}
.tx-skel-line {{
    height: 12px;
    margin: 0.35rem 0;
}}
.tx-skel-card {{
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.6rem;
}}

/* ── Animations ──────────────────────────────────────────────── */
@keyframes txShimmer {{
    0%   {{ background-position: 200% 0; }}
    100% {{ background-position: -200% 0; }}
}}
@keyframes txFadeIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Buttons ──────────────────────────────────────────────────── */
.stButton > button {{
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["primary_dim"]} 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.75rem 1.5rem !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 4px 14px rgba(3, 105, 161, 0.25) !important;
    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(3, 105, 161, 0.35) !important;
}}

/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}}
.tx-sidebar-brand {{
    text-align: center;
    padding: 1rem 0 1.5rem 0;
    border-bottom: 1px solid {COLORS["border"]};
    margin-bottom: 1rem;
}}
.tx-sidebar-brand .tx-logo {{
    font-size: 2.5rem;
    line-height: 1;
}}
.tx-sidebar-brand h3 {{
    margin: 0.5rem 0 0 0;
    font-size: 1.1rem;
    font-weight: 700;
    background: linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["accent"]} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}}
.tx-sidebar-brand p {{
    margin: 0.25rem 0 0 0;
    font-size: 0.7rem;
    color: {COLORS["text_muted"]};
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

/* ── Empty state ─────────────────────────────────────────────── */
.tx-empty {{
    text-align: center;
    padding: 3rem 2rem;
    color: {COLORS["text_muted"]};
}}
.tx-empty .tx-empty-icon {{
    font-size: 3rem;
    opacity: 0.5;
}}

/* ── Hide Streamlit default chrome ───────────────────────────── */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
</style>
"""


def inject_css():
    """Inject CSS vào trang — gọi đúng 1 lần ngay đầu app."""
    st.markdown(CSS, unsafe_allow_html=True)


# =============================================================================
# RENDER HELPERS
# =============================================================================

def render_hero():
    """Hero section ở đầu trang."""
    st.markdown(
        """
        <div class="tx-hero">
            <span class="tx-hero-badge">✨ AI-powered recommendations</span>
            <h1>Tìm điểm đến hoàn hảo cho chuyến đi của bạn</h1>
            <p>Trả lời vài câu hỏi đơn giản, chúng tôi sẽ gợi ý địa điểm và các
            hoạt động phù hợp dựa trên sở thích, phong cách du lịch của bạn.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(step: str, title: str):
    """Header có số thứ tự step dạng circle."""
    st.markdown(
        f"""
        <div class="tx-section-header">
            <div class="tx-step">{html.escape(step)}</div>
            <h2>{html.escape(title)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tag_summary(tags: list):
    """Pill chip list các tag đã chọn."""
    if not tags:
        st.markdown(
            """
            <div class="tx-tags-box">
                <div class="tx-tags-label">🏷️ Chưa chọn tag nào</div>
                <div style="font-size:0.82rem; color:#92400e;">
                    Trả lời các câu hỏi để nhận gợi ý chính xác hơn.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    chips = "".join(f'<span class="tx-chip">{html.escape(t)}</span>' for t in tags)
    st.markdown(
        f"""
        <div class="tx-tags-box">
            <div class="tx-tags-label">🏷️ {len(tags)} tags selected</div>
            <div>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_location_card(rank: int, name: str, score: float, reason: str,
                          description: str, image_path: str = ""):
    """
    Location card đẹp: ảnh hero, rank badge, score bar gradient, reason highlight.

    Lưu ý: image_path có thể là URL hoặc empty. Khi empty, hiển thị gradient
    placeholder với emoji.
    """
    # Image block
    if image_path:
        img_html = f'<img src="{html.escape(image_path)}" class="tx-loc-image" alt="{html.escape(name)}" onerror="this.outerHTML=\'<div class=tx-loc-image-placeholder>🌏</div>\'" />'
    else:
        img_html = '<div class="tx-loc-image-placeholder">🌏</div>'

    # Score bar — clamp 0-100%
    pct = max(0, min(100, round(float(score) * 100)))

    # Description truncate
    desc = description or ""
    if len(desc) > 220:
        desc = desc[:217] + "…"

    reason_html = (
        f'<div class="tx-reason">💡 {html.escape(reason)}</div>' if reason else ""
    )

    st.markdown(
        f"""
        <div class="tx-loc-card">
            {img_html}
            <div class="tx-loc-body">
                <h3 class="tx-loc-title">
                    <span class="tx-loc-rank">{rank}</span>{html.escape(name)}
                </h3>
                <div class="tx-score-wrap">
                    <div class="tx-score-label">
                        <span>Match Score</span>
                        <span>{score:.2f}</span>
                    </div>
                    <div class="tx-score-bar">
                        <div class="tx-score-fill" style="width: {pct}%"></div>
                    </div>
                </div>
                {reason_html}
                <p class="tx-loc-desc">{html.escape(desc)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_activity_skeleton(n: int = 3):
    """Skeleton loader hiển thị trong lúc chờ activities."""
    cards = ""
    for _ in range(n):
        cards += """
        <div class="tx-skel-card">
            <div class="tx-skeleton tx-skel-line" style="width: 70%;"></div>
            <div class="tx-skeleton tx-skel-line" style="width: 90%; height: 8px;"></div>
            <div class="tx-skeleton tx-skel-line" style="width: 60%; height: 8px;"></div>
        </div>
        """
    st.markdown(
        f'<div class="tx-act-list">{cards}</div>',
        unsafe_allow_html=True,
    )


def _provider_meta_html(llm_meta: dict) -> str:
    """Pills hiển thị cache hit / provider / latency."""
    if not llm_meta:
        return ""
    cache_hit     = llm_meta.get("cache_hit", False)
    provider_used = (llm_meta.get("provider_used") or "?").lower()
    latency_ms    = llm_meta.get("latency_ms", 0)

    if cache_hit:
        return '<div class="tx-meta-row"><span class="tx-meta-pill cache">⚡ cached instantly</span></div>'

    provider_cls = provider_used if provider_used in ("gemini", "groq") else "latency"
    provider_icon = {"gemini": "✦", "groq": "⚙"}.get(provider_used, "🤖")
    latency_str = f"{latency_ms/1000:.1f}s" if latency_ms >= 1000 else f"{latency_ms}ms"

    return (
        '<div class="tx-meta-row">'
        f'<span class="tx-meta-pill {provider_cls}">{provider_icon} {html.escape(provider_used)}</span>'
        f'<span class="tx-meta-pill latency">⏱ {latency_str}</span>'
        '</div>'
    )


def render_activities(activities: list, llm_meta: dict):
    """Activities list với card + meta badges."""
    meta_html = _provider_meta_html(llm_meta)

    if not activities:
        st.markdown(
            meta_html +
            '<div class="tx-empty"><div class="tx-empty-icon">🔍</div>'
            '<div>Không tìm thấy hoạt động phù hợp</div></div>',
            unsafe_allow_html=True,
        )
        return

    cards_html = ""
    for act in activities:
        a_meta   = act.get("metadata", {})
        a_name   = a_meta.get("name", "Hoạt động")
        a_score  = act.get("score", 0)
        a_reason = act.get("reason", "")
        a_type   = a_meta.get("activity_type", "")
        a_dur    = a_meta.get("estimated_duration")
        a_price  = a_meta.get("price_level")

        # Micro-meta dưới tên
        meta_parts = []
        if a_type:
            meta_parts.append(f'<span class="tx-act-type">● {html.escape(a_type)}</span>')
        if a_dur:
            meta_parts.append(f'<span class="tx-act-type">⏱ {int(a_dur)}m</span>')
        if a_price:
            dollars = "$" * max(1, min(5, int(round(float(a_price)))))
            meta_parts.append(f'<span class="tx-act-type">{dollars}</span>')
        meta_line = " ".join(meta_parts)

        cards_html += f"""
        <div class="tx-act-card">
            <div class="tx-act-head">
                <div class="tx-act-name">{html.escape(a_name)}</div>
                <div class="tx-act-score">{a_score:.2f}</div>
            </div>
            {meta_line}
            <div class="tx-act-reason">{html.escape(a_reason)}</div>
        </div>
        """

    st.markdown(
        meta_html + f'<div class="tx-act-list">{cards_html}</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_brand():
    """Logo + tên app ở top sidebar."""
    st.markdown(
        """
        <div class="tx-sidebar-brand">
            <div class="tx-logo">🧭</div>
            <h3>Travel Planner</h3>
            <p>AI Recommender</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
