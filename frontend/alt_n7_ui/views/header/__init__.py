import streamlit as st

MODES = [
    "📋 Trắc nghiệm",
    "✍️ Văn bản tự do",
    "📸 Hình ảnh",
    "📊 Kết quả",
]

def render_sticky_header(title: str = "🧭 Travel Planner") -> None:
    """Sticky top nav with mode switcher buttons."""
    if "mode" not in st.session_state:
        st.session_state.mode = MODES[0]
        
    active = st.session_state.mode
    
    with st.container():
        st.markdown('<div class="sticky-header-anchor"></div>', unsafe_allow_html=True)
        st.markdown(f'<h1 class="header-title">{title}</h1>', unsafe_allow_html=True)
        
        cols = st.columns(6)
        
        mode_column_mapping = {
            MODES[0]: cols[0],
            MODES[1]: cols[1],
            MODES[2]: cols[2],
            MODES[3]: cols[5]
        }
        
        for mode, col in mode_column_mapping.items():
            with col:
                is_active = active == mode
                label = f"[ {mode} ]" if is_active else mode
                if st.button(label, use_container_width=True, type="secondary", key=f"nav_{mode}"):
                    if not is_active:
                        st.session_state.mode = mode
                        st.rerun()
