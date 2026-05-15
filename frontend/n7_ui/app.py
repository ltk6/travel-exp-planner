"""
app.py — Travel Experience Planner
Entry point for the Streamlit application.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import requests
import logging
import os
import time

from styles import inject_custom_css
from views.header import render_header
from views.input import render_input_view
from views.result import render_result_view
from state import init_session_state

from config import setup_logging, INTERNAL_API_KEY, API_PORT
logger = setup_logging("N7")

_BACKEND_HEADERS = {"X-Internal-Key": INTERNAL_API_KEY}
_BACKEND_URL = f"http://localhost:{API_PORT}/recommend"

# ── Page config ──
st.set_page_config(
    page_title="Travel Experience Planner",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_custom_css()
render_header(title="🗺️ Travel Experience Planner")

# ── Init ──
init_session_state()

# ── Routing ──
if st.session_state.mode != "📊 Kết quả":
    logger.info(f"Rendering input view (mode: {st.session_state.mode})")
    payload = render_input_view()
    if payload:
        logger.info("Payload received from input view, switching to results mode")
        st.session_state.payload = payload
        st.session_state.mode = "📊 Kết quả"
        st.rerun()

else:
    # Phase 1: pending payload → call backend
    if st.session_state.payload:
        logger.info(f"Sending request to backend API ({_BACKEND_URL})")
        with st.spinner("⏳ Đang phân tích hồ sơ du lịch của bạn…"):
            try:
                # Inject configuration overrides
                payload = dict(st.session_state.payload)
                # (Removed N7-controlled Top K overrides)

                start_t = time.time()
                res = requests.post(
                    _BACKEND_URL,
                    json=payload,
                    headers=_BACKEND_HEADERS,
                    timeout=60,
                )
                duration = time.time() - start_t
                logger.info(f"POST {_BACKEND_URL} took {duration:.4f}s")
                if res.status_code == 200:
                    logger.info("Backend call successful (200 OK)")
                    st.session_state.results = res.json()
                    st.session_state.activity_results = {}
                    st.session_state.payload = None
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
        render_result_view(st.session_state.results)

    # Phase 3: arrived here with no data
    else:
        _, c_mid, _ = st.columns([1, 3, 1])
        with c_mid:
            st.info("Chưa có kết quả. Vui lòng dùng Trắc nghiệm, Văn bản hoặc Hình ảnh.")
            if st.button("← Quay trở về", type="primary", use_container_width=True):
                st.session_state.mode = "📋 Trắc nghiệm"
                st.rerun()