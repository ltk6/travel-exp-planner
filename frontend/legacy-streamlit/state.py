import streamlit as st

def init_session_state():
    """Initializes default values for the session state."""
    st.session_state.setdefault("results", None)
    st.session_state.setdefault("mode", "📋 Trắc nghiệm")
    st.session_state.setdefault("payload", None)
    st.session_state.setdefault("_scroll_pending", False)
