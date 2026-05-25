"""
styles/result.py
Styles specific to the results view, carousel, and activity cards.
"""

def get_result_css():
    return """
    /* ── Wide Image Crop ── */
    .wide-image-container img {
        height: 180px !important;
        object-fit: cover !important;
        width: 100% !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
.wide-image-container img:hover {
        transform: scale(1.02);
    }

    /* ── Compact Metadata ── */
    .compact-reason {
        font-size: 0.85rem;
        color: var(--text-secondary);
        border-left: 3px solid var(--accent);
        background-color: var(--bg-tertiary);
        padding: 8px 12px;
        margin: 8px 0;
        border-radius: 0 6px 6px 0;
        line-height: 1.4;
    }

    /* ── Progress bar / Dots ── */
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
    """
