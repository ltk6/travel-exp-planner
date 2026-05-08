import streamlit as st

def render_result_view(response_data: dict):
    """
    Module giao diện chịu trách nhiệm 100% cho trang Kết Quả.
    """
    st.markdown("---")
    st.title("🗺️ Kết quả phân tích của bạn")
    
    locations = response_data.get("locations", [])
    trace = response_data.get("trace", {})

    # =========================================================
    # INJECT CSS ĐỂ CỐ ĐỊNH KÍCH THƯỚC NÚT & CĂN GIỮA NỘI DUNG
    # =========================================================
    st.markdown("""
    <style>
        /* Thiết kế ô hộp (box) cố định chiều cao đủ cho tối đa 50 ký tự (khoảng 2-3 dòng) */
        div[data-testid="stButton"] > button {
            height: 65px !important;
            width: 100% !important;
            display: inline-flex !important;
            align-items: center !important; /* Căn giữa theo chiều dọc */
            justify-content: center !important; /* Căn giữa theo chiều ngang */
            padding: 5px !important;
            border-radius: 8px !important;
        }
        /* Chữ bên trong được phép rớt dòng và căn giữa */
        div[data-testid="stButton"] > button p {
            white-space: normal !important; 
            word-wrap: break-word !important;
            text-align: center !important; 
            font-size: 14px !important;
            line-height: 1.3 !important;
            margin: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if not locations:
        st.warning("Không tìm thấy địa điểm nào phù hợp. Vui lòng thử lại!")
        return

    with st.expander("🤖 Trí tuệ nhân tạo đã phân tích như thế nào?"):
        user_trace = trace.get("user", {})
        img_desc = user_trace.get("image_processing", {}).get("image_description", "")
        if img_desc:
            st.info(f"**AI nhìn thấy từ ảnh của bạn:** {img_desc}")
        st.json(trace) 

    st.markdown("---")
    
    # =========================================================
    # KHỞI TẠO BIẾN TRẠNG THÁI CHO CHUYỂN TRANG
    # =========================================================
    if "slide_idx" not in st.session_state:
        st.session_state.slide_idx = 0
        
    if st.session_state.slide_idx >= len(locations):
        st.session_state.slide_idx = 0

    # =========================================================
    # KHỐI GIAO DIỆN NGUYÊN KHỐI (MASTER CONTAINER)
    # Bọc tất cả Tabs, Nội dung và Nút bấm vào chung 1 khối duy nhất
    # tự động co giãn theo thiết bị người dùng.
    # =========================================================
    with st.container(border=True):
        
        # ---------------------------------------------------------
        # TẦNG 1: THANH MENU TABS NẰM NGANG Ở TRÊN CÙNG
        # ---------------------------------------------------------
        tab_cols = st.columns(len(locations))
        for i, loc in enumerate(locations):
            full_name = loc.get("metadata", {}).get("name", f"Địa điểm {i+1}")
            short_name = full_name.split(',')[0][:20] 
            
            with tab_cols[i]:
                is_active = (i == st.session_state.slide_idx)
                btn_type = "primary" if is_active else "secondary"
                
                if st.button(short_name, key=f"top_tab_{i}", use_container_width=True, type=btn_type):
                    st.session_state.slide_idx = i
                    st.rerun()

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # TẦNG 2: RENDER NỘI DUNG CHI TIẾT CỦA 1 ĐỊA ĐIỂM
        # ---------------------------------------------------------
        idx = st.session_state.slide_idx
        loc = locations[idx]
        metadata = loc.get("metadata", {})
        score = loc.get("score", 0)
        loc_activities = loc.get("activities", [])
        
        # Phần Header của Nội dung
        header_col1, header_col2 = st.columns([8, 2])
        
        with header_col1:
            st.markdown(f"### {metadata.get('name', 'Địa điểm chưa biết')}")
            tags = metadata.get("tags", [])
            if tags:
                st.markdown(" ".join([f"`#{tag}`" for tag in tags]))
        
        with header_col2:
            score_percent = int(score * 100)
            color = "#4CAF50" if score_percent >= 80 else ("#FF9800" if score_percent >= 60 else "#F44336")
            
            circle_html = f"""
            <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                <div style="width: 70px; height: 70px; border-radius: 50%; background: conic-gradient({color} {score_percent}%, #f0f2f6 0); display: flex; justify-content: center; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="width: 56px; height: 56px; border-radius: 50%; background: white; display: flex; justify-content: center; align-items: center;">
                        <span style="font-size: 16px; font-weight: bold; color: {color};">{score_percent}%</span>
                    </div>
                </div>
            </div>
            """
            st.markdown(circle_html, unsafe_allow_html=True)
        
        st.write("")
        
        # Phần Detail 60/40
        left_col, right_col = st.columns([6, 4])
        
        with left_col:
            image_url = loc.get("image_url") or loc.get("image_path")
            if image_url:
                # Dùng HTML/CSS để cố định khung ảnh (chiếm ~60%) và tự động crop/khớp ảnh (object-fit: cover)
                # Tích hợp Nút mờ (Icon) ở góc phải trên cùng để mở Modal xem ảnh toàn màn hình bằng CSS thuần.
                img_html = f"""
                <style>
                .modal-check-{idx} {{ display: none; }}
                .lightbox-{idx} {{
                    display: none;
                    position: fixed;
                    z-index: 999999;
                    top: 0; left: 0;
                    width: 100vw; height: 100vh;
                    background: rgba(0,0,0,0.85);
                    align-items: center; justify-content: center;
                }}
                .modal-check-{idx}:checked ~ .lightbox-{idx} {{ display: flex; }}
                .lightbox-{idx} img {{
                    max-width: 90vw; max-height: 90vh;
                    border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                }}
                .close-btn-{idx} {{
                    position: absolute; top: 20px; right: 30px;
                    color: white; font-size: 40px; cursor: pointer;
                    font-weight: bold; user-select: none;
                }}
                </style>
                
                <div style="position: relative; width: 100%; height: 380px; border-radius: 8px; overflow: hidden; margin-bottom: 10px; border: 1px solid rgba(49, 51, 63, 0.2);">
                    <img src="{image_url}" style="width: 100%; height: 100%; object-fit: cover;" alt="Location Image">
                    <!-- Nút bấm mờ góc phải trên -->
                    <label for="img_popup_{idx}" style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.4); color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 16px; border: 1px solid rgba(255,255,255,0.3);">
                        ⛶
                    </label>
                </div>

                <!-- Checkbox ẩn điều khiển trạng thái mở ảnh -->
                <input type="checkbox" id="img_popup_{idx}" class="modal-check-{idx}">
                <!-- Modal phóng to ảnh -->
                <div class="lightbox-{idx}">
                    <label for="img_popup_{idx}" class="close-btn-{idx}">×</label>
                    <img src="{image_url}">
                </div>
                """
                st.markdown(img_html, unsafe_allow_html=True)
            
            # Cố định khung chứa text (Mô tả & Lý do) với thanh cuộn dọc (scroll) - chiếm ~40%
            with st.container(height=222, border=True):
                st.write(metadata.get("description", "Không có mô tả chi tiết."))
                if loc.get("reason"):
                    st.info(f"💡 **Lý do đề xuất:** {loc.get('reason')}")
                
        with right_col:
            st.markdown("#### 🎯 Các hoạt động nên thử")
            # Cố định khung chứa danh sách hoạt động. 
            # Đặt chiều cao 600px để phần đáy cột phải phẳng hàng với phần đáy ô mô tả bên cột trái.
            with st.container(height=530, border=True):
                if loc_activities:
                    for act in loc_activities:
                        act_score = int(act.get('score', 0) * 100)
                        act_color = "#4CAF50" if act_score >= 80 else ("#FF9800" if act_score >= 60 else "#F44336")
                        
                        act_html = f"""
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0;">
                            <span style="font-weight: 600; font-size: 15px; padding-right: 10px;">{act.get('activity_id', 'Hoạt động')}</span>
                            <div style="width: 44px; height: 44px; border-radius: 50%; background: conic-gradient({act_color} {act_score}%, #f0f2f6 0); display: flex; justify-content: center; align-items: center; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="width: 32px; height: 32px; border-radius: 50%; background: white; display: flex; justify-content: center; align-items: center;">
                                    <span style="font-size: 12px; font-weight: bold; color: {act_color};">{act_score}%</span>
                                </div>
                            </div>
                        </div>
                        """
                        with st.container(border=True):
                            st.markdown(act_html, unsafe_allow_html=True)
                else:
                    st.caption("Chưa có gợi ý hoạt động nào.")

        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # TẦNG 3: NÚT NEXT / PREV ĐIỀU HƯỚNG BÊN DƯỚI
        # ---------------------------------------------------------
        nav_col1, nav_col2, nav_col3 = st.columns([2, 6, 2])
        
        with nav_col1:
            if st.button("⬅️ Điểm đến trước", use_container_width=True, disabled=st.session_state.slide_idx == 0):
                st.session_state.slide_idx -= 1
                st.rerun()
                
        with nav_col2:
            dots = ["⚫" if i == st.session_state.slide_idx else "⚪" for i in range(len(locations))]
            st.markdown(f"<div style='text-align: center; letter-spacing: 5px; line-height: 2.5;'>{''.join(dots)}</div>", unsafe_allow_html=True)
            
        with nav_col3:
            if st.button("Điểm đến tiếp theo ➡️", use_container_width=True, disabled=st.session_state.slide_idx == len(locations) - 1):
                st.session_state.slide_idx += 1
                st.rerun()


# ==========================================
# KHU VỰC CHẠY TEST ĐỘC LẬP (MOCK DATA)
# ==========================================
if __name__ == "__main__":
    st.set_page_config(page_title="Thiết kế Trang Kết Quả", layout="centered")
    
    mock_payload = {
        "locations": [
            {
                "location_id": "loc_sapa",
                "score": 0.95,
                "reason": "Hoàn toàn khớp với nhu cầu thích núi rừng và không khí lạnh của bạn.",
                "metadata": {
                    "name": "Fansipan, Sapa",
                    "description": "Nóc nhà Đông Dương với hệ thống cáp treo hiện đại. Phù hợp cho những ai yêu thích săn mây, thiên nhiên hùng vĩ và không khí se lạnh quanh năm.",
                    "tags": ["mountain", "cold", "trekking", "nature"]
                },
                "geo": {"lat": 22.3031, "lng": 103.7744},
                "image_url": "https://images.unsplash.com/photo-1549488344-1f9b8d2bd1f3?w=800&q=80",
                "activities": [
                    {"activity_id": "Săn mây lúc bình minh", "score": 0.98},
                    {"activity_id": "Trekking xuyên đồi", "score": 0.92},
                    {"activity_id": "Tắm lá người Dao", "score": 0.85}
                ]
            },
            {
                "location_id": "loc_danang",
                "score": 0.88,
                "reason": "Gợi ý thay thế tuyệt vời nếu bạn muốn vừa ngắm núi (Bà Nà) vừa có biển.",
                "metadata": {
                    "name": "Bà Nà Hills, Đà Nẵng",
                    "description": "Khu nghỉ dưỡng mang kiến trúc làng Pháp cổ kính nằm trên đỉnh núi cao. Trải nghiệm 4 mùa trong 1 ngày đặc sắc.",
                    "tags": ["resort", "cable-car", "city", "sea"]
                },
                "geo": {"lat": 16.0678, "lng": 108.2208},
                "image_url": "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?w=800&q=80",
                "activities": [
                    {"activity_id": "Đi cáp treo ngắm sương", "score": 0.95},
                    {"activity_id": "Chụp ảnh Cầu Vàng", "score": 0.88}
                ]
            },
            {
                "location_id": "loc_ninhbinh",
                "score": 0.76,
                "reason": "Ninh Bình có non nước hữu tình, rất hợp để chụp ảnh và thư giãn.",
                "metadata": {
                    "name": "Tràng An, Ninh Bình",
                    "description": "Được ví như Vịnh Hạ Long trên cạn, bạn sẽ ngồi đò lướt qua những thung lũng nước trong vắt và các hang động xuyên núi kì bí.",
                    "tags": ["culture", "boat", "cave", "heritage"]
                },
                "geo": {"lat": 20.2539, "lng": 105.9749},
                "image_url": "https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=800&q=80",
                "activities": [
                    {"activity_id": "Đi đò xuyên hang", "score": 0.90},
                    {"activity_id": "Đạp xe quanh đồng lúa", "score": 0.85}
                ]
            },
            {
                "location_id": "loc_dalat",
                "score": 0.65,
                "reason": "Sự lãng mạn nhẹ nhàng thay vì leo núi dốc.",
                "metadata": {
                    "name": "Thành phố Đà Lạt",
                    "description": "Thành phố ngàn hoa rực rỡ với rừng thông bạt ngàn. Các quán cafe chill, homestay gỗ và dốc sương mù làm say đắm bất cứ ai.",
                    "tags": ["chill", "romantic", "forest", "coffee"]
                },
                "geo": {"lat": 11.9404, "lng": 108.4383},
                "image_url": "https://images.unsplash.com/photo-1626081079313-0975e1823eb5?w=800&q=80",
                "activities": [
                    {"activity_id": "Uống cafe trên mây", "score": 0.93}
                ]
            },
            {
                "location_id": "loc_hagiang",
                "score": 0.54,
                "reason": "Độ khó di chuyển cao nhưng đền đáp bằng cảnh đẹp hoang sơ vĩ đại.",
                "metadata": {
                    "name": "Mã Pí Lèng, Hà Giang",
                    "description": "Cung đèo hiểm trở đâm xuyên qua cao nguyên đá vôi, ngắm dòng sông Nho Quế màu ngọc bích rực rỡ bên dưới vực sâu.",
                    "tags": ["adventure", "motorbike", "remote", "highland"]
                },
                "geo": {"lat": 23.2300, "lng": 105.2500},
                "image_url": "https://images.unsplash.com/photo-1550184658-ff6132a71714?w=800&q=80",
                "activities": [
                    {"activity_id": "Lái xe máy dạo đèo", "score": 0.99},
                    {"activity_id": "Đi thuyền sông Nho Quế", "score": 0.89}
                ]
            }
        ],
        "trace": {
            "user": {
                "input": {"text": "Tôi muốn đi ngắm mây và rừng thông", "tags": ["mountain", "chill"]},
                "image_processing": {
                    "image_description": "Một bức ảnh đồi núi sương mù với rừng thông và bình minh xa xăm."
                }
            },
            "debug": {
                "status": "Mock API Data loaded successfully."
            }
        }
    }
    
    render_result_view(mock_payload)
