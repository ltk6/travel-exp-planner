# =============================================================================
# n5_activity_templates.py
# Database mẫu các hoạt động du lịch theo địa điểm (PHIÊN BẢN MỞ RỘNG).
#
# File này chứa toàn bộ dữ liệu template cho module N5 Activity Generator.
# Có thể mở rộng thêm địa điểm và hoạt động mới tại đây.
#
# SCHEMA MỚI (v2):
#   Mỗi activity gồm đầy đủ các trường:
#     - activity_id:        ID duy nhất (str)
#     - location_id:        ID location (str)
#     - name:               Tên hoạt động (str)
#     - description:        Mô tả hấp dẫn 2-4 câu (str)
#     - tags:               5-7 tags phong phú để hỗ trợ embedding (list[str])
#     - cost:               Chi phí VNĐ/người (int)
#     - estimated_duration: Thời gian ước tính (phút) (int)
#     - best_time:          Thời gian tốt nhất trong ngày (list[str])
#     - suitable_for:       Đối tượng phù hợp (list[str])
#     - difficulty:         Mức độ khó (str: easy/medium/hard)
#     - season:             Tháng phù hợp nhất (list[str])
#     - reason_template:    Template ngắn giải thích cá nhân hóa (str)
#
# CÁC TRƯỜNG CŨ TƯƠNG THÍCH NGƯỢC:
#   - "desc" → alias cho "description" (dùng trong generate_activities gốc)
#   - "time" → alias cho "estimated_duration"
#   - "cost" → giữ nguyên
#   - "tags" → giữ nguyên nhưng mở rộng 5-7 tags
# =============================================================================
# Template bank cho N5 Activity Generator.
#
# THIẾT KẾ:
#   - LOCATION_PROFILES: đặc trưng từng địa điểm (tags, mô tả, mùa)
#   - ACTIVITY_TYPE_BANK: ~100+ template theo activity_type × subtype
#   - Mỗi template là "recipe" — N5 sẽ instantiate + biến thể để đạt 100/location
#
# SCALABILITY:
#   - Thêm location mới: chỉ cần thêm vào LOCATION_PROFILES
#   - Thêm loại hoạt động mới: thêm vào ACTIVITY_TYPE_BANK
#   - Generator engine trong n5_activity_generator.py tự scale ra 100/location
# =============================================================================

from typing import Dict, List, Any

import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ===========================================================================
# ĐƯỜNG DẪN TỚI FILE JSON CHÍNH (tạo bởi LLM / script generate)
# ===========================================================================
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(_CURRENT_DIR, "data")
_ACTIVITIES_JSON_PATH = os.path.join(_DATA_DIR, "activities.json")


def load_activities_from_json(json_path: str = None) -> List[Dict]:
    """
    Đọc danh sách activities từ file JSON.
    
    File JSON chứa toàn bộ activities với đầy đủ schema v2.
    Nếu file không tồn tại → trả về list rỗng và log warning.
    
    Returns:
        List[Dict]: Danh sách activities từ JSON.
    """
    path = json_path or _ACTIVITIES_JSON_PATH
    if not os.path.exists(path):
        logger.warning(f"Không tìm thấy file activities JSON: {path}")
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            logger.error(f"File activities JSON không phải là array: {path}")
            return []
        
        logger.info(f"Đã load {len(data)} activities từ {path}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Lỗi parse JSON tại {path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Lỗi đọc file {path}: {e}")
        return []


def group_activities_by_location(activities: List[Dict]) -> Dict[str, Dict]:
    """
    Nhóm activities theo location_id, trả về dict tương thích với ACTIVITY_TEMPLATES cũ.
    
    Input: danh sách activities từ JSON (schema v2)
    Output: dict có dạng:
    {
        "Sa Pa": {
            "name": "Sa Pa",
            "tags": [...],   # tổng hợp unique tags từ tất cả activities
            "activities": [
                {
                    "name": "...",
                    "desc": "...",        # alias cho description
                    "cost": ...,
                    "time": ...,          # alias cho estimated_duration
                    "tags": [...],
                    # + tất cả các trường schema v2 khác
                }
            ]
        }
    }
    
    Đảm bảo backward-compatible với hàm generate_activities gốc.
    """
    # Mapping từ location_id → tên hiển thị
    LOCATION_ID_TO_NAME = {
        "loc_sapa": "Sa Pa",
        "loc_dalat": "Đà Lạt",
        "loc_hoian": "Hội An",
        "loc_phuquoc": "Phú Quốc",
        "loc_hagiang": "Hà Giang",
        "loc_phongnha": "Phong Nha",
        "loc_hue": "Huế",
        "loc_danang": "Đà Nẵng",
        "loc_halong": "Hạ Long",
        "loc_nhatrang": "Nha Trang",
    }
    
    grouped: Dict[str, Dict] = {}
    
    for act in activities:
        loc_id = act.get("location_id", "")
        loc_name = LOCATION_ID_TO_NAME.get(loc_id, loc_id.replace("loc_", "").replace("_", " ").title())
        
        if loc_name not in grouped:
            grouped[loc_name] = {
                "name": loc_name,
                "tags": [],
                "activities": [],
            }
        
        # Tạo activity entry tương thích ngược (có cả trường cũ và mới)
        activity_entry = {
            # Trường cũ (backward-compatible)
            "name": act.get("name", ""),
            "desc": act.get("description", ""),
            "cost": act.get("cost", 0),
            "time": act.get("estimated_duration", 60),
            "tags": act.get("tags", []),
            
            # Trường mới (schema v2)
            "activity_id": act.get("activity_id", ""),
            "location_id": act.get("location_id", ""),
            "description": act.get("description", ""),
            "estimated_duration": act.get("estimated_duration", 60),
            "best_time": act.get("best_time", []),
            "suitable_for": act.get("suitable_for", []),
            "difficulty": act.get("difficulty", "easy"),
            "season": act.get("season", []),
            "reason_template": act.get("reason_template", ""),
        }
        
        grouped[loc_name]["activities"].append(activity_entry)
        
        # Tổng hợp unique tags cho location
        for tag in act.get("tags", []):
            if tag not in grouped[loc_name]["tags"]:
                grouped[loc_name]["tags"].append(tag)
    
    return grouped


# ===========================================================================
# ACTIVITY_TEMPLATES: DICT CHÍNH DÙNG BỞI generate_activities()
#
# Ưu tiên: load từ activities.json (schema v2 đầy đủ)
# Fallback: dùng hardcoded templates bên dưới nếu JSON không tồn tại
# ===========================================================================

