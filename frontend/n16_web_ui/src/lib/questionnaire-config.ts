/**
 * Travel questionnaire schema — ported from
 * frontend/n7_legacy_streamlit_ui/views/input/questionnaire_data.py
 *
 * Each Question has:
 *   - categories: section name → option label → tag list (rendered as primary cards)
 *   - specifics: section name → option label → tag list (rendered inside popover)
 *   - multi/maxSelect: cap on category selection count (specifics are capped at 3 per section)
 */
export type OptionTags = Record<string, string[]>;
export type QuestionSection = Record<string, OptionTags>;

export type Question = {
  id: string;
  question: string;
  multi: boolean;
  maxSelect?: number;
  categories?: QuestionSection;
  specifics?: QuestionSection;
};

export const SPECIFICS_MAX = 3;

export const QUESTIONNAIRE_CONFIG: readonly Question[] = [
  {
    id: "q1_landscape",
    question: "Bạn muốn khám phá loại phong cảnh nào? (chọn tối đa 3)",
    multi: true,
    maxSelect: 3,
    categories: {
      "⛰️ Địa hình": {
        "Núi cao": ["mountain"],
        "Đồi núi": ["hill"],
        "Thung lũng": ["valley"],
        "Cao nguyên": ["plateau"],
      },
      "🌊 Sông & Biển": {
        "Bãi biển": ["beach"],
        Đảo: ["island"],
        Sông: ["river"],
        Hồ: ["lake"],
      },
      "🌿 Hệ sinh thái": {
        "Vườn quốc gia": ["national park"],
        "Rừng rậm": ["forest"],
        "Khu bảo tồn": ["nature reserve"],
        "Rạn san hô": ["coral reef"],
      },
      "🏙️ Xã hội": {
        "Thành thị": ["city"],
        "Phố cổ": ["old town"],
        "Làng quê": ["village"],
      },
    },
    specifics: {
      "🏔️ Địa chất & Hang động": {
        "Đá vôi & Karst": ["karst"],
        "Hang động": ["cave"],
        "Đồi cát": ["sand dune"],
      },
      "💧 Cảnh quan Nước": {
        "Quần đảo": ["archipelago"],
        "Thác nước": ["waterfall"],
        "Suối nước nóng": ["hot spring"],
        "Đồng bằng": ["delta"],
      },
      "🌳 Rừng & Sinh thái": {
        "Rừng ngập mặn": ["mangrove"],
        "Khu dự trữ sinh quyển": ["biosphere reserve"],
      },
      "⛅ Mùa & Hiện tượng đặc trưng": {
        "Săn mây": ["cloud sea"],
        "Mùa lúa chín": ["harvest season"],
        "Mùa hoa nở": ["flower season"],
      },
    },
  },
  {
    id: "q2_companion",
    question: "Bạn chia sẻ chuyến đi này cùng với những ai?",
    multi: false,
    categories: {
      "👥 Thành phần": {
        "Một mình": ["solo"],
        "Cặp đôi": ["couple"],
        "Gia đình": ["family"],
        "Nhóm bạn": ["friends trip"],
        "Đồng nghiệp": ["corporate"],
      },
    },
  },
  {
    id: "q3_vibes",
    question: "Bạn muốn chuyến đi mang lại cảm giác gì? (chọn tối đa 4)",
    multi: true,
    maxSelect: 4,
    categories: {
      "💕 Cảm xúc": {
        "Lãng mạn": ["romantic"],
        "Hoang dã": ["wild"],
        "Hoài cổ": ["nostalgic"],
        "Tâm linh": ["spiritual"],
      },
      "😌 Thư giãn": {
        "Yên bình": ["peaceful"],
        Chill: ["chill"],
        "Chậm rãi": ["slow travel"],
        "Ấm cúng": ["cozy"],
      },
      "🌋 Khám phá": {
        "Sôi động": ["vibrant"],
        "Phiêu lưu": ["adventure"],
        "Góc khuất ẩn mình": ["off the beaten path"],
        "Văn hóa địa phương": ["authentic"],
      },
      "✨ Thẩm mỹ": {
        "Nên thơ": ["picturesque"],
        Bohemian: ["bohemian"],
        "Mộc mạc": ["rustic"],
        "Hiện đại": ["modern"],
      },
    },
  },
  {
    id: "q4_food",
    question: "Bạn muốn trải nghiệm ẩm thực theo phong cách nào?",
    multi: false,
    categories: {
      "🍱 Ẩm thực": {
        "Vỉa hè": ["street food"],
        "Đặc sản": ["local cuisine"],
        "Nhà hàng": ["fine dining"],
        "Tour ẩm thực": ["food tour"],
        "Hải sản": ["seafood"],
      },
    },
    specifics: {
      "🍽️ Lựa chọn ẩm thực đặc biệt khác": {
        "Ẩm thực cung đình": ["royal cuisine"],
        "Hữu cơ & Sạch": ["organic"],
        "Ăn chay (vegetarian)": ["vegetarian"],
        "Thuần chay (vegan)": ["vegan"],
        Halal: ["halal"],
        "Cà phê Việt Nam": ["coffee"],
        "Bia hơi": ["bia hoi"],
        "Bia thủ công": ["craft beer"],
        "Hoa quả nhiệt đới": ["tropical fruit"],
        "Rượu truyền thống": ["local wine"],
        "Trà cao nguyên": ["tea"],
      },
    },
  },
  {
    id: "q5_activities",
    question: "Bạn muốn trải nghiệm hoạt động gì? (chọn tối đa 5)",
    multi: true,
    maxSelect: 5,
    specifics: {
      "🥾 Phiêu lưu trên cạn": {
        Trekking: ["trekking"],
        "Leo núi": ["hiking"],
        "Tour xe máy": ["motorbiking"],
        "Phượt xe máy / Loop": ["motorbike loop"],
        "Đạp xe": ["cycling"],
        "Chạy trail": ["trail running"],
        "Leo vách đá": ["rock climbing"],
        "Thám hiểm hang động": ["caving"],
        Canyoning: ["canyoning"],
        "Cắm trại": ["camping"],
        "Tour xe Jeep": ["jeep tour"],
        "Tour xe địa hình": ["ATV"],
      },
      "🌊 Phiêu lưu dưới nước": {
        "Lặn có bình khí": ["scuba diving"],
        "Lặn ống thở": ["snorkeling"],
        Seawalk: ["seawalk"],
        "Chèo thuyền kayak": ["kayaking"],
        "SUP (đứng chèo)": ["stand up paddle"],
        "Lướt sóng": ["surfing"],
        Kitesurfing: ["kitesurfing"],
        "Chèo thuyền vượt thác": ["rafting"],
        "Nhảy thác": ["waterfall jumping"],
        "Bơi lội": ["swimming"],
        "Tắm bùn khoáng": ["mud bath"],
      },
      "🛶 Trải nghiệm trên sông": {
        "Du thuyền qua đêm": ["boat cruise"],
        "Thuyền gỗ truyền thống": ["junk boat"],
        "Ngồi đò qua hang động": ["limestone boat ride"],
        "Chèo bè tre": ["bamboo rafting"],
        "Thuyền thúng": ["basket boat"],
        "Tàu cao tốc": ["speed boat"],
        "Du thuyền sông": ["river cruise"],
        "Câu cá": ["fishing"],
        "Câu mực ban đêm": ["squid fishing"],
      },
      "🎈 Trên không & Giải trí": {
        "Cáp treo": ["cable car"],
        "Dù lượn": ["paragliding"],
        "Khinh khí cầu": ["hot air balloon"],
        "Hành trình tàu hỏa": ["train journey"],
        "Tàu hoả đêm": ["night train"],
        "Tour xích lô": ["cyclo"],
        "Chụp ảnh phong cảnh": ["photography"],
        "Mua sắm": ["shopping"],
        Golf: ["golf"],
        "Công viên giải trí": ["theme park"],
        "Công viên nước": ["water park"],
        "Dã ngoại / Picnic": ["picnic"],
        "Tour đêm": ["night tour"],
      },
      "🧖 Sức khoẻ & Spa": {
        "Spa & Massage": ["spa"],
        "Tắm thảo dược": ["herbal bath"],
        "Retreat Yoga": ["yoga retreat"],
        "Retreat sức khoẻ": ["wellness retreat"],
        "Tắm suối nước nóng": ["hot spring bath"],
      },
      "🍜 Văn hoá & Học hỏi": {
        "Lớp học nấu ăn": ["cooking class"],
        "Lớp làm gốm": ["pottery class"],
        "Làm đèn lồng": ["lantern making"],
        "Thăm trang trại": ["farm tour"],
        "Thưởng trà": ["tea tasting"],
        "Tour cà phê": ["coffee tour"],
        "Biểu diễn nghệ thuật": ["cultural show"],
        "Múa rối nước": ["water puppet"],
        "Âm nhạc truyền thống": ["traditional music"],
        "Làng nghề thủ công": ["craft village"],
        "Hoạt động thiện nguyện": ["volunteering"],
      },
    },
  },
  {
    id: "q6_style",
    question: "Bạn thích đi theo phong cách nào?",
    multi: false,
    specifics: {
      "⏱️ Thời lượng & Dịp đặc biệt": {
        "Đi về trong ngày": ["day trip"],
        "Cuối tuần": ["weekend trip"],
        "Dài ngày": ["long stay"],
        Workcation: ["workcation"],
        "Phượt bụi": ["backpacking"],
        "Tuần trăng mật": ["honeymoon"],
        "Kỷ niệm": ["couple"],
        "Team building": ["group"],
      },
      "💰 Ngân sách & Nhịp độ": {
        "Tiết kiệm / Bụi": ["budget", "backpacking"],
        "Tầm trung": ["mid range"],
        "Sang trọng": ["luxury"],
        "Chậm & Sâu": ["slow travel"],
      },
      "🏠 Nơi lưu trú": {
        "Khu nghỉ dưỡng": ["resort"],
        "Khách sạn boutique": ["boutique"],
        Homestay: ["homestay"],
        "Eco lodge": ["eco lodge"],
        Glamping: ["glamping"],
        "Cắm trại": ["camping"],
      },
      "🏘️ Trải nghiệm đô thị": {
        "Làng chài": ["fishing village"],
        "Chợ nổi": ["floating market"],
        "Chợ đêm": ["night market"],
        "Phố đi bộ": ["walking street"],
        "Bar rooftop": ["rooftop bar"],
        "Không gian coworking": ["coworking"],
      },
      "🎒 Du lịch chuyên biệt": {
        "Du lịch sinh thái": ["eco travel"],
        "Du lịch nông nghiệp": ["agro tourism"],
        "Du lịch sức khoẻ": ["wellness tourism"],
        "Tour ẩm thực chuyên đề": ["culinary tourism"],
        "Du lịch chiến trường": ["war tourism"],
        "Du lịch tâm linh": ["religious tourism"],
        "Du lịch thể thao": ["sports tourism"],
        "Tour chụp ảnh": ["photography tour"],
        "Du lịch y tế": ["medical tourism"],
        "Digital nomad": ["digital nomad"],
        "MICE & Doanh nghiệp": ["MICE"],
      },
    },
  },
];
