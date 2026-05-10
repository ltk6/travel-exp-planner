"""
app.py — Travel Experience Planner
Entry point for the Streamlit application.
"""
import streamlit as st
import requests
import logging
import os

from styles import inject_custom_css
from views.header import render_sticky_header
from views.input import render_input_view
from views.result import render_result_view
from state import init_session_state
from utils import inject_scroll_to_top

# ── Logging Configuration ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alt_n7.app")

_INTERNAL_KEY = os.environ.get("INTERNAL_API_KEY", "")
_BACKEND_HEADERS = {"X-Internal-Key": _INTERNAL_KEY}
_BACKEND_URL = "http://localhost:5000/recommend"

# ── Page config ──
st.set_page_config(
    page_title="Travel Experience Planner",
    page_icon="🗺️",
    layout="wide",
)
inject_custom_css()
render_sticky_header(title="🗺️ Travel Experience Planner")

# ── Init ──
init_session_state()

# ── Routing ──
if st.session_state.mode != "📊 Kết quả":
    logger.info(f"Rendering input view (mode: {st.session_state.mode})")
    inject_scroll_to_top()
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
        logger.info(f"Sending request to backend API ({_BACKEND_URL})")
        inject_scroll_to_top()
        with st.spinner("⏳ Đang phân tích hồ sơ du lịch của bạn…"):
            try:
                res = requests.post(
                    _BACKEND_URL,
                    json=st.session_state.payload,
                    headers=_BACKEND_HEADERS,
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
            except Exception as e:
                logger.error(f"Backend call failed: {e}")
                st.error(f"❌ Không thể kết nối đến backend. Hãy kiểm tra máy chủ. ({e})")
                st.session_state.payload = None

    # Phase 2: results ready → show result view
    elif st.session_state.results:
        logger.info(f"Rendering result view with {len(st.session_state.results.get('locations', []))} locations")
        inject_scroll_to_top()
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