# Hardcoded fallback templates (schema v1 - tương thích ngược)
_FALLBACK_TEMPLATES: Dict[str, Any] = {
    "Sa Pa": {
        "name": "Sa Pa",
        "tags": ["mountain", "nature", "cool", "trekking", "culture"],
        "activities": [
            {"name": "Trekking Fansipan", "desc": "Leo núi Fansipan bằng cáp treo hoặc trek nhẹ", "cost": 800000, "time": 240, "tags": ["adventure", "nature", "trekking", "mountain", "iconic"]},
            {"name": "Thăm bản Cát Cát", "desc": "Khám phá văn hóa dân tộc và ruộng bậc thang", "cost": 150000, "time": 120, "tags": ["culture", "relax", "ethnic", "village", "photography"]},
            {"name": "Chụp ảnh ruộng bậc thang", "desc": "Thưởng ngoạn và chụp ảnh tại ruộng bậc thang", "cost": 50000, "time": 90, "tags": ["photography", "nature", "landscape", "scenic"]},
            {"name": "Ăn đặc sản thắng cố & lợn cắp nách", "desc": "Thử ẩm thực địa phương", "cost": 200000, "time": 60, "tags": ["food", "cuisine", "local_food", "culture"]},
        ]
    },
    "Phú Quốc": {
        "name": "Phú Quốc",
        "tags": ["beach", "sea", "resort", "relax", "island"],
        "activities": [
            {"name": "Snorkeling tại Bãi Sao", "desc": "Lặn ngắm san hô", "cost": 400000, "time": 180, "tags": ["adventure", "sea", "snorkeling", "nature"]},
            {"name": "Thăm vườn tiêu", "desc": "Khám phá nông trại tiêu nổi tiếng", "cost": 100000, "time": 90, "tags": ["nature", "agriculture", "education"]},
            {"name": "Ngắm hoàng hôn trên biển", "desc": "Thư giãn tại bãi biển", "cost": 50000, "time": 120, "tags": ["relax", "photography", "sunset", "beach"]},
        ]
    },
    "Đà Lạt": {
        "name": "Đà Lạt",
        "tags": ["mountain", "cool", "flower", "nature", "romantic"],
        "activities": [
            {"name": "Tham quan đồi chè Cầu Đất", "desc": "Ngắm cảnh và thử trà", "cost": 150000, "time": 120, "tags": ["nature", "relax", "tea", "photography"]},
            {"name": "Chèo thuyền trên hồ Xuân Hương", "desc": "Hoạt động thư giãn", "cost": 100000, "time": 60, "tags": ["relax", "lake", "romantic"]},
            {"name": "Thăm vườn hoa thành phố", "desc": "Chụp ảnh hoa", "cost": 80000, "time": 90, "tags": ["photography", "flower", "nature", "garden"]},
        ]
    },
    "Hội An": {
        "name": "Hội An",
        "tags": ["culture", "history", "food", "relax", "photography", "heritage"],
        "activities": [
            {"name": "Tham quan phố cổ Hội An", "desc": "Khám phá các ngôi nhà cổ và hội quán", "cost": 120000, "time": 180, "tags": ["culture", "history", "photography", "heritage"]},
            {"name": "Đi thuyền trên sông Hoài", "desc": "Ngắm phố cổ về đêm và thả đèn hoa đăng", "cost": 150000, "time": 60, "tags": ["relax", "culture", "photography", "romantic"]},
            {"name": "May áo dài lấy ngay", "desc": "May đo trang phục truyền thống", "cost": 1000000, "time": 120, "tags": ["culture", "shopping", "fashion", "traditional"]},
            {"name": "Thưởng thức Cao Lầu & Mì Quảng", "desc": "Ăn các món đặc sản Hội An", "cost": 80000, "time": 60, "tags": ["food", "culture", "local_food", "cuisine"]},
            {"name": "Đạp xe dạo quanh ruộng lúa", "desc": "Đạp xe ra vùng ven ngắm cảnh", "cost": 50000, "time": 120, "tags": ["nature", "relax", "sports", "cycling"]},
            {"name": "Tham gia lớp học nấu ăn", "desc": "Học làm các món ăn đặc trưng miền Trung", "cost": 500000, "time": 150, "tags": ["food", "culture", "education", "cooking"]},
            {"name": "Tham quan Rừng Dừa Bảy Mẫu", "desc": "Trải nghiệm ngồi thúng và múa thúng", "cost": 150000, "time": 120, "tags": ["nature", "adventure", "fun", "boat"]},
            {"name": "Tắm biển Cửa Đại/An Bàng", "desc": "Thư giãn trên bãi biển", "cost": 0, "time": 180, "tags": ["beach", "relax", "swimming"]},
        ]
    },
    "Hạ Long": {
        "name": "Hạ Long",
        "tags": ["sea", "nature", "cruise", "adventure", "island"],
        "activities": [
            {"name": "Tour du thuyền Vịnh Hạ Long", "desc": "Ngắm hòn đảo đá vôi và thưởng thức hải sản", "cost": 800000, "time": 240, "tags": ["sea", "nature", "relax", "cruise", "sightseeing"]},
            {"name": "Chèo Kayak trên Vịnh", "desc": "Tự do chèo thuyền kayak đến gần hang động", "cost": 200000, "time": 90, "tags": ["adventure", "sea", "sports", "kayak"]},
            {"name": "Thăm Động Thiên Cung", "desc": "Tham quan hang động tự nhiên với nhũ đá tuyệt đẹp", "cost": 100000, "time": 60, "tags": ["nature", "sightseeing", "cave", "geology"]},
            {"name": "Vui chơi tại Sun World", "desc": "Chơi các trò mạo hiểm và đi cáp treo", "cost": 450000, "time": 240, "tags": ["fun", "entertainment", "theme_park"]},
            {"name": "Tắm biển Bãi Cháy", "desc": "Tắm biển và thưởng ngoạn hoàng hôn", "cost": 0, "time": 120, "tags": ["beach", "relax", "swimming"]},
        ]
    },
    "Hà Giang": {
        "name": "Hà Giang",
        "tags": ["mountain", "nature", "adventure", "culture", "motorbiking"],
        "activities": [
            {"name": "Lái xe máy đèo Mã Pí Lèng", "desc": "Trải nghiệm cung đường đèo hùng vĩ nhất Việt Nam", "cost": 250000, "time": 180, "tags": ["adventure", "motorbiking", "nature", "scenic"]},
            {"name": "Đi thuyền trên sông Nho Quế", "desc": "Ngắm vực Tu Sản dưới chân đèo Mã Pí Lèng", "cost": 120000, "time": 120, "tags": ["nature", "relax", "photography", "canyon"]},
            {"name": "Tham quan Dinh Vua Mèo", "desc": "Tìm hiểu gia tộc họ Vương và lịch sử vùng cao", "cost": 30000, "time": 60, "tags": ["culture", "history", "architecture"]},
            {"name": "Check-in Cột cờ Lũng Cú", "desc": "Chinh phục điểm cực Bắc Tổ quốc", "cost": 40000, "time": 90, "tags": ["sightseeing", "history", "patriotic", "hiking"]},
            {"name": "Chơi chợ phiên Đồng Văn", "desc": "Tham quan và thưởng thức thắng cố, rượu ngô", "cost": 100000, "time": 120, "tags": ["culture", "food", "market", "ethnic"]},
            {"name": "Ngắm lúa chín Hoàng Su Phì", "desc": "Chụp ảnh tại ruộng bậc thang ngút ngàn", "cost": 50000, "time": 150, "tags": ["nature", "photography", "rice_terrace", "scenic"]},
        ]
    },
    "Nha Trang": {
        "name": "Nha Trang",
        "tags": ["beach", "sea", "entertainment", "relax", "diving"],
        "activities": [
            {"name": "Chơi VinWonders", "desc": "Khu vui chơi giải trí trên đảo Hòn Tre", "cost": 800000, "time": 360, "tags": ["fun", "entertainment", "family", "theme_park"]},
            {"name": "Tour 3 đảo", "desc": "Tham quan Hòn Mun, Hòn Tằm, trải nghiệm lặn biển", "cost": 500000, "time": 420, "tags": ["sea", "adventure", "nature", "island"]},
            {"name": "Tắm bùn khoáng tháp Bà", "desc": "Thư giãn với bùn khoáng nóng", "cost": 250000, "time": 120, "tags": ["relax", "health", "spa", "wellness"]},
            {"name": "Tham quan Tháp Bà Ponagar", "desc": "Khám phá kiến trúc đền tháp Chăm cổ", "cost": 30000, "time": 60, "tags": ["culture", "history", "architecture", "temple"]},
            {"name": "Thưởng thức hải sản bãi biển", "desc": "Ăn tôm hùm, nhum biển với giá hợp lý", "cost": 500000, "time": 90, "tags": ["food", "seafood", "local_food"]},
        ]
    },
    "Huế": {
        "name": "Huế",
        "tags": ["culture", "history", "food", "architecture", "relax", "heritage"],
        "activities": [
            {"name": "Tham quan Đại Nội Huế", "desc": "Khám phá hoàng cung của vua triều Nguyễn", "cost": 200000, "time": 180, "tags": ["history", "culture", "architecture", "heritage"]},
            {"name": "Thăm Lăng tẩm các vua Nguyễn", "desc": "Tham quan lăng Khải Định, Minh Mạng, Tự Đức", "cost": 150000, "time": 180, "tags": ["history", "culture", "architecture", "royal"]},
            {"name": "Nghe Nhã nhạc cung đình Huế", "desc": "Đi thuyền rồng trên sông Hương và thưởng thức nhã nhạc", "cost": 100000, "time": 90, "tags": ["culture", "music", "relax", "heritage"]},
            {"name": "Thưởng thức bún bò Huế & các loại bánh", "desc": "Ăn uống tại quán địa phương", "cost": 80000, "time": 60, "tags": ["food", "culture", "local_food", "cuisine"]},
            {"name": "Tham quan chùa Thiên Mụ", "desc": "Vãn cảnh ngôi chùa cổ kính bên sông Hương", "cost": 0, "time": 60, "tags": ["culture", "history", "sightseeing", "temple"]},
            {"name": "Đạp xe tham quan làng Thủy Biều", "desc": "Trải nghiệm làm thanh trà, nấu ăn và massage chân", "cost": 300000, "time": 180, "tags": ["nature", "culture", "relax", "cycling"]},
        ]
    },
}


