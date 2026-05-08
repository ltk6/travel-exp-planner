import streamlit as st


def inject_custom_css():
    st.markdown(
        """
        <style>
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
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"] { display: none !important; }

        [data-testid="stAppViewBlockContainer"] {
            padding-left: 5rem !important;
            padding-right: 5rem !important;
            max-width: 1200px !important;
        }

        /* ── Sticky Header ── */
        div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-anchor) {
            position: sticky;
            top: 0;
            z-index: 1000;
            background-color: var(--bg-primary);
            padding: 1rem 0;
            margin-top: -1rem;
            border-bottom: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        .header-title {
            margin: 0 0 10px 0 !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            text-align: center;
        }

        /* ── Card containers (st.container with border=True) ── */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: var(--radius-lg);
            background-color: var(--bg-secondary);
            box-shadow: var(--shadow-md);
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid var(--border);
        }

        div[data-testid="column"] > div,
        div[data-testid="column"] > div > div,
        div[data-testid="column"] > div > div > div,
        div[data-testid="column"] > div > div > div > div,
        div.element-container {
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            display: block !important;
        }
        div[data-testid="column"] div.element-container,
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] {
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            display: block !important;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label,
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label > div {
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label > div[role="checkbox"],
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label > span:first-child,
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] > label > div:first-child:not([data-testid="stMarkdownContainer"]),
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] div[data-testid="stCheckboxUI"],
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] input[type="checkbox"] {
            display: none !important;
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] label {
            width: 100% !important;
            min-height: 56px !important;
            margin: 0 !important;
            background-color: var(--bg-tertiary);
            border: 2px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 10px 16px;
            box-sizing: border-box;
            cursor: pointer;
            transition: border-color 0.15s ease, background-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
            display: flex !important;
            align-items: center !important;
            gap: 10px !important;
            box-shadow: var(--shadow-sm);
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] label:hover {
            border-color: var(--border-hover);
            background-color: var(--border);
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"]:has(input:checked) label {
            background-color: #1f1015;
            border-color: var(--accent);
            box-shadow: 0 4px 16px var(--accent-glow);
            transform: translateY(-1px);
        }
        div[data-testid="stHorizontalBlock"] div[data-testid="stCheckbox"] label p {
            margin: 0;
            font-weight: 600;
            color: var(--text-primary);
            font-size: 0.9rem;
            line-height: 1.3;
        }

        /* ── Primary button (submit) ── */
        div.stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            border-radius: var(--radius-md) !important;
            background-color: var(--accent) !important;
            background-image: none !important;
            border: none !important;
            color: white !important;
            font-weight: 700 !important;
            font-family: 'Be Vietnam Pro', sans-serif !important;
            height: 64px !important;
            font-size: 1.2rem !important;
            letter-spacing: 0.5px !important;
            box-shadow: var(--shadow-accent) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 28px rgba(255, 107, 107, 0.5) !important;
        }

        /* ── Popover (optional sections) ── */
        div[data-testid="stPopover"] > button {
            background-color: var(--bg-tertiary) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--text-primary) !important;
            transition: border-color 0.15s ease, background-color 0.15s ease !important;
        }
        div[data-testid="stPopover"] > button:hover {
            border-color: var(--border-hover) !important;
            background-color: var(--border) !important;
        }

        /* ── Spinner ── */
        div[data-testid="stSpinner"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            padding: 2rem 0 !important;
        }
        div[data-testid="stSpinner"] > div {
            color: var(--accent) !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
        }

        /* ── Tag / badge component ── */
        .tag-badge {
            display: inline-block;
            background-color: #1f1015;
            border: 1px solid var(--accent);
            color: var(--accent);
            border-radius: 20px;
            padding: 3px 10px;
            font-size: 0.78rem;
            font-weight: 600;
            margin: 2px;
        }

        /* ── Progress bar ── */
        .progress-container {
            display: flex;
            gap: 6px;
            margin: 8px 0 16px;
            align-items: center;
        }
        .progress-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: var(--border);
            transition: background-color 0.3s ease;
        }
        .progress-dot.done { background-color: var(--accent); }

        /* ── Activity card ── */
        .activity-card {
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 12px 16px;
            margin-bottom: 8px;
            transition: border-color 0.15s ease;
        }
        .activity-card:hover { border-color: var(--border-hover); }
        </style>
        """,
        unsafe_allow_html=True,
    )