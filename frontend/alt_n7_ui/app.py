"""
app.py — Travel Experience Planner
Entry point for the Streamlit application.

Routing logic:
  - Any mode except "📊 Kết quả" → render input view
  - "📊 Kết quả" + pending payload → call backend, then rerun
  - "📊 Kết quả" + cached results → render result view
  - "📊 Kết quả" + nothing → show fallback with nav back
"""
import streamlit as st
import requests
import logging

# ── Logging Configuration ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alt_n7.app")

from styles import inject_custom_css
from views.header import render_sticky_header
from views.input import render_input_view
from views.result import render_result_view

# ── Page config ──
st.set_page_config(
    page_title="Travel Experience Planner",
    page_icon="🗺️",
    layout="wide",
)
inject_custom_css()
render_sticky_header(title="🗺️ Travel Experience Planner")

# ── Session state defaults ──
st.session_state.setdefault("results", None)
st.session_state.setdefault("mode", "📋 Trắc nghiệm")
st.session_state.setdefault("payload", None)
st.session_state.setdefault("_scroll_pending", False)


def _inject_scroll_to_top() -> None:
    """Injects JavaScript to scroll once, guarded by session flag."""
    if not st.session_state.get("_scroll_pending"):
        return
    st.session_state["_scroll_pending"] = False
    st.components.v1.html(
        """<script>
            var body = window.parent.document.querySelector(".main");
            if (body) body.scrollTo({ top: 0, behavior: 'auto' });
        </script>""",
        height=0,
        width=0,
    )


# ── Routing ──
if st.session_state.mode != "📊 Kết quả":
    logger.info(f"Rendering input view (mode: {st.session_state.mode})")
    _inject_scroll_to_top()
    payload = render_input_view()
    if payload:
        logger.info("Payload received from input view, switching to results mode")
        st.session_state.payload = payload
        st.session_state.mode = "📊 Kết quả"
        st.session_state["_scroll_pending"] = True
        st.rerun()

else:
    # Phase 1: pending payload → call backend
    if st.session_state.payload:
        logger.info("Sending request to backend API (localhost:5000)")
        _inject_scroll_to_top()
        with st.spinner("⏳ Đang phân tích hồ sơ du lịch của bạn…"):
            try:
                res = requests.post(
                    "http://localhost:5000/recommend",
                    json=st.session_state.payload,
                    timeout=60,
                )
                if res.status_code == 200:
                    logger.info("Backend call successful (200 OK)")
                    st.session_state.results = res.json()
                    st.session_state.activity_results = {}
                    st.session_state.payload = None
                    st.session_state["_scroll_pending"] = True
                    st.rerun()
                else:
                    logger.error(f"Backend API error: {res.status_code} - {res.text}")
                    st.error(f"Lỗi từ máy chủ: {res.status_code} — {res.text}")
                    st.session_state.payload = None
            except requests.exceptions.ConnectionError:
                logger.error("Connection error: backend unreachable")
                st.error("❌ Không thể kết nối đến backend (localhost:5000). Hãy kiểm tra máy chủ.")
                st.session_state.payload = None
            except requests.exceptions.Timeout:
                logger.error("Timeout error during backend call")
                st.error("⏱️ Yêu cầu quá thời gian chờ. Hãy thử lại.")
                st.session_state.payload = None

    # Phase 2: results ready → show result view
    elif st.session_state.results:
        logger.info(f"Rendering result view with {len(st.session_state.results.get('locations', []))} locations")
        _inject_scroll_to_top()
        render_result_view(st.session_state.results)

    # Phase 3: arrived here with no data
    else:
        _, c_mid, _ = st.columns([1, 3, 1])
        with c_mid:
            st.info("Chưa có kết quả. Vui lòng dùng Trắc nghiệm, Văn bản hoặc Hình ảnh.")
            if st.button("← Quay trở về", type="primary", use_container_width=True):
                st.session_state.mode = "📋 Trắc nghiệm"
                st.session_state["_scroll_pending"] = True
                st.rerun()