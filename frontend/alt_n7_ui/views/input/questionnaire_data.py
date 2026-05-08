"""
questionnaire_data.py — Bảng câu hỏi du lịch Việt Nam
Dựa trên bộ tag chuẩn từ maps/tags.py.

Cấu trúc mỗi câu hỏi:
  question   — Câu hỏi hiển thị cho người dùng
  multi      — True nếu cho phép chọn nhiều (tối đa max_select)
  categories — Các lựa chọn chính (hiển thị dạng thẻ / nút bấm)
  specifics  — Dropdown mở rộng bên trong mỗi nhóm (tuỳ chọn)

Thứ tự câu hỏi:
  Q1 — Phong cảnh          (Landscape)
  Q2 — Người đồng hành     (Companion)
  Q3 — Cảm xúc & Không khí (Vibe & Mood)
  Q4 — Ẩm thực             (Food & Drink)
  Q5 — Hoạt động           (Activities)
  Q6 — Phong cách đi       (Style & Budget)
"""

QUESTIONNAIRE_CONFIG = {

    # ─────────────────────────────────────────────────────────────
    # Q1 — PHONG CẢNH & THIÊN NHIÊN
    # ─────────────────────────────────────────────────────────────
    "q1_landscape": {
        "question"   : "Bạn muốn khám phá loại phong cảnh nào? (chọn tối đa 3)",
        "multi"      : True,
        "max_select" : 3,
        "categories" : {
            "⛰️ Địa hình": {
                "Núi cao"       : ["mountain"],
                "Đồi núi"       : ["hill"],
                "Thung lũng"    : ["valley"],
                "Cao nguyên"    : ["plateau"],
            },
            "🌊 Sông & Biển": {
                "Bãi biển"      : ["beach"],
                "Đảo"           : ["island"],
                "Sông"          : ["river"],
                "Hồ"            : ["lake"],
            },
            "🌿 Hệ sinh thái": {
                "Vườn quốc gia" : ["national park"],
                "Rừng rậm"      : ["forest"],
                "Khu bảo tồn"   : ["nature reserve"],
                "Rạn san hô"    : ["coral reef"],
            },
            "🏙️ Xã hội": {
                "Thành thị"     : ["city"],
                "Phố cổ"        : ["old town"],
                "Làng quê"      : ["village"],
            },
        },
        "specifics"  : {
            "🏡 Cảnh quan đặc trưng khác của Việt Nam": {
                "Đá vôi & Karst"    : ["karst"],
                "Vách đá"           : ["cliff"],
                "Hang động"         : ["cave"],
                "Đồi cát"           : ["sand dune"],
                "Quần đảo"          : ["archipelago"],
                "Suối"              : ["stream"],
                "Thác nước"         : ["waterfall"],
                "Suối nước nóng"    : ["hot spring"],
                "Đất ngập nước"     : ["wetland"],
                "Rừng thông"        : ["pine forest"],
                "Rừng tre"          : ["bamboo forest"],
                "Rừng ngập mặn"     : ["mangrove"],
                "Khu dự trữ sinh quyển": ["biosphere reserve"],
                "Ruộng bậc thang"   : ["rice terrace"],
                "Nông trại"         : ["farm"],
                "Đồng hoa"          : ["flower field"],
                "Đồng bằng"         : ["delta"],
            },
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Q2 — NGƯỜI ĐỒNG HÀNH
    # ─────────────────────────────────────────────────────────────
    "q2_companion": {
        "question"   : "Bạn chia sẻ chuyến đi này cùng với những ai?",
        "multi"      : False,
        "categories" : {
            "👥 Thành phần": {
                "Một mình"      : ["solo"],
                "Cặp đôi"       : ["couple"],
                "Gia đình"      : ["family"],
                "Nhóm bạn"      : ["friends trip"],
                "Đồng nghiệp"   : ["corporate"],
            },
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Q3 — CẢM XÚC & KHÔNG KHÍ MONG MUỐN
    # ─────────────────────────────────────────────────────────────
    "q3_vibes": {
        "question"   : "Bạn muốn chuyến đi mang lại cảm giác gì? (chọn tối đa 4)",
        "multi"      : True,
        "max_select" : 4,
        "categories" : {
            "💕 Cảm xúc": {
                "Lãng mạn"          : ["romantic"],
                "Hoang dã"          : ["wild"],
                "Hoài cổ"           : ["nostalgic"],
                "Tâm linh"          : ["spiritual"],
            },
            "😌 Thư giãn": {
                "Yên bình"          : ["peaceful"],
                "Chill"             : ["chill"],
                "Chậm rãi"          : ["slow travel"],
                "Ấm cúng"           : ["cozy"],
            },
            "🌋 Khám phá": {
                "Sôi động"          : ["vibrant"],
                "Phiêu lưu"         : ["adventure"],
                "Góc khuất ẩn mình" : ["off the beaten path"],
                "Trải nghiệm sâu"   : ["immersive"],
            },
            "✨ Thẩm mỹ": {
                "Nên thơ"           : ["picturesque"],
                "Bohemian"          : ["bohemian"],
                "Mộc mạc"           : ["rustic"],
                "Hiện đại"          : ["modern"],
            },
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Q4 — ẨM THỰC & ĐỒ UỐNG
    # ─────────────────────────────────────────────────────────────
    "q4_food": {
        "question"   : "Bạn muốn trải nghiệm ẩm thực theo phong cách nào?",
        "multi"      : False,
        "categories" : {
            "🍱 Ẩm thực": {
                "Vỉa hè"        : ["street food"],
                "Đặc sản"       : ["local cuisine"],
                "Nhà hàng"      : ["fine dining"],
                "Tour ẩm thực"  : ["food tour"],
                "Hải sản"       : ["seafood"],
            },
        },
        "specifics"  : {
            "🍽️ Lựa chọn ẩm thực đặc biệt khác": {
                "Ẩm thực cung đình"    : ["royal cuisine"],
                "Hữu cơ & Sạch"        : ["organic"],
                "Ăn chay (vegetarian)" : ["vegetarian"],
                "Thuần chay (vegan)"   : ["vegan"],
                "Halal"                : ["halal"],
                "Cà phê Việt Nam"      : ["coffee"],
                "Bia thủ công"         : ["craft beer"],
                "Hoa quả nhiệt đới"    : ["tropical fruit"],
                "Rượu truyền thống"    : ["local wine"],
                "Trà cao nguyên"       : ["tea"],
            },
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Q5 — HOẠT ĐỘNG
    # ─────────────────────────────────────────────────────────────
    "q5_activities": {
        "question"   : "Bạn muốn trải nghiệm hoạt động gì? (chọn tối đa 5)",
        "multi"      : True,
        "max_select" : 5,
        "categories" : {},
        "specifics"  : {
            "🥾 Phiêu lưu trên cạn": {
                "Trekking"              : ["trekking"],
                "Leo núi"               : ["hiking"],
                "Tour xe máy"           : ["motorbiking"],
                "Đạp xe"                : ["cycling"],
                "Leo vách đá"           : ["rock climbing"],
                "Thám hiểm hang động"   : ["caving"],
                "Canyoning"             : ["canyoning"],
                "Cắm trại"              : ["camping"],
                "Tour xe Jeep"          : ["jeep tour"],
                "Tour xe địa hình"      : ["ATV"],
            },
            "🌊 Phiêu lưu dưới nước": {
                "Lặn có bình khí"       : ["scuba diving"],
                "Lặn ống thở"           : ["snorkeling"],
                "Seawalk"               : ["seawalk"],
                "Chèo thuyền kayak"     : ["kayaking"],
                "SUP (đứng chèo)"       : ["stand up paddle"],
                "Lướt sóng"             : ["surfing"],
                "Kitesurfing"           : ["kitesurfing"],
                "Chèo thuyền vượt thác" : ["rafting"],
                "Bơi lội"               : ["swimming"],
                "Tắm bùn khoáng"        : ["mud bath"],
            },
            "🛶 Trải nghiệm trên sông": {
                "Du thuyền qua đêm"      : ["boat cruise"],
                "Thuyền gỗ truyền thống" : ["junk boat"],
                "Thuyền thúng"           : ["basket boat"],
                "Tàu cao tốc"            : ["speed boat"],
                "Du thuyền sông"         : ["river cruise"],
                "Câu cá"                 : ["fishing"],
                "Câu mực ban đêm"        : ["squid fishing"],
            },
            "🎈 Trên không & Giải trí": {
                "Cáp treo"              : ["cable car"],
                "Dù lượn"               : ["paragliding"],
                "Khinh khí cầu"         : ["hot air balloon"],
                "Hành trình tàu hỏa"    : ["train journey"],
                "Tour xích lô"          : ["cyclo"],
                "Chụp ảnh phong cảnh"   : ["photography"],
                "Mua sắm"               : ["shopping"],
                "Golf"                  : ["golf"],
                "Công viên giải trí"    : ["theme park"],
                "Công viên nước"        : ["water park"],
                "Dã ngoại / Picnic"     : ["picnic"],
                "Tour đêm"              : ["night tour"],
            },
            "🧖 Sức khoẻ & Spa": {
                "Spa & Massage"         : ["spa"],
                "Tắm thảo dược"         : ["herbal bath"],
                "Retreat Yoga"          : ["yoga retreat"],
                "Retreat sức khoẻ"      : ["wellness retreat"],
                "Tắm suối nước nóng"    : ["hot spring bath"],
            },
            "🍜 Văn hoá & Học hỏi": {
                "Lớp học nấu ăn"        : ["cooking class"],
                "Lớp làm gốm"           : ["pottery class"],
                "Làm đèn lồng"          : ["lantern making"],
                "Thăm trang trại"       : ["farm tour"],
                "Thưởng trà"            : ["tea tasting"],
                "Tour cà phê"           : ["coffee tour"],
                "Biểu diễn nghệ thuật"  : ["cultural show"],
                "Âm nhạc truyền thống"  : ["traditional music"],
                "Làng nghề thủ công"    : ["craft village"],
            },
        },
    },

    # ─────────────────────────────────────────────────────────────
    # Q6 — PHONG CÁCH & NGÂN SÁCH
    # ─────────────────────────────────────────────────────────────
    "q6_style": {
        "question"   : "Bạn thích đi theo phong cách nào?",
        "multi"      : False,
        "categories" : {},
        "specifics"  : {
            "⏱️ Thời lượng & Dịp đặc biệt": {
                "Đi về trong ngày"  : ["day trip"],
                "Cuối tuần"         : ["weekend trip"],
                "Dài ngày"          : ["long stay"],
                "Workcation"        : ["workcation"],
                "Phượt bụi"         : ["backpacking"],
                "Tuần trăng mật"    : ["honeymoon"],
                "Kỷ niệm"           : ["couple"],
                "Team building"     : ["group"],
            },
            "💰 Ngân sách & Nhịp độ": {
                "Tiết kiệm / Bụi"   : ["budget", "backpacking"],
                "Tầm trung"         : ["mid range"],
                "Sang trọng"        : ["luxury"],
                "Chậm & Sâu"        : ["slow travel"],
            },
            "🏠 Nơi lưu trú": {
                "Khu nghỉ dưỡng"    : ["resort"],
                "Khách sạn boutique": ["boutique"],
                "Homestay"          : ["homestay"],
                "Eco lodge"         : ["eco lodge"],
                "Glamping"          : ["glamping"],
                "Cắm trại"          : ["camping"],
            },
            "🏘️ Trải nghiệm đô thị": {
                "Làng chài"             : ["fishing village"],
                "Chợ nổi"               : ["floating market"],
                "Chợ đêm"               : ["night market"],
                "Phố đi bộ"             : ["walking street"],
                "Bar rooftop"           : ["rooftop bar"],
                "Không gian coworking"  : ["coworking"],
            },
            "🎒 Du lịch chuyên biệt": {
                "Du lịch sinh thái"      : ["eco travel"],
                "Du lịch nông nghiệp"    : ["agro tourism"],
                "Du lịch sức khoẻ"       : ["wellness tourism"],
                "Tour ẩm thực chuyên đề" : ["culinary tourism"],
                "Du lịch chiến trường"   : ["war tourism"],
                "Du lịch tâm linh"       : ["religious tourism"],
                "Du lịch thể thao"       : ["sports tourism"],
                "Tour chụp ảnh"          : ["photography tour"],
                "Du lịch y tế"           : ["medical tourism"],
                "Digital nomad"          : ["digital nomad"],
                "MICE & Doanh nghiệp"    : ["MICE"],
            },
        },
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# EMOJI MAP — keys match exact option names in QUESTIONNAIRE_CONFIG above
# ─────────────────────────────────────────────────────────────────────────────

EMOJI_MAP = {
    # Q1 — categories
    "Núi cao"               : "🏔️",
    "Đồi núi"               : "⛰️",
    "Thung lũng"            : "🌄",
    "Cao nguyên"            : "🏜️",
    "Bãi biển"              : "🏖️",
    "Đảo"                   : "🏝️",
    "Sông"                  : "🛶",
    "Hồ"                    : "🦢",
    "Vườn quốc gia"         : "🌲",
    "Rừng rậm"              : "🌳",
    "Khu bảo tồn"           : "🌿",
    "Rạn san hô"            : "🪸",
    "Thành thị"             : "🏙️",
    "Phố cổ"                : "🏛️",
    "Làng quê"              : "🏘️",
    # Q1 — specifics
    "Đá vôi & Karst"        : "🪨",
    "Vách đá"               : "🧗",
    "Hang động"             : "🦇",
    "Đồi cát"               : "🏜️",
    "Quần đảo"              : "🏝️",
    "Suối"                  : "💧",
    "Thác nước"             : "💦",
    "Suối nước nóng"        : "♨️",
    "Đất ngập nước"         : "🦅",
    "Rừng thông"            : "🌲",
    "Rừng tre"              : "🎋",
    "Rừng ngập mặn"         : "🌱",
    "Ruộng bậc thang"       : "🌾",
    "Nông trại"             : "🚜",
    "Đồng hoa"              : "🌸",
    "Đồng bằng"             : "🏞️",

    # Q2
    "Một mình"              : "👤",
    "Cặp đôi"               : "💑",
    "Gia đình"              : "👨‍👩‍👧",
    "Nhóm bạn"              : "🎉",
    "Đồng nghiệp"           : "🏢",

    # Q3
    "Lãng mạn"              : "💕",
    "Hoang dã"              : "🐾",
    "Hoài cổ"               : "🎞️",
    "Tâm linh"              : "📿",
    "Yên bình"              : "🧘",
    "Chill"                 : "🥤",
    "Chậm rãi"              : "🐚",
    "Ấm cúng"               : "🕯️",
    "Sôi động"              : "⚡",
    "Phiêu lưu"             : "🌋",
    "Góc khuất ẩn mình"     : "🕵️",
    "Trải nghiệm sâu"       : "🌀",
    "Nên thơ"               : "🖼️",
    "Bohemian"              : "🎸",
    "Mộc mạc"               : "🪵",
    "Hiện đại"              : "🏙️",

    # Q4 — categories
    "Vỉa hè"                : "🍜",
    "Đặc sản"               : "🍲",
    "Nhà hàng"              : "🍴",
    "Tour ẩm thực"          : "🍢",
    "Hải sản"               : "🦐",
    # Q4 — specifics
    "Ẩm thực cung đình"     : "👑",
    "Hữu cơ & Sạch"         : "🌿",
    "Ăn chay (vegetarian)"  : "🥗",
    "Thuần chay (vegan)"    : "🥑",
    "Halal"                 : "☪️",
    "Cà phê Việt Nam"       : "☕",
    "Bia thủ công"          : "🍺",
    "Hoa quả nhiệt đới"     : "🍍",
    "Rượu truyền thống"     : "🍶",
    "Trà cao nguyên"        : "🍵",

    # Q5
    "Trekking"              : "🥾",
    "Leo núi"               : "👟",
    "Tour xe máy"           : "🏍️",
    "Đạp xe"                : "🚴",
    "Leo vách đá"           : "🧗",
    "Thám hiểm hang động"   : "🔦",
    "Canyoning"             : "🧗",
    "Cắm trại"              : "⛺",
    "Tour xe Jeep"          : "🚙",
    "Tour xe địa hình"      : "🏎️",
    "Lặn có bình khí"       : "🤿",
    "Lặn ống thở"           : "🐠",
    "Seawalk"               : "🐟",
    "Chèo thuyền kayak"     : "🛶",
    "SUP (đứng chèo)"       : "🏄",
    "Lướt sóng"             : "🏄",
    "Kitesurfing"           : "🪁",
    "Chèo thuyền vượt thác" : "🌊",
    "Bơi lội"               : "🏊",
    "Tắm bùn khoáng"        : "🧖",
    "Du thuyền qua đêm"     : "🛳️",
    "Thuyền gỗ truyền thống": "⛵",
    "Thuyền thúng"          : "🧺",
    "Tàu cao tốc"           : "🚤",
    "Du thuyền sông"        : "🛥️",
    "Câu cá"                : "🎣",
    "Câu mực ban đêm"       : "🦑",
    "Cáp treo"              : "🚡",
    "Dù lượn"               : "🪂",
    "Khinh khí cầu"         : "🎈",
    "Hành trình tàu hỏa"    : "🚂",
    "Tour xích lô"          : "🚲",
    "Chụp ảnh phong cảnh"   : "📷",
    "Mua sắm"               : "🛍️",
    "Golf"                  : "⛳",
    "Công viên giải trí"    : "🎡",
    "Công viên nước"        : "⛲",
    "Dã ngoại / Picnic"     : "🧺",
    "Tour đêm"              : "🌙",
    "Spa & Massage"         : "💆",
    "Tắm thảo dược"         : "🛁",
    "Retreat Yoga"          : "🧘",
    "Retreat sức khoẻ"      : "🌿",
    "Tắm suối nước nóng"    : "♨️",
    "Lớp học nấu ăn"        : "👨‍🍳",
    "Lớp làm gốm"           : "🏺",
    "Làm đèn lồng"          : "🏮",
    "Thăm trang trại"       : "🧑‍🌾",
    "Thưởng trà"            : "🍵",
    "Tour cà phê"           : "☕",
    "Biểu diễn nghệ thuật"  : "🎭",
    "Âm nhạc truyền thống"  : "🎶",
    "Làng nghề thủ công"    : "🔨",

    # Q6
    "Đi về trong ngày"      : "☀️",
    "Cuối tuần"             : "🧳",
    "Dài ngày"              : "📅",
    "Workcation"            : "💻",
    "Phượt bụi"             : "🎒",
    "Tuần trăng mật"        : "💍",
    "Kỷ niệm"               : "🥂",
    "Team building"         : "🤝",
    "Tiết kiệm / Bụi"       : "🫰",
    "Tầm trung"             : "💵",
    "Sang trọng"            : "💎",
    "Chậm & Sâu"            : "🐚",
    "Khu nghỉ dưỡng"        : "🏰",
    "Khách sạn boutique"    : "🛎️",
    "Homestay"              : "🏡",
    "Eco lodge"             : "🛖",
    "Glamping"              : "🏕️",
    "Cắm trại"              : "⛺",
    "Làng chài"             : "🛶",
    "Chợ nổi"               : "🚣",
    "Chợ đêm"               : "🏮",
    "Phố đi bộ"             : "🚶",
    "Bar rooftop"           : "🍸",
    "Không gian coworking"  : "💻",
    "Du lịch sinh thái"     : "🍃",
    "Du lịch nông nghiệp"   : "🧑‍🌾",
    "Du lịch sức khoẻ"      : "🧘",
    "Tour ẩm thực chuyên đề": "🍳",
    "Du lịch chiến trường"  : "🎖️",
    "Du lịch tâm linh"      : "🛕",
    "Du lịch thể thao"      : "🏃",
    "Tour chụp ảnh"         : "🔭",
    "Du lịch y tế"          : "🏥",
    "Digital nomad"         : "🌍",
    "MICE & Doanh nghiệp"   : "💼",
}