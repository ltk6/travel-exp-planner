import streamlit as st

def inject_scroll_to_top() -> None:
    """Injects JavaScript to scroll once, guarded by session flag."""
    if not st.session_state.get("_scroll_pending"):
        return
    st.session_state["_scroll_pending"] = False
    st.iframe(
        "data:text/html;charset=utf-8," + 
        """<script>
            var body = window.parent.document.querySelector(".main");
            if (body) body.scrollTo({ top: 0, behavior: 'auto' });
        </script>""",
        height=1,
        width=1,
    )
