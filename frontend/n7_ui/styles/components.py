"""
styles/components.py
Reusable component styles: buttons, cards, checkboxes, badges.
Restored to the original alt_n7_ui reddish theme.
"""

def get_components_css():
    return """
    /* ── Card containers (st.container with border=True) ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius-lg);
        background-color: var(--bg-secondary);
        box-shadow: var(--shadow-md);
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid var(--border);
    }

    /* ── Questionnaire Checkbox-as-Button ── */
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

    /* ── Popover and Expander Size Limit ── */
    div[data-testid="stPopoverBody"],
    div[data-testid="stExpanderDetails"] {
        max-height: 240px;
        overflow-y: auto;
    }

    /* ── Spinner ── */
    div[data-testid="stSpinner"] > div {
        color: var(--accent) !important;
        font-weight: 600 !important;
    }
    """
