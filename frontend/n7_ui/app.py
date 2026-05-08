"""
N7 — Travel Questionnaire UI (Streamlit) - FINAL VERSION (EMOJI CARDS + BOTTOM PROGRESS BAR)
"""

import streamlit as st
import requests
from PIL import Image
import base64
import time

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG 
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Travel Planner", page_icon="🧭", layout="wide")

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS STYLE - CLICKABLE CARDS & PROGRESS BAR
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Màu nền kem nhạt cực sang */
    .stApp {
        background-color: #fdfbf7;
        font-family: 'DM Sans', sans-serif;
    }
    
    /* Box chứa từng câu hỏi */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px;
        background-color: #ffffff;
        box-shadow: 0 4px 16px rgba(0,0,0,0.03);
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid #f0ece1;
    }
    
    /* Bo góc cho ảnh bìa (nếu dùng st.image) */
    [data-testid="stImage"] img {
        border-radius: 20px;
        margin-bottom: 10px;
    }
    
    /* -----------------------------------------------------------------
       MAGIC CSS: BIẾN CHECKBOX THÀNH CLICKABLE CARDS — EQUAL HEIGHT
       ----------------------------------------------------------------- */

    /* Ép hàng columns stretch các con theo chiều cao nhau */
    div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }

    /* Ép các cột Streamlit stretch theo chiều cao nhau và CHỐNG TRÀN CHIỀU NGANG */
    div[data-testid="column"] {
        display: flex !important;
        flex-direction: column !important;
        min-width: 0 !important; /* FIX: Ép cột giữ đúng tỷ lệ, không bị phình to do nội dung chữ dài */
    }

    /* FIX: Đảm bảo Container bao bọc Checkbox bắt buộc chiếm trọn 100% chiều ngang của cột */
    div[data-testid="stElementContainer"] {
        width: 100% !important;
    }

    /* stCheckbox container chiếm toàn bộ chiều cao và chiều ngang cột */
    div[data-testid="stCheckbox"] {
        width: 100% !important;
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* Ẩn hoàn toàn ô vuông Checkbox mặc định */
    div[data-testid="stCheckbox"] div[role="checkbox"], 
    div[data-testid="stCheckbox"] input[type="checkbox"] {
        display: none !important;
    }

    /* Label (thẻ) stretch full height — key fix cho equal height */
    div[data-testid="stCheckbox"] label {
        flex: 1 1 auto !important;
        background-color: #ffffff;
        border: 2px solid #edf2f7;
        border-radius: 16px;
        padding: 18px 12px;
        width: 100% !important;
        min-height: 145px;
        box-sizing: border-box;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.01);
    }
    
    /* Hiệu ứng khi lướt chuột qua */
    div[data-testid="stCheckbox"] label:hover {
        border-color: #cbd5e0;
        background-color: #f8fafc;
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.05);
    }
    
    /* Hiệu ứng khi thẻ ĐÃ ĐƯỢC CHỌN */
    div[data-testid="stCheckbox"]:has(input:checked) label {
        background-color: #ebf8f4;
        border-color: #48bb78; 
        box-shadow: 0 4px 16px rgba(72, 187, 120, 0.15);
        transform: translateY(-1px);
    }
    
    /* Định dạng chữ và Icon bên trong Thẻ */
    div[data-testid="stCheckbox"] label p {
        margin: 0;
        font-weight: 600;
        color: #2d3748;
        text-align: center;
        line-height: 1.4;
        font-size: 0.95rem;
        white-space: pre-wrap; 
        overflow-wrap: break-word; /* FIX: Chữ dài tự rớt dòng, không ép giãn ngang thẻ */
        width: 100%;
    }
    
    /* Phóng to Icon (Dòng đầu tiên) lên cực to */
    div[data-testid="stCheckbox"] label p::first-line {
        font-size: 2.8rem;
        line-height: 1.8;
    }
    
    /* Nút Submit lộng lẫy */
    button[kind="primary"] {
        border-radius: 12px;
        background: linear-gradient(135deg, #ff7b9c 0%, #ff6b6b 100%);
        border: none;
        color: white;
        padding: 14px 0;
        font-size: 1.2rem;
        margin-top: 15px;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
        transition: all 0.3s ease;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.6);
    }
    /* FIX: Ép in đậm chữ bên trong nút Submit */
    button[kind="primary"] * {
        font-weight: 800 !important; 
    }
    
    /* -----------------------------------------------------------------
       TÙY CHỈNH THANH TIẾN ĐỘ (PROGRESS BAR) CHUẨN 1 THANH
       ----------------------------------------------------------------- */
    /* Vỏ ngoài (Track) màu trắng, viền đen */
    div[data-testid="stProgressBar"] {
        background-color: #ffffff !important;
        border: 2px solid #000000 !important;
        border-radius: 12px !important;
        height: 22px !important;
        overflow: hidden !important;
    }
    
    /* Ruột bên trong (Fill) lấp đầy màu xanh lá, đánh bay màu xanh mặc định */
    div[data-testid="stProgressBar"] > div {
        background-color: #4CAF50 !important;
        height: 100% !important;
        border-radius: 0 !important;
    }
    /* ----------------------------------------------------------------- */
    
    /* Tiêu đề */
    h1, h2, h3, h4, p, label { color: #1a1a2e !important; }
    h3 {
        font-size: 1.2rem !important;
        margin-bottom: 5px !important;
        font-weight: 800 !important;
        border-bottom: 2px solid #f0ece1;
        padding-bottom: 8px;
    }
    .question-title {
        font-weight: 600;
        font-size: 1.05rem;
        margin-top: 15px;
        margin-bottom: 5px;
    }
    .hint {
        font-size: 0.85rem;
        color: #888888 !important;
        font-style: italic;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DICTIONARIES (Giữ nguyên gốc 100% không đổi)
# ─────────────────────────────────────────────────────────────
SOCIAL_GROUP_TAGS = {
    "Just me": ["một mình", "solo"],
    "Me and my partner": ["cặp đôi", "vợ chồng", "romantic"],
    "Family with young kids": ["gia đình có trẻ em", "trẻ em", "family trip"],
    "Family, kids are older / no kids": ["gia đình", "family trip"],
    "A group of friends": ["nhóm bạn", "group"],
    "Me and a few close friends": ["bạn bè", "group"],
}
SEASON_TAGS = {
    "Hot / Summer": ["mùa hè", "nóng", "summer"],
    "Cool / Autumn": ["mùa thu", "mát mẻ", "autumn"],
    "Cold / Winter": ["mùa đông", "lạnh", "winter"],
    "Rainy season": ["mùa mưa", "rainy season"],
    "Dry season": ["mùa khô", "dry season"],
    "Not sure yet": [],
}
DURATION_TAGS = {
    "A day trip": ["cuối tuần"],
    "A weekend (2–3 days)": ["cuối tuần", "long weekend"],
    "A short week (4–5 days)": [],
    "A full week or more": [],
}
DISTANCE_TAGS = {
    "Stay close — under 2 hours": ["cuối tuần"],
    "Domestic — anywhere in Vietnam": [],
    "Open to international": [],
    "Distance doesn't matter": [],
}
EMOTION_DRIVER_TAGS = {
    "Exhausted — need real rest": ["mệt mỏi", "căng thẳng", "relaxation trip"],
    "Bored — want something new": ["chán", "bored", "adventure travel"],
    "Celebrating a milestone": ["kỷ niệm", "lãng mạn", "romantic getaway"],
    "Disconnected — want to feel alive": ["trống rỗng", "chán nản", "adventure travel"],
    "Just want fun": ["vui vẻ", "fun"],
    "Want to grow / discover": ["discovery", "cultural trip"],
}
EMOTION_OUTCOME_TAGS = {
    "Recharged and at peace": ["relaxation trip", "yên tĩnh", "peaceful"],
    "Excited — did something remarkable": ["adventure travel", "adrenaline"],
    "Connected — to people / culture": ["cultural trip", "local", "community"],
    "Romantic and close": ["romantic getaway", "lãng mạn", "intimate"],
    "Happy and light-hearted": ["fun", "vui vẻ", "lively"],
    "Inspired": ["cultural trip", "art", "discovery"],
}
LANDSCAPE_TAGS = {
    "Beach / coastline / sea": ["biển", "beach", "coastal"],
    "Mountains / highlands": ["núi", "mountain", "highland"],
    "Lush forest / jungle": ["rừng", "forest", "jungle"],
    "Rivers, lakes, waterfalls": ["hồ", "thác nước", "river"],
    "Open countryside / rice fields": ["làng quê", "đồng lúa", "countryside"],
    "I don't care about the landscape": [],
}
RAWNESS_TAGS = {
    "Completely wild and untouched": ["off the beaten path", "hidden gem", "adventure travel"],
    "Mostly natural, basic facilities": ["eco", "backpacking"],
    "Good mix of nature and comfort": ["glamping", "eco"],
    "Nature as backdrop — want comfort": ["resort", "luxury travel"],
}
CULTURE_DEPTH_TAGS = {
    "It's my main reason for traveling": ["cultural trip", "văn hóa", "lịch sử", "heritage"],
    "Very interested": ["văn hóa", "cultural trip"],
    "Somewhat — a bit of culture is nice": ["văn hóa"],
    "Not really": [],
}
CULTURE_SPECIFIC_TAGS = {
    "Local markets and street food": ["chợ", "ẩm thực", "street food"],
    "Temples, pagodas, sacred sites": ["chùa", "tôn giáo", "spiritual"],
    "Heritage architecture and old towns": ["phố cổ", "kiến trúc", "heritage"],
    "Festivals or local celebrations": ["lễ hội", "festival"],
    "Art, galleries, performances": ["nghệ thuật", "âm nhạc", "art"],
    "Craft villages and artisans": ["làng nghề", "craft", "authentic"],
}
INTENSITY_TAGS = {
    "Very active — hiking, climbing, paddling": ["adventure travel", "trekking", "leo núi"],
    "Moderately active — walking, cycling": ["hiking", "đạp xe", "cycling"],
    "Low effort — strolling, sightseeing": ["sightseeing", "thăm quan"],
    "Minimal — rest and enjoy": ["relaxation trip", "spa"],
}
ACTIVITY_TAGS = {
    "Trekking / hiking": ["leo núi", "trekking", "hiking"],
    "Water activities (diving, snorkeling, surfing)": ["lặn biển", "diving", "snorkeling"],
    "Camping or glamping": ["cắm trại", "camping"],
    "Kayaking or boat trips": ["chèo kayak", "kayaking", "đi thuyền"],
    "Photography and scenic viewpoints": ["chụp ảnh", "check-in", "photography"],
    "Spa, massage, and wellness": ["spa", "yoga", "wellness"],
    "Cooking classes or food tours": ["nấu ăn", "ẩm thực", "cooking class"],
    "Stargazing or night experiences": ["ngắm sao", "stargazing", "cắm trại"],
    "None in particular": [],
}
VIBE_TAGS = {
    "Quiet and peaceful — no crowds": ["yên tĩnh", "secluded", "peaceful", "quiet"],
    "Lively and social — buzzing energy": ["vui vẻ", "lively", "vibrant", "nightlife"],
    "Mysterious and atmospheric": ["mysterious", "misty", "sương mù"],
    "Romantic and intimate": ["lãng mạn", "romantic", "cặp đôi"],
    "Adventurous and raw": ["adventure travel", "off the beaten path", "adrenaline"],
    "Comfortable and polished": ["luxury travel", "resort", "modern"],
}
PHOTO_TAGS = {
    "Very — it has to be visually stunning": ["check-in", "photogenic", "instagrammable"],
    "Somewhat — nice photos are a bonus": ["check-in"],
    "Not at all — how it feels matters more": [],
}
ACCOMMODATION_TAGS = {
    "Luxury resort or hotel": ["resort", "luxury travel", "hotel"],
    "Private villa or guesthouse": ["villa", "luxury travel"],
    "Local homestay": ["homestay", "authentic", "local"],
    "Budget hostel or guesthouse": ["hostel", "budget travel"],
    "Tent camping or glamping": ["camping", "glamping"],
    "No strong preference": [],
}
ACCOMMODATION_PRIORITY_TAGS = {
    "Privacy and exclusivity": ["villa", "secluded"],
    "Proximity to nature": ["eco", "glamping"],
    "Cultural authenticity": ["homestay", "authentic"],
    "Facilities and amenities": ["resort", "hotel"],
    "Price / value for money": ["budget travel", "hostel"],
}
FOOD_TAGS = {
    "Food IS the trip": ["ẩm thực", "street food", "local cuisine", "seafood"],
    "Very important — great local food is a must": ["ẩm thực", "local cuisine"],
    "Moderate — good food but not focus": ["ẩm thực"],
    "Not important": [],
}
STYLE_TAGS = {
    "Planned and guided — clear itinerary": ["sightseeing", "cultural trip"],
    "Semi-structured — a few anchors, flexible": [],
    "Completely free — discover as I go": ["solo travel", "backpacking"],
    "Package / resort-stay — everything handled": ["luxury travel", "resort"],
}
CONSTRAINT_TAGS = {
    "Budget is tight": ["budget travel", "hostel", "backpacking"],
    "Accessibility matters (mobility needs)": ["accessible"],
    "Must be safe/easy for young children": ["gia đình có trẻ em", "family trip"],
    "Need reliable internet / remote work": ["city", "modern"],
    "None — I'm flexible": [],
}
TRIP_MOMENT_TAGS = {
    "Sunrise hike to a summit": ["trekking", "leo núi", "adventure travel"],
    "Lazy beach afternoon with a book": ["biển", "relaxation trip", "beach"],
    "Wandering a night market alone": ["street food", "ẩm thực", "solo travel"],
    "Kayaking through limestone caves": ["kayaking", "adventure travel", "hidden gem"],
    "A quiet dinner under the stars": ["lãng mạn", "romantic getaway", "peaceful"],
    "Getting lost in an old quarter": ["phố cổ", "heritage", "cultural trip"],
}

# ─────────────────────────────────────────────────────────────
# EMOJI / FLAT ICON MAP (Ảnh vẽ dạng Vector chuẩn 100%)
# ─────────────────────────────────────────────────────────────
EMOJI_MAP = {
    "Just me": "👤", "Me and my partner": "💑", "Family with young kids": "👨‍👩‍👧", 
    "Family, kids are older / no kids": "🏡", "A group of friends": "🎉", "Me and a few close friends": "🥂",
    
    "Hot / Summer": "☀️", "Cool / Autumn": "🍂", "Cold / Winter": "❄️", 
    "Rainy season": "🌧️", "Dry season": "🏜️", "Not sure yet": "🤔",
    
    "A day trip": "🌅", "A weekend (2–3 days)": "🏕️", "A short week (4–5 days)": "🧳", "A full week or more": "📅",
    
    "Stay close — under 2 hours": "🚗", "Domestic — anywhere in Vietnam": "🇻🇳", 
    "Open to international": "✈️", "Distance doesn't matter": "🌍",
    
    "Exhausted — need real rest": "🔋", "Bored — want something new": "🥱", "Celebrating a milestone": "🍾",
    "Disconnected — want to feel alive": "🧘", "Just want fun": "🥳", "Want to grow / discover": "🌱",
    
    "Recharged and at peace": "😌", "Excited — did something remarkable": "🤩", "Connected — to people / culture": "🤝",
    "Romantic and close": "🥰", "Happy and light-hearted": "😁", "Inspired": "💡",
    
    "Beach / coastline / sea": "🏖️", "Mountains / highlands": "⛰️", "Lush forest / jungle": "🌲",
    "Rivers, lakes, waterfalls": "🏞️", "Open countryside / rice fields": "🌾", "I don't care about the landscape": "🤷",
    
    "Completely wild and untouched": "🏕️", "Mostly natural, basic facilities": "🪵", 
    "Good mix of nature and comfort": "🛖", "Nature as backdrop — want comfort": "🏨",
    
    "It's my main reason for traveling": "🏛️", "Very interested": "🏺", 
    "Somewhat — a bit of culture is nice": "🚶", "Not really": "🙅",
    
    "Local markets and street food": "🍜", "Temples, pagodas, sacred sites": "🛕", 
    "Heritage architecture and old towns": "🏯", "Festivals or local celebrations": "🏮", 
    "Art, galleries, performances": "🎭", "Craft villages and artisans": "🏺",
    
    "Very active — hiking, climbing, paddling": "🧗", "Moderately active — walking, cycling": "🚴",
    "Low effort — strolling, sightseeing": "🚶", "Minimal — rest and enjoy": "🧘",
    
    "Trekking / hiking": "🥾", "Water activities (diving, snorkeling, surfing)": "🤿", "Camping or glamping": "⛺",
    "Kayaking or boat trips": "🛶", "Photography and scenic viewpoints": "📸", "Spa, massage, and wellness": "💆",
    "Cooking classes or food tours": "👨‍🍳", "Stargazing or night experiences": "🌌", "None in particular": "🛌",
    
    "Quiet and peaceful — no crowds": "🤫", "Lively and social — buzzing energy": "🕺", "Mysterious and atmospheric": "🌫️",
    "Romantic and intimate": "🍷", "Adventurous and raw": "🌋", "Comfortable and polished": "🛁",
    
    "Very — it has to be visually stunning": "📸", "Somewhat — nice photos are a bonus": "📱", "Not at all — how it feels matters more": "🙈",
    
    "Luxury resort or hotel": "🏨", "Private villa or guesthouse": "🏡", "Local homestay": "🏘️", 
    "Budget hostel or guesthouse": "🛏️", "Tent camping or glamping": "⛺", "No strong preference": "🤷",
    
    "Privacy and exclusivity": "🤫", "Proximity to nature": "🍃", "Cultural authenticity": "🏮", 
    "Facilities and amenities": "✨", "Price / value for money": "💰",
    
    "Food IS the trip": "🤤", "Very important — great local food is a must": "🍲", 
    "Moderate — good food but not focus": "🍽️", "Not important": "🥪",
    
    "Planned and guided — clear itinerary": "📋", "Semi-structured — a few anchors, flexible": "📝", 
    "Completely free — discover as I go": "🗺️", "Package / resort-stay — everything handled": "🛎️",
    
    "Budget is tight": "💸", "Accessibility matters (mobility needs)": "♿", "Must be safe/easy for young children": "🚸", 
    "Need reliable internet / remote work": "📶", "None — I'm flexible": "😎",

    "Making memories": "📸", "Pure relaxation": "🛁", "Exploration & discovery": "🗺️",
    "Bonding with travel companions": "🤝", "Personal challenge / growth": "🏔️", "Good food & local flavors": "🍜",
    "Sunrise hike to a summit": "🌄", "Lazy beach afternoon with a book": "📖",
    "Wandering a night market alone": "🏮", "Kayaking through limestone caves": "🛶",
    "A quiet dinner under the stars": "🌟", "Getting lost in an old quarter": "🏯",
}

# Callbacks logic
def radio_callback(q_idx, selected_idx, total_opts):
    for i in range(total_opts):
        if i != selected_idx:
            st.session_state[f"chk_{q_idx}_{i}"] = False

def multi_callback(q_idx, selected_idx, total_opts, max_sel):
    count = sum(1 for i in range(total_opts) if st.session_state.get(f"chk_{q_idx}_{i}", False))
    if count > max_sel:
        st.session_state[f"chk_{q_idx}_{selected_idx}"] = False

def render_clickable_cards(question_text, hint, mapping_dict, q_idx, is_multi=False, max_sel=3):
    st.markdown(f"<div class='question-title'>{question_text}</div>", unsafe_allow_html=True)
    if hint:
        st.markdown(f"<div class='hint'>{hint}</div>", unsafe_allow_html=True)
        
    opts = list(mapping_dict.keys())
    total_opts = len(opts)
    
    for i in range(total_opts):
        if f"chk_{q_idx}_{i}" not in st.session_state:
            st.session_state[f"chk_{q_idx}_{i}"] = False

    selected_tags = []
    selected_options = []

    def render_card(col_idx, global_i, opt, cols_list):
        with cols_list[col_idx]:
            emoji = EMOJI_MAP.get(opt, "✨")
            card_content = f"{emoji}\n{opt}"
            if not is_multi:
                is_checked = st.checkbox(card_content, key=f"chk_{q_idx}_{global_i}", on_change=radio_callback, args=(q_idx, global_i, total_opts))
            else:
                is_checked = st.checkbox(card_content, key=f"chk_{q_idx}_{global_i}", on_change=multi_callback, args=(q_idx, global_i, total_opts, max_sel))
            return is_checked

    if total_opts == 4:
        # 1 hàng 4 thẻ bằng nhau
        cols = st.columns(4, gap="small")
        for i, opt in enumerate(opts):
            chk = render_card(i, i, opt, cols)
            if chk:
                selected_tags.extend(mapping_dict[opt])
                selected_options.append(opt)

    elif total_opts == 5:
        # Hàng 1: 3 thẻ, hàng 2: 2 thẻ căn giữa
        row1 = st.columns(3, gap="small")
        for i in range(3):
            chk = render_card(i, i, opts[i], row1)
            if chk:
                selected_tags.extend(mapping_dict[opts[i]])
                selected_options.append(opts[i])
        _, c1, c2, _ = st.columns([0.5, 1, 1, 0.5], gap="small")
        for j, col in enumerate([c1, c2]):
            i = 3 + j
            with col:
                emoji = EMOJI_MAP.get(opts[i], "✨")
                card_content = f"{emoji}\n{opts[i]}"
                if not is_multi:
                    chk = st.checkbox(card_content, key=f"chk_{q_idx}_{i}", on_change=radio_callback, args=(q_idx, i, total_opts))
                else:
                    chk = st.checkbox(card_content, key=f"chk_{q_idx}_{i}", on_change=multi_callback, args=(q_idx, i, total_opts, max_sel))
                if chk:
                    selected_tags.extend(mapping_dict[opts[i]])
                    selected_options.append(opts[i])

    elif total_opts == 6:
        # 2 hàng mỗi hàng 3 thẻ
        row1 = st.columns(3, gap="small")
        for i in range(3):
            chk = render_card(i, i, opts[i], row1)
            if chk:
                selected_tags.extend(mapping_dict[opts[i]])
                selected_options.append(opts[i])
        row2 = st.columns(3, gap="small")
        for i in range(3, 6):
            chk = render_card(i - 3, i, opts[i], row2)
            if chk:
                selected_tags.extend(mapping_dict[opts[i]])
                selected_options.append(opts[i])

    elif total_opts == 9:
        # 3 hàng mỗi hàng 3 thẻ
        for row_start in range(0, 9, 3):
            row_cols = st.columns(3, gap="small")
            for j in range(3):
                i = row_start + j
                chk = render_card(j, i, opts[i], row_cols)
                if chk:
                    selected_tags.extend(mapping_dict[opts[i]])
                    selected_options.append(opts[i])

    else:
        # Mặc định: 3 cột
        cols = st.columns(3, gap="small")
        for i, opt in enumerate(opts):
            chk = render_card(i % 3, i, opt, cols)
            if chk:
                selected_tags.extend(mapping_dict[opt])
                selected_options.append(opt)
                
    return selected_tags, selected_options

# ─────────────────────────────────────────────────────────────
# INPUT SECTION — STANDARD HEADER + CLICKABLE CARDS
# ─────────────────────────────────────────────────────────────

# THAY ĐỔI TỶ LỆ CỘT Ở ĐÂY: Thu nhỏ hai bên trái phải, kéo giãn phần giữa lấp đầy màn hình
_, col_input, _ = st.columns([0.1, 4, 0.1])

with col_input:
    # --- THÊM ẢNH BÌA MÁY BAY BẦU TRỜI XANH, BỎ KHUNG TRẮNG, DÙNG BÓNG MỜ CHO CHỮ ---
    st.markdown("""
    <div style="
        background-image: url('https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2560&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 20px;
        padding: 100px 20px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    ">
        <h1 style='color: #0f172a !important; font-size: 3.6rem; margin-bottom: 10px; text-shadow: 0px 0px 15px rgba(255,255,255,0.9), 0px 0px 5px rgba(255,255,255,0.9);'>🧭 Travel Planner</h1>
        <p style='color: #1e293b !important; font-size: 1.25rem; margin-bottom: 0; font-weight: 700; text-shadow: 0px 0px 10px rgba(255,255,255,0.9);'>Answer a few questions and we'll find your perfect destination.</p>
    </div>
    """, unsafe_allow_html=True)

    tags = []
    constraints_list = []
    user_text = ""
    image_b64 = ""

    # BLOCK 10: FREE TEXT & IMAGE
    with st.container(border=True):
        st.markdown("### ✍️ Describe your ideal trip")

        st.markdown("<div class='question-title' style='margin-top: 5px;'>In your own words (Optional)</div>", unsafe_allow_html=True)
        user_text = st.text_area("In Your Own Words", 
                                 placeholder="e.g. I want to wake up to the sound of waves, eat fresh seafood, and do nothing stressful...",
                                 label_visibility="collapsed", height=100)
        
        st.markdown("<div class='question-title' style='margin-top: 15px;'>🖼 Upload inspiration image (Optional)</div>", unsafe_allow_html=True)
        uploaded_image = st.file_uploader("Upload", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_image:
            img = Image.open(uploaded_image)
            st.image(img, caption="Uploaded Image", use_container_width=True)
            image_b64 = base64.b64encode(uploaded_image.getvalue()).decode("utf-8")
            uploaded_image.seek(0)
            image_b64 = base64.b64encode(uploaded_image.read()).decode("utf-8")

    # BIẾN TOÀN BỘ CÂU HỎI THÀNH THẺ CLICKABLE CARDS
    with st.container(border=True):
        st.markdown("### 📍 Block 1 — Who & When")
        t, _ = render_clickable_cards("Q1. Who's coming on this trip?", "", SOCIAL_GROUP_TAGS, "q1")
        tags += t
        t, _ = render_clickable_cards("Q2. What season / weather will it be?", "", SEASON_TAGS, "q2")
        tags += t
        t, _ = render_clickable_cards("Q3. How long is the trip?", "", DURATION_TAGS, "q3")
        tags += t
        t, _ = render_clickable_cards("Q4. How far are you willing to travel from home?", "", DISTANCE_TAGS, "q4")
        tags += t

    with st.container(border=True):
        st.markdown("### 💭 Block 2 — Why This Trip?")
        t, _ = render_clickable_cards("Q5. What's pushing you to take this trip right now?", "", EMOTION_DRIVER_TAGS, "q5")
        tags += t
        t, _ = render_clickable_cards("Q6. How do you want to feel by the end of the trip?", "", EMOTION_OUTCOME_TAGS, "q6")
        tags += t

    with st.container(border=True):
        st.markdown("### 🌿 Block 3 — Nature & Landscape")
        t, _ = render_clickable_cards("Q7. What kind of natural landscape appeals to you most?", "", LANDSCAPE_TAGS, "q7")
        tags += t
        t, _ = render_clickable_cards("Q8. How \"raw\" do you want nature to feel?", "", RAWNESS_TAGS, "q8")
        tags += t

    with st.container(border=True):
        st.markdown("### 🏛️ Block 4 — Culture & Urban Life")
        t, _ = render_clickable_cards("Q9. How interested are you in local culture and history?", "", CULTURE_DEPTH_TAGS, "q9")
        tags += t
        t, _ = render_clickable_cards("Q10. Which cultural experiences interest you?", "(Pick all that apply)", CULTURE_SPECIFIC_TAGS, "q10", is_multi=True, max_sel=10)
        tags += t

    with st.container(border=True):
        st.markdown("### 🏃 Block 5 — Activities & Energy")
        t, _ = render_clickable_cards("Q11. How physically active do you want to be?", "", INTENSITY_TAGS, "q11")
        tags += t
        t, _ = render_clickable_cards("Q12. Which activities are you most excited about?", "(Pick all that apply)", ACTIVITY_TAGS, "q12", is_multi=True, max_sel=10)
        tags += t

    with st.container(border=True):
        st.markdown("### ✨ Block 6 — Atmosphere & Vibe")
        t, _ = render_clickable_cards("Q13. What's the vibe you're going for?", "(Pick all that apply)", VIBE_TAGS, "q13", is_multi=True, max_sel=10)
        tags += t
        t, _ = render_clickable_cards("Q14. How important is it that the place looks amazing in photos?", "", PHOTO_TAGS, "q14")
        tags += t

    with st.container(border=True):
        st.markdown("### 🏡 Block 7 — Where You Stay")
        t, _ = render_clickable_cards("Q15. Where would you like to stay?", "", ACCOMMODATION_TAGS, "q15")
        tags += t
        t, _ = render_clickable_cards("Q16. What matters most in your accommodation?", "", ACCOMMODATION_PRIORITY_TAGS, "q16")
        tags += t

    with st.container(border=True):
        st.markdown("### 🍜 Block 8 — Food")
        t, _ = render_clickable_cards("Q17. How important is food on this trip?", "", FOOD_TAGS, "q17")
        tags += t

    with st.container(border=True):
        st.markdown("### 🎒 Block 9 — Travel Style & Constraints")
        t, _ = render_clickable_cards("Q18. How do you prefer to travel?", "", STYLE_TAGS, "q18")
        tags += t
        t, opts = render_clickable_cards("Q19. Any hard constraints for this trip?", "(Pick all that apply)", CONSTRAINT_TAGS, "q19", is_multi=True, max_sel=10)
        tags += t
        constraints_list = opts
        t, _ = render_clickable_cards("Q20. Which of these moments sounds most like your perfect trip?", "(Pick one)", TRIP_MOMENT_TAGS, "q20")
        tags += t

    # Lọc tags trùng
    seen = set()
    unique_tags = [t for t in tags if t not in seen and not seen.add(t)]

    # -----------------------------------------------------------------
    # BOTTOM PROGRESS BAR (Thanh tiến trình đặt sát cuối form)
    # -----------------------------------------------------------------
    st.write("")
    
    # Đếm số lượng thẻ đã được tick trong session_state
    answered = sum(1 for k, v in st.session_state.items() if str(k).startswith("chk_") and v is True)
    # Form có 19 câu hỏi dạng check/radio
    progress = min(answered / 19, 1.0)
    
    st.markdown(f"<p style='text-align: center; color: #1e293b; font-weight: bold; margin-bottom: 5px; font-size: 0.95rem;'>🚀 Preference gathering progress: {int(progress * 100)}%</p>", unsafe_allow_html=True)
    st.progress(progress)
    st.write("") 
    
    st.markdown(f"🏷️ <span style='color:#7f8c8d'>**Tags Profile ({len(unique_tags)}):** {', '.join(unique_tags) if unique_tags else 'none'}</span>", unsafe_allow_html=True)
    submit = st.button("🚀 Build Itinerary & Find Locations", type="primary", use_container_width=True)

st.divider()

# ═════════════════════════════════════════════════════════════
# OUTPUT SECTION — full wide page (GIỮ NGUYÊN HOÀN TOÀN 100%)
# ═════════════════════════════════════════════════════════════

if submit:

    if not user_text and not unique_tags:
        st.warning("Please answer at least one question or describe your trip.")
    else:
        # N8 API contract: { text, image, tags, constraint, top_k_locations }
        payload = {
            "text": user_text,
            "image": image_b64,
            "tags": unique_tags,
            "constraint": constraints_list,
            "top_k_locations": 5,
        }

        with st.spinner("⏳ Analyzing travel profile and finding the best locations for you..."):
            time.sleep(1.5)

            st.info(f"📝 text: {len(user_text)} chars | 🏷️ tags: {len(unique_tags)} | 🖼️ image: {'yes' if image_b64 else 'no'} | 🚫 constraint: {len(constraints_list)}")

            try:
                res = requests.post(
                    "http://localhost:5000/recommend",
                    json=payload,
                    timeout=60
                )

                if res.status_code != 200:
                    st.error(res.text)
                    st.stop()

                data = res.json()
                locations = data.get("locations", [])
                trace = data.get("trace", {})
                user_trace = trace.get("user", {})
                user_vectors = user_trace.get("user_vectors", {})
                sig_k = user_trace.get("n1_embedding", {}).get("sig_k", 0)
                img_desc = user_trace.get("n2_image", {}).get("img_desc", "")

                st.success("✅ Results found!")
                st.subheader("📍 Suggested Locations")

                placeholders = []

                for loc in locations:
                    loc_id = loc.get("location_id", "unknown")
                    meta = loc.get("metadata", {})
                    name = meta.get("name", loc_id)
                    score = loc.get("score", 0)
                    reason = loc.get("reason", "")
                    desc = meta.get("description", "")
                    img_path = loc.get("image_path", "")

                    col_loc, col_act = st.columns(2)

                    with col_loc:
                        st.markdown(f"### {name}")
                        st.metric("Score", f"{score:.4f}")
                        if reason:
                            st.caption(f"💡 {reason}")
                        if desc:
                            st.write(desc)
                        if img_path:
                            try:
                                st.image(img_path, caption=name, use_container_width=True)
                            except Exception:
                                pass

                    with col_act:
                        st.markdown("#### 🎯 Activities")
                        ph = st.empty()
                        with ph.container():
                            st.caption("⏳ Loading activities…")

                        placeholders.append({
                            "placeholder": ph,
                            "loc_id": loc_id,
                            "meta": meta,
                        })

                    st.divider()

                for item in placeholders:
                    ph = item["placeholder"]
                    loc_id = item["loc_id"]
                    meta = item["meta"]

                    with ph.container():
                        st.caption(f"🔄 Generating activities for **{meta.get('name', loc_id)}**…")

                    act_payload = {
                        "text": user_text,
                        "img_desc": img_desc,
                        "tags": unique_tags,
                        "sig_k": sig_k,
                        "user_vectors": user_vectors,
                        "constraints": {},
                        "context": {},
                        "location": {"location_id": loc_id, "metadata": meta},
                        "top_k_activities": 5,
                    }

                    try:
                        act_res = requests.post(
                            "http://localhost:5000/activities",
                            json=act_payload,
                            timeout=120,
                        )
                        if act_res.status_code == 200:
                            ranked_activities = act_res.json().get("activities", [])

                            with ph.container():
                                if not ranked_activities:
                                    st.write("No activities found.")
                                for act in ranked_activities:
                                    a_meta = act.get("metadata", {})
                                    a_name = a_meta.get("name", "Unknown")
                                    a_score = act.get("score", 0)
                                    a_reason = act.get("reason", "")
                                    a_type = a_meta.get("activity_type", "")

                                    st.markdown(
                                        f"**{a_name}** ({a_type})  \n"
                                        f"Score: `{a_score:.2f}` — {a_reason}"
                                    )
                        else:
                            with ph.container():
                                st.error("Failed to load activities.")
                    except Exception as e:
                        with ph.container():
                            st.error(f"Error: {e}")

                with st.expander("🔍 Trace (Debug)"):
                    st.markdown("**User Input**")
                    st.json(user_trace.get("input", {}))

                    n2_trace = user_trace.get("n2_image", {})
                    if n2_trace.get("img_desc"):
                        st.markdown("**N2 — Image Description**")
                        st.write(n2_trace["img_desc"])

                    n1_trace = user_trace.get("n1_embedding", {})
                    st.markdown(f"**N1 — sig_k = {n1_trace.get('sig_k', '?')}**")

                    st.markdown("**Vector Dimensions**")
                    st.json(user_trace.get("vector_dims", {}))

                    st.markdown("**N4 — Ranking**")
                    st.json(trace.get("ranking", {}))

                    st.markdown("**Debug**")
                    st.json(trace.get("debug", {}))

                with st.expander("📦 RAW RESPONSE"):
                    st.json(data)

            except Exception as e:
                st.error(f"Connection failed: {e}")