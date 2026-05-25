import { QUESTIONNAIRE_CONFIG } from "./questionnaire-config";

/**
 * Shortened static translation map for travel ontology tags (Max 3 words)
 */
const ALL_TAGS_VI: Record<string, string> = {
  // A. TERRAIN & LANDSCAPE
  mountain: "Núi cao",
  hill: "Đồi núi",
  karst: "Địa hình đá vôi",
  valley: "Thung lũng",
  plateau: "Cao nguyên",
  cliff: "Vách đá",
  cave: "Hang động",
  "sand dune": "Đồi cát",
  delta: "Đồng bằng sông",
  plain: "Đồng bằng",
  "rice terrace": "Ruộng bậc thang",
  farm: "Trang trại",
  "flower field": "Cánh đồng hoa",
  "tea plantation": "Đồi chè",
  "salt field": "Ruộng muối",

  // B. WATER & COAST
  beach: "Bãi biển",
  bay: "Vịnh biển",
  island: "Đảo",
  archipelago: "Quần đảo",
  lagoon: "Đầm phá",
  lake: "Hồ nước",
  river: "Sông nước",
  stream: "Suối nguồn",
  waterfall: "Thác nước",
  "hot spring": "Suối khoáng nóng",
  wetland: "Đất ngập nước",
  "coral reef": "Rạn san hô",
  mangrove: "Rừng ngập mặn",

  // C. FLORA & ECOSYSTEMS
  "national park": "Vườn quốc gia",
  forest: "Rừng rậm",
  "pine forest": "Rừng thông",
  "bamboo forest": "Rừng tre",
  "biosphere reserve": "Dự trữ sinh quyển",
  "nature reserve": "Bảo tồn tự nhiên",
  birdwatching: "Ngắm chim",
  wildlife: "Động vật hoang dã",

  // D. CLIMATE & SEASON
  "cool climate": "Khí hậu mát",
  tropical: "Nhiệt đới",
  cold: "Khí hậu lạnh",
  "dry season": "Mùa khô",
  "rainy season": "Mùa mưa",
  "summer trip": "Du lịch hè",
  "winter trip": "Du lịch đông",
  "spring trip": "Du lịch xuân",
  "autumn trip": "Du lịch thu",
  snow: "Ngắm tuyết rơi",
  "cloud sea": "Săn biển mây",
  "flower season": "Mùa hoa nở",
  "harvest season": "Mùa lúa chín",

  // E. CULTURE & HERITAGE
  history: "Lịch sử",
  "war history": "Lịch sử chiến tranh",
  "colonial heritage": "Kiến trúc Pháp",
  imperial: "Cung điện cổ",
  "royal tomb": "Lăng tẩm cổ",
  "cham culture": "Văn hóa Chăm",
  prehistoric: "Tiền sử",
  temple: "Đền thờ",
  pagoda: "Chùa chiền",
  church: "Nhà thờ cổ",
  spiritual: "Tâm linh",
  meditation: "Thiền định",
  "ethnic minority": "Dân tộc ít người",
  "ethnic village": "Bản làng vùng cao",
  "craft village": "Làng nghề cổ",
  "silk village": "Làng lụa",
  "traditional music": "Nhạc cổ truyền",
  "water puppet": "Múa rối nước",
  festival: "Lễ hội",
  art: "Nghệ thuật",
  "lantern festival": "Lễ đèn lồng",
  "UNESCO heritage": "Di sản UNESCO",

  // F. URBAN & SETTLEMENT
  city: "Đô thị",
  "old town": "Khu phố cổ",
  village: "Làng quê",
  "fishing village": "Làng chài",
  market: "Chợ truyền thống",
  "night market": "Chợ đêm",
  "floating market": "Chợ nổi",
  "ethnic market": "Chợ phiên",
  "walking street": "Phố đi bộ",
  "rooftop bar": "Rooftop Bar",
  coworking: "Coworking Space",

  // G. ACTIVITIES — LAND
  trekking: "Trekking",
  hiking: "Hiking",
  motorbiking: "Phượt xe máy",
  "motorbike loop": "Đèo dốc phượt",
  cycling: "Đạp xe dã ngoại",
  "rock climbing": "Leo núi đá",
  caving: "Khám phá hang",
  "cave expedition": "Thám hiểm hang",
  canyoning: "Vượt thác",
  "zip lining": "Trượt Zipline",
  camping: "Cắm trại",
  "jeep tour": "Tour xe Jeep",
  ATV: "Đua xe ATV",
  "train journey": "Tàu hỏa ngắm cảnh",
  "night train": "Tàu giường nằm",
  cyclo: "Đi xích lô",
  photography: "Nhiếp ảnh",
  shopping: "Mua sắm",
  golf: "Chơi Golf",
  "trail running": "Chạy địa hình",
  "scooter tour": "Tour xe máy",
  paragliding: "Bay dù lượn",
  "hot air balloon": "Khinh khí cầu",
  "cable car": "Đi cáp treo",

  // H. ACTIVITIES — WATER
  "scuba diving": "Lặn dưỡng khí",
  snorkeling: "Lặn ống thở",
  seawalk: "Đi bộ biển",
  kayaking: "Chèo Kayak",
  "stand up paddle": "Chèo SUP",
  surfing: "Lướt sóng",
  kitesurfing: "Lướt ván diều",
  "boat cruise": "Du thuyền",
  "junk boat": "Tàu gỗ vịnh",
  "basket boat": "Thuyền thúng",
  "speed boat": "Cano cao tốc",
  fishing: "Câu cá",
  "squid fishing": "Câu mực đêm",
  "river cruise": "Du thuyền sông",
  "limestone boat ride": "Thuyền chèo hang",
  rafting: "Vượt thác phao",
  "mud bath": "Tắm bùn nóng",
  swimming: "Tắm biển",
  "bamboo rafting": "Bè tre sông",
  "waterfall jumping": "Nhảy thác",

  // I. ACTIVITIES — LEISURE, WELLNESS & LEARNING
  spa: "Spa Massage",
  "herbal bath": "Tắm lá thuốc",
  "yoga retreat": "Tĩnh tâm Yoga",
  "wellness retreat": "Wellness Retreat",
  "hot spring bath": "Tắm suối nóng",
  "cooking class": "Lớp nấu ăn",
  "pottery class": "Lớp làm gốm",
  "lantern making": "Lớp đèn lồng",
  "farm tour": "Trải nghiệm vườn",
  "tea tasting": "Thưởng trà",
  "coffee tour": "Tour cà phê",
  "cultural show": "Xem Show diễn",
  "theme park": "Theme Park",
  "water park": "Công viên nước",
  picnic: "Cắm trại picnic",
  "night tour": "Tour du đêm",
  "martial arts class": "Lớp võ",
  volunteering: "Tình nguyện",

  // J. FOOD & DRINK
  "street food": "Ẩm thực đường phố",
  "local cuisine": "Đặc sản",
  "fine dining": "Fine Dining",
  "food tour": "Food Tour",
  "royal cuisine": "Ẩm thực cung đình",
  pho: "Món Phở",
  "banh mi": "Bánh mì",
  "fish sauce": "Nước mắm",
  seafood: "Hải sản",
  vegetarian: "Ăn chay",
  vegan: "Chay thuần (Vegan)",
  halal: "Ẩm thực Halal",
  organic: "Thực phẩm Organic",
  coffee: "Cà phê phin",
  "street coffee": "Cà phê bệt",
  "craft beer": "Bia thủ công",
  "bia hoi": "Bia hơi",
  "tropical fruit": "Quả nhiệt đới",
  "local wine": "Rượu đặc sản",
  tea: "Trà đặc sản",

  // K. VIBE & MOOD
  peaceful: "Yên bình",
  vibrant: "Nhộn nhịp",
  chill: "Thư thái",
  "slow travel": "Du lịch chậm",
  romantic: "Lãng mạn",
  mysterious: "Huyền bí",
  wild: "Hoang sơ",
  cozy: "Ấm cúng",
  nostalgic: "Hoài cổ",
  rustic: "Mộc mạc",
  picturesque: "Đẹp như tranh",
  bohemian: "Phóng khoáng",
  instagrammable: "Check-in đẹp",
  modern: "Hiện đại",
  "off the beaten path": "Khám phá mới",
  authentic: "Bản địa",
  immersive: "Trải nghiệm sâu",
  adventure: "Phiêu lưu",

  // L. TRIP PROFILE
  "day trip": "Chuyến đi ngày",
  "weekend trip": "Đi cuối tuần",
  "long stay": "Dài ngày",
  workcation: "Workcation",
  solo: "Đi một mình",
  couple: "Cặp đôi",
  honeymoon: "Tuần trăng mật",
  family: "Gia đình",
  group: "Nhóm đông",
  "friends trip": "Cùng bạn bè",
  corporate: "Teambuilding",
  backpacking: "Du lịch bụi",

  // M. BUDGET & ACCOMMODATION STYLE
  budget: "Bình dân",
  "mid range": "Tầm trung",
  luxury: "Sang trọng",
  boutique: "Boutique Hotel",
  homestay: "Homestay",
  "eco lodge": "Eco Lodge",
  resort: "Resort nghỉ dưỡng",
  glamping: "Glamping",
  "pet friendly": "Thân thú cưng",
  "wheelchair accessible": "Lối xe lăn",

  // N. SPECIAL INTEREST SEGMENTS
  "eco travel": "Du lịch sinh thái",
  "agro tourism": "Canh nông",
  "medical tourism": "Y tế",
  "wellness tourism": "Du lịch Wellness",
  "culinary tourism": "Du lịch ẩm thực",
  MICE: "Hội nghị MICE",
  "digital nomad": "Digital Nomad",
  "war tourism": "Chiến tích",
  "religious tourism": "Hành hương",
  "sports tourism": "Thể thao",
  "photography tour": "Tour săn ảnh",
  nightlife: "Giải trí đêm",
  "luxury travel": "Siêu sang",
};

/**
 * Builds a reverse map: English tag (returned by backend) → Vietnamese label
 * (from the questionnaire option that produced it). Used for displaying
 * `metadata.tags` on location/activity cards in Vietnamese.
 */
const TAG_TO_LABEL_VI: Record<string, string> = (() => {
  const map: Record<string, string> = {};
  for (const q of QUESTIONNAIRE_CONFIG) {
    for (const sec of Object.values(q.categories ?? {})) {
      for (const [label, tags] of Object.entries(sec)) {
        for (const t of tags) {
          if (!map[t]) map[t] = label;
        }
      }
    }
    for (const sec of Object.values(q.specifics ?? {})) {
      for (const [label, tags] of Object.entries(sec)) {
        for (const t of tags) {
          if (!map[t]) map[t] = label;
        }
      }
    }
  }
  return map;
})();

export function labelForTag(tag: string): string {
  if (!tag) return "";
  const normalizedTag = tag.toLowerCase().trim();
  return TAG_TO_LABEL_VI[normalizedTag] ?? ALL_TAGS_VI[normalizedTag] ?? tag;
}
