"""
styles/base.py
General styles, variables, and base layout.
Restored to the original alt_n7_ui reddish theme.
"""

def get_base_css():
    return """
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

    /* ── CSS Variables ── */
    :root {
        --bg-primary:     #0d1117;
        --bg-secondary:   #161b22;
        --bg-tertiary:    #21262d;
        --border:         #30363d;
        --border-hover:   #8b949e;
        --text-primary:   #e6edf3;
        --text-muted:     #8b949e;
        --accent:         #ff6b6b;
        --accent-dark:    #cc3333;
        --accent-glow:    rgba(255, 107, 107, 0.25);
        --radius-sm:      8px;
        --radius-md:      12px;
        --radius-lg:      16px;
        --shadow-sm:      0 2px 8px rgba(0, 0, 0, 0.3);
        --shadow-md:      0 4px 16px rgba(0, 0, 0, 0.5);
        --shadow-accent:  0 4px 20px rgba(255, 107, 107, 0.3);
    }

    /* ── Base ── */
    .stApp {
        background-color: var(--bg-primary);
        font-family: 'Be Vietnam Pro', sans-serif;
    }
    h1, h2, h3, h4, p, label { color: var(--text-primary) !important; }
    h3 {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        margin-bottom: 5px !important;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--border);
    }

    /* ── Layout ── */
    [data-testid="stSidebar"] {
        background-color: var(--bg-secondary) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebarNav"] { display: none !important; }

    [data-testid="stAppViewBlockContainer"] {
        padding-left: 5rem !important;
        padding-right: 5rem !important;
        max-width: 1200px !important;
    }

    /* ── Sticky Nav Bar ── */
    div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-anchor) {
        position: sticky;
        top: -1px;
        z-index: 1000;
        background-color: var(--bg-primary);
        padding: 1rem 0;
        margin-top: 0;
        border-bottom: 1px solid var(--border);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        overflow: visible !important;
    }
    .header-title {
        margin: 0 0 10px 0 !important;
        font-size: 2rem !important;
        font-weight: 800 !important;
        text-align: center;
        color: var(--accent);
    }
    """