def _build_activity_templates() -> Dict[str, Any]:
    """
    Xây dựng ACTIVITY_TEMPLATES từ nguồn dữ liệu tốt nhất có sẵn.
    
    Ưu tiên:
      1. Load từ activities.json (schema v2, đầy đủ 100+ activities)
      2. Fallback về _FALLBACK_TEMPLATES nếu JSON không tồn tại
    
    Kết quả được cache ở module level (ACTIVITY_TEMPLATES).
    """
    json_activities = load_activities_from_json()
    
    if json_activities:
        templates = group_activities_by_location(json_activities)
        logger.info(
            f"Loaded {len(json_activities)} activities cho {len(templates)} locations từ JSON"
        )
        return templates
    else:
        logger.info("Sử dụng fallback templates (hardcoded)")
        return _FALLBACK_TEMPLATES


# Module-level constant: dùng bởi n5_activity_generator.py
ACTIVITY_TEMPLATES: Dict[str, Any] = _build_activity_templates()


# ===========================================================================
# TIỆN ÍCH: Lấy danh sách tất cả locations, activities, thống kê
# ===========================================================================

def get_all_location_names() -> List[str]:
    """Trả về danh sách tên tất cả locations có trong templates."""
    return list(ACTIVITY_TEMPLATES.keys())


def get_activities_for_location(location_name: str) -> List[Dict]:
    """Trả về danh sách activities cho một location cụ thể."""
    template = ACTIVITY_TEMPLATES.get(location_name, {})
    return template.get("activities", [])


def get_total_activity_count() -> int:
    """Đếm tổng số activities trên tất cả locations."""
    total = 0
    for loc_data in ACTIVITY_TEMPLATES.values():
        total += len(loc_data.get("activities", []))
    return total


def get_stats() -> Dict:
    """
    Thống kê tổng quan về database activities.
    
    Returns:
        Dict với các key: total_locations, total_activities, locations_detail
    """
    stats = {
        "total_locations": len(ACTIVITY_TEMPLATES),
        "total_activities": 0,
        "locations_detail": {}
    }
    
    for loc_name, loc_data in ACTIVITY_TEMPLATES.items():
        count = len(loc_data.get("activities", []))
        stats["total_activities"] += count
        stats["locations_detail"][loc_name] = {
            "activity_count": count,
            "tags": loc_data.get("tags", []),
        }
    
    return stats


