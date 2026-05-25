"use client";

/**
 * VN sovereignty overlay — symbol layers zoom-scaled, dùng chung giữa các bản đồ.
 * Vẽ tên biển ("Biển Đông"), tên quần đảo (Hoàng Sa, Trường Sa), tên đảo nổi
 * + tên đá / bãi ngầm của VN tại Trường Sa kèm tên quốc tế.
 */

import { Source, Layer } from "react-map-gl/maplibre";
import type { FeatureCollection, Point } from "geojson";

type OverlayKind = "sea" | "archipelago" | "island" | "reef";

function f(name: string, en: string | null, kind: OverlayKind, lng: number, lat: number) {
  return {
    type: "Feature" as const,
    properties: { name, en: en ?? "", kind },
    geometry: { type: "Point" as const, coordinates: [lng, lat] },
  };
}

const VN_OVERLAY_GEOJSON: FeatureCollection<
  Point,
  { name: string; en: string; kind: OverlayKind }
> = {
  type: "FeatureCollection",
  features: [
    // Sea label (thay South China Sea)
    f("Biển Đông", null, "sea", 113.0, 14.5),

    // Archipelagos
    f("Đặc khu Hoàng Sa", null, "archipelago", 112.0, 16.5),
    f("Đặc khu Trường Sa", null, "archipelago", 114.0, 10.0),

    // Đảo nổi
    f("Đảo Trường Sa", "Spratly Island", "island", 111.921, 8.6447),
    f("Đảo Trường Sa Đông", "Central Reef", "island", 112.36, 8.91),
    f("Đảo An Bang", "Amboyna Cay", "island", 112.9167, 7.8833),
    f("Đảo Nam Yết", "Namyit Island", "island", 114.3667, 10.1667),
    f("Đảo Sơn Ca", "Sand Cay", "island", 114.4833, 10.3833),
    f("Đảo Sinh Tồn", "Sin Cowe Island", "island", 114.3333, 9.8833),
    f("Đảo Sinh Tồn Đông", "Grierson Reef", "island", 114.65, 9.9),
    f("Đảo Song Tử Tây", "Southwest Cay", "island", 114.3333, 11.4333),
    f("Đảo Phan Vinh", "Pearson Reef", "island", 113.7, 8.95),

    // Đá / Bãi
    f("Đá Cô Lin", "Collins Reef", "reef", 114.25, 9.7667),
    f("Đá Đông", "East Reef", "reef", 112.6, 8.8333),
    f("Đá Lát", "Ladd Reef", "reef", 111.6667, 8.6833),
    f("Đá Len Đao", "Lansdowne Reef", "reef", 114.3833, 9.7167),
    f("Đá Lớn", "Discovery Great Reef", "reef", 113.85, 10.0333),
    f("Đá Nam", "South Reef", "reef", 114.3, 11.3833),
    f("Đá Núi Thị", "Petley Reef", "reef", 114.5833, 10.4167),
    f("Đá Núi Le", "Cornwallis South Reef", "reef", 114.1833, 8.7333),
    f("Đá Tây", "West Reef", "reef", 112.2333, 8.85),
    f("Bãi Thuyền Chài", "Barque Canada Reef", "reef", 113.3, 8.1667),
    f("Đá Tiên Nữ", "Tennent Reef", "reef", 114.65, 8.85),
    f("Đá Tốc Tan", "Alison Reef", "reef", 113.9833, 8.8333),
  ],
};

export function VnSovereigntyOverlay() {
  return (
    <Source id="vn-overlay" type="geojson" data={VN_OVERLAY_GEOJSON}>
      {/* Tên biển: thay "South China Sea" bằng "Biển Đông" (maxzoom 7) */}
      <Layer
        id="vn-sea-label"
        type="symbol"
        maxzoom={7}
        filter={["==", ["get", "kind"], "sea"]}
        layout={{
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Italic"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 3, 14, 5, 20, 7, 28, 10, 38],
          "text-letter-spacing": 0.25,
          "text-max-width": 8,
          "text-transform": "uppercase",
        }}
        paint={{
          "text-color": "#1e3a8a",
          "text-halo-color": "rgba(255,255,255,0.9)",
          "text-halo-width": 1.5,
        }}
      />

      {/* Tên đặc khu (Hoàng Sa, Trường Sa) — xám, regular giống admin labels */}
      <Layer
        id="vn-archipelago-label"
        type="symbol"
        maxzoom={9}
        filter={["==", ["get", "kind"], "archipelago"]}
        layout={{
          "text-field": ["get", "name"],
          "text-font": ["Open Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 3, 11, 5, 14, 7, 18, 10, 24],
          "text-letter-spacing": 0.1,
          "text-max-width": 8,
        }}
        paint={{
          "text-color": "#6b7280",
          "text-halo-color": "rgba(255,255,255,0.95)",
          "text-halo-width": 1.6,
        }}
      />

      {/* Đảo nổi — dot + 2-line label (VN tên + tên quốc tế nhỏ hơn) */}
      <Layer
        id="vn-island-dot"
        type="circle"
        filter={["==", ["get", "kind"], "island"]}
        minzoom={5}
        paint={{
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 2, 8, 3.5, 11, 5],
          "circle-color": "#b91c1c",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2,
        }}
      />
      <Layer
        id="vn-island-label"
        type="symbol"
        filter={["==", ["get", "kind"], "island"]}
        minzoom={6}
        layout={{
          "text-field": [
            "format",
            ["get", "name"],
            { "font-scale": 1.0 },
            "\n",
            {},
            ["get", "en"],
            { "font-scale": 0.72, "text-font": ["literal", ["Open Sans Italic"]] },
          ],
          "text-font": ["Open Sans Bold"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 6, 9, 8, 12, 11, 16, 14, 20],
          "text-anchor": "top",
          "text-offset": [0, 0.7],
          "text-max-width": 10,
        }}
        paint={{
          "text-color": "#0f172a",
          "text-halo-color": "rgba(255,255,255,0.95)",
          "text-halo-width": 1.4,
        }}
      />

      {/* Đá / Bãi — dot nhỏ hơn + label chỉ hiện ở zoom cao hơn */}
      <Layer
        id="vn-reef-dot"
        type="circle"
        filter={["==", ["get", "kind"], "reef"]}
        minzoom={6}
        paint={{
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 1.5, 9, 2.5, 12, 4],
          "circle-color": "#0ea5e9",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
        }}
      />
      <Layer
        id="vn-reef-label"
        type="symbol"
        filter={["==", ["get", "kind"], "reef"]}
        minzoom={7}
        layout={{
          "text-field": [
            "format",
            ["get", "name"],
            { "font-scale": 1.0 },
            "\n",
            {},
            ["get", "en"],
            { "font-scale": 0.7, "text-font": ["literal", ["Open Sans Italic"]] },
          ],
          "text-font": ["Open Sans Regular"],
          "text-size": ["interpolate", ["linear"], ["zoom"], 7, 8, 9, 11, 12, 14, 14, 18],
          "text-anchor": "top",
          "text-offset": [0, 0.6],
          "text-max-width": 10,
        }}
        paint={{
          "text-color": "#0c4a6e",
          "text-halo-color": "rgba(255,255,255,0.9)",
          "text-halo-width": 1.2,
        }}
      />
    </Source>
  );
}
