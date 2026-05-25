/**
 * Shared VN-sovereignty map helpers — dùng chung giữa Results map và Explore map.
 *
 * Trên Carto Positron, tile vendor dùng OSM data nên có thể render:
 *   - "South China Sea" (layer `watername_ocean`)
 *   - Các claim hành chính do TQ áp đặt (Tam Sa, Quận Nam Sa) và tên đảo theo
 *     pinyin / chữ Hán (Zhubidao, Yongle Qundao, Yagong, ...)
 *
 * `applyVnLocalization()` gọi sau khi style load xong:
 *   1. Ẩn các layer label biển/đại dương — sẽ được thay bằng "Biển Đông" trong
 *      <VnSovereigntyOverlay/>
 *   2. Override `text-field` cho mọi symbol layer `place`:
 *      - Trả "" cho feature trong bbox tranh chấp hoặc tên trong blacklist
 *      - Ngược lại ưu tiên `name:vi` rồi fallback `name`
 */

import type { Map as MaplibreMap } from "maplibre-gl";

const STYLE_OVERRIDE = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "";

/** URL style mặc định — Carto Positron (free, no key, OpenMapTiles schema). */
export const MAP_STYLE_URL =
  STYLE_OVERRIDE || "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";

/** View khởi tạo — bao phủ VN + Hoàng Sa + Trường Sa. */
export const VN_INITIAL_VIEW = { longitude: 110, latitude: 14, zoom: 4.3 };

const SEA_LABEL_LAYER_IDS = [
  "watername_ocean",
  "watername_sea",
  "water_name_ocean",
  "water_name_sea",
];

/**
 * Bbox bao Hoàng Sa + Trường Sa. Cận tây 110.5°E cố ý chọn để không catch nhầm
 * bờ biển VN (Đà Nẵng 108.2°, Nha Trang 109.2°).
 */
const DISPUTED_BBOX_GEOJSON = {
  type: "Polygon" as const,
  coordinates: [
    [
      [110.5, 6],
      [118, 6],
      [118, 19],
      [110.5, 19],
      [110.5, 6],
    ],
  ],
};

const HIDDEN_PLACE_NAMES = [
  // Tam Sa (Sansha) — TP cấp địa khu TQ áp đặt lên Hoàng Sa + Trường Sa
  "Sansha",
  "Sansha City",
  "Sansha Shi",
  "Tam Sa",
  "三沙",
  "三沙市",
  // Quận Nam Sa (Nansha District)
  "Nansha",
  "Nansha District",
  "Nansha Qu",
  "Nansha Qū",
  "Quận Nam Sa",
  "南沙",
  "南沙区",
  // Kalayaan (claim Philippines)
  "Kalayaan",
  // Đá Xu Bi (Zhubi Dao / Subi Reef)
  "Zhubi",
  "Zhubi Dao",
  "Zhubidao",
  "Subi",
  "Subi Reef",
  "渚碧",
  "渚碧岛",
  // Nhóm Lưỡi Liềm (Yongle Qundao / Crescent Group thuộc Hoàng Sa)
  "Yongle",
  "Yongle Qundao",
  "Crescent Group",
  "永乐",
  "永乐群岛",
  // Đảo Ngân Tự (Yin Yu)
  "Yinyu",
  "Yin Yu",
  "银屿",
  "Ngân Tự",
  "Xã khu Ngân Tự",
  // Đảo Áp Công (Yagong)
  "Yagong",
  "Ya Gong",
  "鸭公",
  "Áp Công",
  "Xã khu Áp Công",
  // Đảo Cam Tuyền (Ganquan / Robert Island)
  "Ganquan",
  "Ganquan Dao",
  "Robert Island",
  "甘泉",
  "甘泉岛",
  "Cam Tuyền",
  "Xã khu Cam Tuyền",
  // Đá Linh Dương (Lingyang / Antelope Reef)
  "Lingyang",
  "Lingyang Jiao",
  "Antelope Reef",
  "羚羊",
  "羚羊礁",
  "Linh Dương",
  "Xã khu Linh Dương",
  // Nhóm Đảo An Vĩnh (Qilianyu / Seven Connected Isles) — user viết "Quiulanyu"
  "Qilianyu",
  "Qilian",
  "Quiulanyu",
  "Quilianyu",
  "七连屿",
];

export function applyVnLocalization(map: MaplibreMap): void {
  for (const id of SEA_LABEL_LAYER_IDS) {
    try {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", "none");
    } catch {
      // ignore — layer absent in current style
    }
  }
  const style = map.getStyle();
  for (const layer of style.layers ?? []) {
    if (layer.type !== "symbol") continue;
    if ((layer as { "source-layer"?: string })["source-layer"] !== "place") continue;
    try {
      map.setLayoutProperty(layer.id, "text-field", [
        "case",
        [
          "any",
          ["within", DISPUTED_BBOX_GEOJSON],
          ["in", ["get", "name"], ["literal", HIDDEN_PLACE_NAMES]],
          ["in", ["get", "name:vi"], ["literal", HIDDEN_PLACE_NAMES]],
          ["in", ["get", "name:en"], ["literal", HIDDEN_PLACE_NAMES]],
          ["in", ["get", "name:zh"], ["literal", HIDDEN_PLACE_NAMES]],
        ],
        "",
        [
          "coalesce",
          ["get", "name:vi"],
          ["get", "name_vi"],
          ["get", "name:latin"],
          ["get", "name"],
        ],
      ]);
    } catch {
      // ignore — some layers don't accept text-field overrides
    }
  }
}