# ===========================================================================
# LOCATION_PROFILES: Đặc trưng từng địa điểm
# Dùng bởi n5_activity_generator._get_profile()
# Keys bắt buộc: tags, description, best_season, indoor_ratio, price_range, region
# ===========================================================================
LOCATION_PROFILES: Dict[str, Any] = {
    "Sa Pa": {
        "tags": ["mountain", "trekking", "nature", "cool_weather", "photography", "culture", "ethnic", "scenic", "rice_terrace"],
        "description": "Thị trấn vùng cao Sa Pa với ruộng bậc thang hùng vĩ và văn hóa dân tộc phong phú",
        "best_season": ["sep", "oct", "nov", "mar", "apr"],
        "indoor_ratio": 0.2,
        "price_range": (50_000, 800_000),
        "region": "northwest",
    },
    "Phú Quốc": {
        "tags": ["beach", "sea", "resort", "relax", "island", "diving", "seafood", "snorkeling"],
        "description": "Đảo ngọc Phú Quốc với bãi biển trong xanh và hải sản tươi ngon",
        "best_season": ["nov", "dec", "jan", "feb", "mar", "apr"],
        "indoor_ratio": 0.15,
        "price_range": (50_000, 1_200_000),
        "region": "south",
    },
    "Đà Lạt": {
        "tags": ["mountain", "cool_weather", "flower", "nature", "romantic", "photography", "trekking", "scenic"],
        "description": "Thành phố ngàn hoa Đà Lạt với khí hậu mát mẻ và cảnh quan thơ mộng",
        "best_season": ["dec", "jan", "feb", "mar", "nov"],
        "indoor_ratio": 0.25,
        "price_range": (50_000, 600_000),
        "region": "central_highlands",
    },
    "Hội An": {
        "tags": ["culture", "history", "food", "photography", "heritage", "relax", "beach", "architecture"],
        "description": "Phố cổ Hội An với kiến trúc đặc sắc và ẩm thực phong phú",
        "best_season": ["feb", "mar", "apr", "may"],
        "indoor_ratio": 0.35,
        "price_range": (50_000, 1_000_000),
        "region": "central",
    },
    "Hạ Long": {
        "tags": ["sea", "nature", "cruise", "adventure", "island", "cave", "kayak", "scenic"],
        "description": "Vịnh Hạ Long với ngàn hòn đảo đá vôi và những hang động kỳ bí",
        "best_season": ["mar", "apr", "may", "sep", "oct", "nov"],
        "indoor_ratio": 0.1,
        "price_range": (100_000, 1_500_000),
        "region": "northeast",
    },
    "Hà Giang": {
        "tags": ["mountain", "nature", "adventure", "culture", "motorbiking", "scenic", "ethnic", "trekking", "canyon", "rice_terrace"],
        "description": "Cao nguyên đá Hà Giang hoang sơ với đèo Mã Pí Lèng hùng vĩ",
        "best_season": ["sep", "oct", "nov", "mar", "apr"],
        "indoor_ratio": 0.15,
        "price_range": (30_000, 500_000),
        "region": "northeast",
    },
    "Nha Trang": {
        "tags": ["beach", "sea", "entertainment", "relax", "diving", "seafood", "island", "snorkeling"],
        "description": "Thành phố biển Nha Trang với bãi biển xanh và các khu vui chơi sầm uất",
        "best_season": ["jan", "feb", "mar", "apr", "jun", "jul", "aug"],
        "indoor_ratio": 0.2,
        "price_range": (50_000, 1_000_000),
        "region": "central",
    },
    "Huế": {
        "tags": ["culture", "history", "food", "architecture", "heritage", "relax", "scenic"],
        "description": "Cố đô Huế với hệ thống lăng tẩm, đền đài và ẩm thực cung đình tinh tế",
        "best_season": ["feb", "mar", "apr", "may"],
        "indoor_ratio": 0.30,
        "price_range": (30_000, 500_000),
        "region": "central",
    },
    "Đà Nẵng": {
        "tags": ["beach", "sea", "culture", "food", "urban", "relax", "photography", "scenic"],
        "description": "Thành phố đáng sống Đà Nẵng với bãi biển Mỹ Khê và cầu Rồng nổi tiếng",
        "best_season": ["feb", "mar", "apr", "may", "jun", "jul", "aug"],
        "indoor_ratio": 0.25,
        "price_range": (50_000, 800_000),
        "region": "central",
    },
    "Phong Nha": {
        "tags": ["cave", "nature", "adventure", "trekking", "river", "jungle", "scenic"],
        "description": "Vườn quốc gia Phong Nha - Kẻ Bàng với hệ thống hang động lớn nhất thế giới",
        "best_season": ["feb", "mar", "apr", "may", "jun", "jul", "aug"],
        "indoor_ratio": 0.05,
        "price_range": (50_000, 800_000),
        "region": "central",
    },
}


# ===========================================================================
# SIGHTSEEING_BOOST_TAGS: Tags nào tăng điểm sightseeing_priority cho template
# Dùng bởi n5_activity_generator._score_templates_for_location()
# ===========================================================================
SIGHTSEEING_BOOST_TAGS: Dict[str, float] = {
    "mountain":    0.20,
    "nature":      0.15,
    "waterfall":   0.20,
    "scenic":      0.15,
    "photography": 0.10,
    "beach":       0.10,
    "sea":         0.10,
    "island":      0.10,
    "trekking":    0.10,
    "cave":        0.15,
    "rice_terrace": 0.20,
    "canyon":      0.20,
    "cool_weather": 0.05,
    "flower":      0.10,
    "river":       0.10,
    "jungle":      0.10,
    "forest":      0.10,
    "landscape":   0.15,
    "motorbiking": 0.05,
    "cruise":      0.10,
}


# ===========================================================================
# VARIATION_MODIFIERS: Tạo biến thể activities để đạt đủ 100/location
# Dùng bởi n5_activity_generator._expand_templates()
# Keys bắt buộc: suffix, desc_prefix, time_of_day_suitable
# ===========================================================================
VARIATION_MODIFIERS: List[Dict[str, Any]] = [
    {
        "suffix": "buổi sáng sớm",
        "desc_prefix": "Bắt đầu ngày mới tuyệt vời: ",
        "time_of_day_suitable": "morning",
    },
    {
        "suffix": "cùng bạn bè",
        "desc_prefix": "Cùng bạn bè tận hưởng: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "hoàng hôn",
        "desc_prefix": "Tận hưởng buổi chiều tà với: ",
        "time_of_day_suitable": "afternoon",
    },
    {
        "suffix": "phiên bản VIP",
        "desc_prefix": "Trải nghiệm đẳng cấp cao cấp: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "cho người mới",
        "desc_prefix": "Hoàn toàn phù hợp cho người mới: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "cùng gia đình",
        "desc_prefix": "Trải nghiệm ý nghĩa bên gia đình: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "ban đêm",
        "desc_prefix": "Khám phá vẻ đẹp huyền ảo về đêm: ",
        "time_of_day_suitable": "night",
    },
    {
        "suffix": "hidden gem",
        "desc_prefix": "Bí mật chỉ dành riêng cho bạn: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "có hướng dẫn viên",
        "desc_prefix": "Khám phá chuyên sâu cùng hướng dẫn viên địa phương: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "thư giãn",
        "desc_prefix": "Phiên bản nhẹ nhàng, thư thái: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "mạo hiểm",
        "desc_prefix": "Thử thách bản thân với phiên bản mạo hiểm: ",
        "time_of_day_suitable": None,
    },
    {
        "suffix": "solo",
        "desc_prefix": "Tự do khám phá theo cách của riêng bạn: ",
        "time_of_day_suitable": None,
    },
]


# ===========================================================================
# ACTIVITY_TYPE_BANK: Template bank theo loại hoạt động
# Dùng bởi n5_activity_generator._expand_templates()
#
# Mỗi template cần đủ các keys:
#   name_template, description_template, activity_type, activity_subtype,
#   compatible_location_tags, duration_range, price_level_range [1.0-5.0],
#   indoor_outdoor, weather_dependent, time_of_day_suitable, sightseeing_priority
# ===========================================================================
ACTIVITY_TYPE_BANK: Dict[str, List[Dict[str, Any]]] = {

    # ── NATURE (sightseeing_priority cao: 0.75-0.95) ──────────────────────
    "nature": [
        {
            "name_template": "Trekking ngắm cảnh tại {location}",
            "description_template": "Khám phá vẻ đẹp thiên nhiên hoang sơ tại {location} qua những cung đường trekking tuyệt đẹp. Hít thở không khí trong lành và chiêm ngưỡng phong cảnh hùng vĩ trải dài trước mắt.",
            "activity_type": "nature",
            "activity_subtype": "nature_walk",
            "compatible_location_tags": ["mountain", "nature", "trekking", "jungle", "forest", "scenic"],
            "duration_range": [120, 240],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.85,
        },
        {
            "name_template": "Ngắm bình minh tại {location}",
            "description_template": "Thức dậy sớm để chiêm ngưỡng khoảnh khắc bình minh kỳ diệu tại {location}. Ánh nắng đầu ngày chiếu rọi trên núi đồi tạo nên cảnh tượng không thể quên.",
            "activity_type": "nature",
            "activity_subtype": "sunrise_viewing",
            "compatible_location_tags": ["mountain", "nature", "photography", "scenic", "beach", "sea", "cool_weather"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 1.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.95,
        },
        {
            "name_template": "Ngắm hoàng hôn tại {location}",
            "description_template": "Tận hưởng khoảnh khắc hoàng hôn tuyệt đẹp tại {location} khi mặt trời từ từ lặn xuống chân trời. Bầu trời nhuốm sắc cam hồng tạo nên bức tranh thiên nhiên sống động.",
            "activity_type": "nature",
            "activity_subtype": "sunset_viewing",
            "compatible_location_tags": ["mountain", "nature", "photography", "scenic", "beach", "sea", "island", "cool_weather"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 1.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "afternoon",
            "sightseeing_priority": 0.95,
        },
        {
            "name_template": "Chụp ảnh phong cảnh {location}",
            "description_template": "Khám phá những góc chụp đẹp nhất tại {location} cùng camera. Từ ruộng bậc thang, thác nước đến bãi biển — mỗi khoảnh khắc là một tác phẩm nghệ thuật.",
            "activity_type": "nature",
            "activity_subtype": "landscape_photography",
            "compatible_location_tags": ["nature", "photography", "mountain", "scenic", "beach", "flower", "rice_terrace", "cool_weather"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.90,
        },
        {
            "name_template": "Khám phá hang động tại {location}",
            "description_template": "Bước vào thế giới kỳ ảo của những hang động tự nhiên tại {location}. Những nhũ đá, măng đá triệu năm tuổi tạo nên cảnh quan choáng ngợp dưới lòng đất.",
            "activity_type": "nature",
            "activity_subtype": "viewpoint",
            "compatible_location_tags": ["cave", "nature", "adventure", "trekking", "river"],
            "duration_range": [60, 180],
            "price_level_range": [1.5, 3.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.85,
        },
        {
            "name_template": "Ngắm cảnh panorama {location}",
            "description_template": "Leo lên điểm nhìn panorama để chiêm ngưỡng toàn cảnh {location} trải rộng bao la. Tầm mắt không giới hạn ôm trọn núi đồi, sông suối và bầu trời xanh thẳm.",
            "activity_type": "nature",
            "activity_subtype": "panorama_viewpoint",
            "compatible_location_tags": ["mountain", "scenic", "photography", "trekking", "nature", "canyon"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.95,
        },
        {
            "name_template": "Đi thuyền ngắm cảnh {location}",
            "description_template": "Thong thả trôi trên mặt nước ngắm nhìn cảnh quan tuyệt vời của {location} từ góc độ hoàn toàn khác. Gió mát và khung cảnh hùng vĩ hai bên bờ mang lại cảm giác bình yên.",
            "activity_type": "nature",
            "activity_subtype": "boat_sightseeing",
            "compatible_location_tags": ["sea", "river", "island", "cave", "kayak", "cruise", "scenic"],
            "duration_range": [90, 240],
            "price_level_range": [2.0, 4.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.90,
        },
        {
            "name_template": "Khám phá thiên nhiên hoang dã {location}",
            "description_template": "Hòa mình vào thiên nhiên nguyên sơ tại {location}, quan sát động thực vật bản địa trong môi trường tự nhiên. Trải nghiệm eco-tour thân thiện với môi trường.",
            "activity_type": "nature",
            "activity_subtype": "eco_tour",
            "compatible_location_tags": ["nature", "jungle", "forest", "trekking", "mountain", "river"],
            "duration_range": [120, 300],
            "price_level_range": [1.5, 3.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.80,
        },
        {
            "name_template": "Ngắm ruộng bậc thang {location}",
            "description_template": "Chiêm ngưỡng những thửa ruộng bậc thang xếp tầng kỳ vĩ tại {location} — kiệt tác nghệ thuật của người nông dân vùng cao. Màu sắc thay đổi theo mùa tạo nên vẻ đẹp độc đáo.",
            "activity_type": "nature",
            "activity_subtype": "scenic_walk",
            "compatible_location_tags": ["rice_terrace", "mountain", "nature", "photography", "scenic", "ethnic"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.92,
        },
        {
            "name_template": "Ngắm cảnh từ đỉnh núi {location}",
            "description_template": "Chinh phục độ cao để đứng trên đỉnh núi {location} nhìn xuống toàn bộ thung lũng bên dưới. Cảm giác tự do và hùng vĩ chỉ có được khi đứng trên đỉnh cao.",
            "activity_type": "nature",
            "activity_subtype": "nature_photography",
            "compatible_location_tags": ["mountain", "scenic", "trekking", "nature", "canyon", "cool_weather"],
            "duration_range": [180, 360],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.90,
        },
    ],

    # ── ADVENTURE (sightseeing_priority thấp: 0.25-0.45) ──────────────────
    "adventure": [
        {
            "name_template": "Leo núi chinh phục đỉnh cao {location}",
            "description_template": "Thử thách bản thân với cung đường leo núi mạo hiểm tại {location}. Chinh phục đỉnh cao và cảm nhận niềm vui chiến thắng khi đứng trên đỉnh hùng vĩ.",
            "activity_type": "adventure",
            "activity_subtype": "hiking",
            "compatible_location_tags": ["mountain", "trekking", "adventure", "nature", "cool_weather"],
            "duration_range": [240, 480],
            "price_level_range": [2.0, 4.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.40,
        },
        {
            "name_template": "Chèo kayak khám phá {location}",
            "description_template": "Trải nghiệm cảm giác mạnh khi chèo kayak trên mặt nước tại {location}. Khám phá những ngóc ngách ẩn mình và tận hưởng cảm giác tự do trên sóng nước.",
            "activity_type": "adventure",
            "activity_subtype": "kayaking",
            "compatible_location_tags": ["sea", "river", "kayak", "island", "cave", "adventure"],
            "duration_range": [90, 180],
            "price_level_range": [2.0, 3.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.30,
        },
        {
            "name_template": "Lặn biển ngắm san hô tại {location}",
            "description_template": "Khám phá thế giới dưới nước đầy màu sắc tại {location}. Lặn ngắm san hô và đàn cá nhiều màu sắc trong làn nước trong xanh tuyệt đẹp.",
            "activity_type": "adventure",
            "activity_subtype": "snorkeling",
            "compatible_location_tags": ["sea", "beach", "diving", "island", "snorkeling"],
            "duration_range": [120, 240],
            "price_level_range": [2.5, 4.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.25,
        },
        {
            "name_template": "Đi xe máy khám phá {location}",
            "description_template": "Tự do khám phá {location} trên yên xe máy qua những cung đường uốn lượn hùng vĩ. Cảm nhận gió mát và tự tạo hành trình theo ý muốn của mình.",
            "activity_type": "adventure",
            "activity_subtype": "motorbiking",
            "compatible_location_tags": ["mountain", "motorbiking", "adventure", "scenic", "trekking", "canyon"],
            "duration_range": [180, 360],
            "price_level_range": [1.5, 3.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.40,
        },
        {
            "name_template": "Cắm trại dưới sao {location}",
            "description_template": "Trải nghiệm đêm nằm ngủ dưới bầu trời đầy sao tại {location}. Nướng BBQ, hát hò bên lửa trại và ngắm Milky Way trong đêm yên tĩnh.",
            "activity_type": "adventure",
            "activity_subtype": "camping",
            "compatible_location_tags": ["mountain", "nature", "adventure", "trekking", "jungle", "scenic"],
            "duration_range": [360, 480],
            "price_level_range": [2.0, 3.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.35,
        },
        {
            "name_template": "Thám hiểm hang động {location}",
            "description_template": "Phiêu lưu vào lòng hang động bí ẩn tại {location}. Vượt qua những thách thức địa hình và khám phá vẻ đẹp ẩn sâu trong lòng đất.",
            "activity_type": "adventure",
            "activity_subtype": "cave_exploration",
            "compatible_location_tags": ["cave", "adventure", "nature", "trekking", "river"],
            "duration_range": [120, 300],
            "price_level_range": [2.5, 4.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.30,
        },
        {
            "name_template": "Tắm thác nước tại {location}",
            "description_template": "Tìm đến những thác nước hoang sơ tại {location} để tắm mát và thư giãn. Tiếng nước chảy rì rào và màu xanh trong vắt của nước tạo cảm giác sảng khoái.",
            "activity_type": "adventure",
            "activity_subtype": "waterfall_visit",
            "compatible_location_tags": ["waterfall", "nature", "mountain", "trekking", "jungle", "adventure"],
            "duration_range": [120, 240],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.45,
        },
    ],

    # ── RELAXATION (sightseeing_priority trung bình: 0.10-0.60) ───────────
    "relaxation": [
        {
            "name_template": "Thư giãn tắm biển tại {location}",
            "description_template": "Tắm mình trong làn nước biển mát lành tại {location}. Nằm dài trên bãi cát trắng mịn, nghe sóng vỗ và tận hưởng cảm giác bình yên tuyệt đối.",
            "activity_type": "relaxation",
            "activity_subtype": "beach_relaxation",
            "compatible_location_tags": ["beach", "sea", "relax", "island", "resort"],
            "duration_range": [120, 300],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.50,
        },
        {
            "name_template": "Trải nghiệm spa và massage tại {location}",
            "description_template": "Thả lỏng cơ thể với dịch vụ spa cao cấp tại {location}. Được xoa bóp bằng tinh dầu thảo mộc địa phương và tận hưởng cảm giác thư thái từ đầu đến chân.",
            "activity_type": "relaxation",
            "activity_subtype": "spa_massage",
            "compatible_location_tags": ["resort", "relax", "health", "beach", "sea", "cool_weather"],
            "duration_range": [60, 120],
            "price_level_range": [2.5, 4.5],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "afternoon",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Cà phê ngắm cảnh {location}",
            "description_template": "Ngồi thư giãn tại quán cà phê view đẹp nhất {location}, nhâm nhi ly cà phê thơm ngon trong khi chiêm ngưỡng cảnh quan tuyệt vời xung quanh.",
            "activity_type": "relaxation",
            "activity_subtype": "scenic_walk",
            "compatible_location_tags": ["nature", "mountain", "scenic", "photography", "relax", "cool_weather", "beach", "culture"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.60,
        },
        {
            "name_template": "Yoga và thiền định tại {location}",
            "description_template": "Bắt đầu ngày mới với buổi tập yoga và thiền định trong không gian thiên nhiên bình yên của {location}. Cân bằng tâm thân giữa không khí trong lành.",
            "activity_type": "relaxation",
            "activity_subtype": "nature_walk",
            "compatible_location_tags": ["nature", "mountain", "resort", "relax", "health", "beach", "cool_weather"],
            "duration_range": [60, 90],
            "price_level_range": [1.5, 3.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": True,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.45,
        },
        {
            "name_template": "Dạo bộ buổi tối tại {location}",
            "description_template": "Thư thái dạo bộ qua những con phố đêm lung linh của {location}. Ngắm nhìn cuộc sống về đêm và tận hưởng bầu không khí dễ chịu sau hoàng hôn.",
            "activity_type": "relaxation",
            "activity_subtype": "scenic_walk",
            "compatible_location_tags": ["culture", "urban", "food", "relax", "beach", "heritage"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 1.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.55,
        },
        {
            "name_template": "Nghỉ dưỡng resort {location}",
            "description_template": "Tận hưởng kỳ nghỉ sang trọng tại resort cao cấp của {location} với hồ bơi, bãi biển riêng và dịch vụ 5 sao. Quên đi mọi lo toan trong không gian đẳng cấp.",
            "activity_type": "relaxation",
            "activity_subtype": "beach_relaxation",
            "compatible_location_tags": ["resort", "beach", "sea", "relax", "island", "entertainment"],
            "duration_range": [240, 480],
            "price_level_range": [3.5, 5.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.20,
        },
    ],

    # ── CULTURE (sightseeing_priority trung bình: 0.20-0.70) ──────────────
    "culture": [
        {
            "name_template": "Tham quan đền chùa cổ tại {location}",
            "description_template": "Khám phá kiến trúc cổ kính và tâm linh sâu sắc tại những ngôi đền, chùa linh thiêng nhất {location}. Hiểu thêm về lịch sử và văn hóa địa phương qua từng viên gạch.",
            "activity_type": "culture",
            "activity_subtype": "temple_visit",
            "compatible_location_tags": ["culture", "history", "heritage", "architecture", "temple", "spiritual"],
            "duration_range": [60, 180],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.65,
        },
        {
            "name_template": "Khám phá phố cổ {location}",
            "description_template": "Đắm chìm trong không khí cổ kính của phố cổ {location} với những con đường nhỏ lát đá và các cửa hiệu thủ công mỹ nghệ truyền thống. Mỗi góc phố là một câu chuyện lịch sử.",
            "activity_type": "culture",
            "activity_subtype": "heritage_walk",
            "compatible_location_tags": ["culture", "history", "heritage", "photography", "architecture"],
            "duration_range": [90, 240],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.70,
        },
        {
            "name_template": "Tham quan bảo tàng lịch sử {location}",
            "description_template": "Tìm hiểu chiều sâu lịch sử và văn hóa {location} qua các hiện vật và triển lãm tại bảo tàng. Mở rộng kiến thức và hiểu thêm về vùng đất đang khám phá.",
            "activity_type": "culture",
            "activity_subtype": "museum_visit",
            "compatible_location_tags": ["culture", "history", "heritage", "education", "architecture"],
            "duration_range": [60, 150],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.50,
        },
        {
            "name_template": "Học nấu ăn đặc sản {location}",
            "description_template": "Học làm các món ăn đặc trưng của {location} cùng đầu bếp địa phương. Tự tay chế biến và thưởng thức thành quả — trải nghiệm văn hóa ẩm thực sâu sắc nhất.",
            "activity_type": "culture",
            "activity_subtype": "cooking_class",
            "compatible_location_tags": ["culture", "food", "education", "tradition", "heritage"],
            "duration_range": [120, 240],
            "price_level_range": [3.0, 4.5],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.20,
        },
        {
            "name_template": "Gặp gỡ người dân bản địa {location}",
            "description_template": "Tham quan bản làng và giao lưu với người dân địa phương tại {location}. Tìm hiểu phong tục tập quán, nghề truyền thống và cuộc sống thường ngày của họ.",
            "activity_type": "culture",
            "activity_subtype": "village_visit",
            "compatible_location_tags": ["culture", "ethnic", "village", "tradition", "mountain", "heritage"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.55,
        },
        {
            "name_template": "Xem biểu diễn nghệ thuật truyền thống {location}",
            "description_template": "Thưởng thức các tiết mục nghệ thuật truyền thống đặc sắc của {location}: âm nhạc dân gian, múa cổ truyền và các hình thức biểu diễn độc đáo của địa phương.",
            "activity_type": "culture",
            "activity_subtype": "cultural_performance",
            "compatible_location_tags": ["culture", "history", "heritage", "music", "art", "tradition"],
            "duration_range": [60, 120],
            "price_level_range": [1.5, 3.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.45,
        },
    ],

    # ── FOOD (sightseeing_priority thấp: 0.10-0.25) ───────────────────────
    "food": [
        {
            "name_template": "Khám phá ẩm thực đường phố {location}",
            "description_template": "Dạo quanh các con phố để thưởng thức những món ăn đường phố ngon nổi tiếng của {location}. Từ gánh hàng rong đến quán nhỏ ven đường, mỗi góc phố là một hương vị riêng.",
            "activity_type": "food",
            "activity_subtype": "street_food_tour",
            "compatible_location_tags": ["food", "culture", "urban", "market", "tradition", "heritage"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "outdoor",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.15,
        },
        {
            "name_template": "Thưởng thức hải sản tươi sống {location}",
            "description_template": "Thưởng thức hải sản tươi ngon nhất của {location} tại các nhà hàng ven biển. Tôm hùm, cua, ốc, cá được chế biến đặc trưng theo phong cách địa phương.",
            "activity_type": "food",
            "activity_subtype": "seafood_dining",
            "compatible_location_tags": ["sea", "beach", "food", "seafood", "island"],
            "duration_range": [90, 150],
            "price_level_range": [3.0, 5.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "afternoon",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Thử món đặc sản địa phương {location}",
            "description_template": "Khám phá kho tàng ẩm thực phong phú của {location} qua các món đặc sản chỉ có tại đây. Những hương vị độc đáo sẽ để lại ấn tượng khó quên trong chuyến đi.",
            "activity_type": "food",
            "activity_subtype": "local_cuisine",
            "compatible_location_tags": ["food", "culture", "tradition", "heritage", "ethnic"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 3.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Tham quan chợ địa phương {location}",
            "description_template": "Khám phá chợ địa phương sôi động của {location}, nơi người dân bày bán đủ loại nông sản, gia vị và đặc sản vùng. Trải nghiệm văn hóa chợ búa truyền thống.",
            "activity_type": "food",
            "activity_subtype": "market_visit",
            "compatible_location_tags": ["food", "culture", "market", "tradition", "ethnic", "village"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 2.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.20,
        },
        {
            "name_template": "Trải nghiệm nhà hàng đặc sắc {location}",
            "description_template": "Thưởng thức bữa ăn tại nhà hàng nổi tiếng của {location} với không gian thiết kế đẹp và menu phong phú kết hợp hương vị địa phương và hiện đại.",
            "activity_type": "food",
            "activity_subtype": "restaurant_dining",
            "compatible_location_tags": ["food", "culture", "relax", "heritage", "beach", "urban"],
            "duration_range": [60, 120],
            "price_level_range": [2.5, 5.0],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "afternoon",
            "sightseeing_priority": 0.10,
        },
    ],

    # ── NIGHTLIFE (sightseeing_priority thấp: 0.10-0.40) ──────────────────
    "nightlife": [
        {
            "name_template": "Trải nghiệm bar đêm {location}",
            "description_template": "Trải nghiệm cuộc sống về đêm sôi động của {location} tại các bar và pub nổi tiếng. Âm nhạc sống động, cocktail thơm ngon và không khí cuồng nhiệt.",
            "activity_type": "nightlife",
            "activity_subtype": "bar_pub",
            "compatible_location_tags": ["nightlife", "entertainment", "urban", "beach", "sea", "fun"],
            "duration_range": [120, 300],
            "price_level_range": [2.5, 4.5],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Ngắm thành phố về đêm {location}",
            "description_template": "Leo lên điểm cao nhất ngắm nhìn {location} lấp lánh ánh đèn về đêm. Vẻ đẹp lung linh của thành phố về đêm là trải nghiệm không thể bỏ qua khi đến đây.",
            "activity_type": "nightlife",
            "activity_subtype": "city_lights_view",
            "compatible_location_tags": ["urban", "photography", "culture", "scenic", "mountain", "beach"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.40,
        },
        {
            "name_template": "Tham quan chợ đêm {location}",
            "description_template": "Dạo quanh chợ đêm sầm uất của {location} để mua sắm, thưởng thức đồ ăn vặt và tận hưởng không khí đêm đặc trưng. Nhiều món ăn ngon và quà lưu niệm hấp dẫn.",
            "activity_type": "nightlife",
            "activity_subtype": "night_market",
            "compatible_location_tags": ["food", "shopping", "culture", "nightlife", "entertainment", "urban"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 2.5],
            "indoor_outdoor": "outdoor",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.20,
        },
        {
            "name_template": "Show âm nhạc biểu diễn đêm {location}",
            "description_template": "Tận hưởng đêm nhạc sống tại các tụ điểm văn nghệ của {location}. Tiết mục đặc sắc kết hợp giữa âm nhạc truyền thống và hiện đại trong không gian ấm cúng.",
            "activity_type": "nightlife",
            "activity_subtype": "live_music",
            "compatible_location_tags": ["entertainment", "music", "culture", "nightlife", "urban"],
            "duration_range": [90, 180],
            "price_level_range": [2.0, 4.0],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "night",
            "sightseeing_priority": 0.15,
        },
    ],

    # ── SHOPPING (sightseeing_priority rất thấp: 0.05-0.25) ───────────────
    "shopping": [
        {
            "name_template": "Mua đồ lưu niệm thủ công {location}",
            "description_template": "Chọn lựa những món quà lưu niệm thủ công mang đặc trưng {location} tại các cửa hàng và chợ địa phương. Mỗi món đồ là một tác phẩm nghệ thuật độc đáo.",
            "activity_type": "shopping",
            "activity_subtype": "souvenir_shopping",
            "compatible_location_tags": ["culture", "shopping", "craft", "art", "tradition", "heritage"],
            "duration_range": [60, 120],
            "price_level_range": [1.5, 3.5],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Mua đặc sản địa phương {location}",
            "description_template": "Tìm mua những đặc sản nổi tiếng của {location} để làm quà hoặc thưởng thức. Từ thực phẩm chế biến, gia vị đến đồ uống đặc trưng của vùng.",
            "activity_type": "shopping",
            "activity_subtype": "local_products",
            "compatible_location_tags": ["food", "culture", "tradition", "market", "ethnic"],
            "duration_range": [60, 120],
            "price_level_range": [1.0, 3.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "anytime",
            "sightseeing_priority": 0.10,
        },
        {
            "name_template": "Khám phá làng nghề thủ công {location}",
            "description_template": "Thăm các làng nghề truyền thống tại {location} để xem thợ thủ công làm việc và mua trực tiếp sản phẩm chất lượng. Hiểu hơn về nghề thủ công bản địa.",
            "activity_type": "shopping",
            "activity_subtype": "craft_village",
            "compatible_location_tags": ["culture", "craft", "art", "tradition", "heritage", "village", "ethnic"],
            "duration_range": [90, 180],
            "price_level_range": [1.0, 3.0],
            "indoor_outdoor": "mixed",
            "weather_dependent": False,
            "time_of_day_suitable": "morning",
            "sightseeing_priority": 0.25,
        },
        {
            "name_template": "Shopping trung tâm thương mại {location}",
            "description_template": "Tham quan và mua sắm tại trung tâm thương mại hiện đại nhất {location}. Nhiều thương hiệu quốc tế và địa phương, khu ẩm thực và giải trí đa dạng.",
            "activity_type": "shopping",
            "activity_subtype": "mall_shopping",
            "compatible_location_tags": ["shopping", "entertainment", "urban", "food", "fun"],
            "duration_range": [120, 240],
            "price_level_range": [2.0, 5.0],
            "indoor_outdoor": "indoor",
            "weather_dependent": False,
            "time_of_day_suitable": "afternoon",
            "sightseeing_priority": 0.05,
        },
    ],
}


# ===========================================================================
# CHẠY TRỰC TIẾP: hiển thị thống kê
# ===========================================================================
if __name__ == "__main__":
    stats = get_stats()
    print(f"\n{'=' * 50}")
    print(f"  📊 THỐNG KÊ ACTIVITY TEMPLATES")
    print(f"{'=' * 50}")
    print(f"  Tổng locations: {stats['total_locations']}")
    print(f"  Tổng activities: {stats['total_activities']}")
    print()
    
    for loc_name, detail in stats["locations_detail"].items():
        print(f"  📍 {loc_name}: {detail['activity_count']} activities")
        print(f"     Tags: {', '.join(detail['tags'][:8])}...")
    print()
