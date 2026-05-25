"use client";

import { useEffect, useMemo, useRef } from "react";
import { Map, Marker, NavigationControl, type MapRef } from "react-map-gl/maplibre";
import {
  applyVnLocalization,
  MAP_STYLE_URL,
  VN_INITIAL_VIEW,
} from "@/components/map/vn-localization";
import { VnSovereigntyOverlay } from "@/components/map/vn-sovereignty-overlay";
import type { ExploreLocation } from "@/lib/types";
import { cn } from "@/lib/utils";

type Props = {
  locations: ExploreLocation[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
};

export function ExploreMap({ locations, selectedId, onSelect }: Props) {
  const withGeo = useMemo(
    () => locations.filter((l) => typeof l.geo?.lat === "number" && typeof l.geo?.lng === "number"),
    [locations],
  );
  const mapRef = useRef<MapRef>(null);
  const hasFitBoundsRef = useRef(false);

  // When selectedId changes → fly to that location
  useEffect(() => {
    if (!selectedId || !mapRef.current) return;
    const target = withGeo.find((l) => l.location_id === selectedId);
    if (!target) return;
    mapRef.current.flyTo({
      center: [target.geo!.lng!, target.geo!.lat!],
      zoom: 10,
      duration: 900,
      essential: true,
    });
  }, [selectedId, withGeo]);

  return (
    <Map
      ref={mapRef}
      initialViewState={VN_INITIAL_VIEW}
      mapStyle={MAP_STYLE_URL}
      style={{ width: "100%", height: "100%" }}
      onLoad={(e) => {
        applyVnLocalization(e.target);
        if (!hasFitBoundsRef.current && withGeo.length > 1 && mapRef.current) {
          const lats = withGeo.map((l) => l.geo!.lat!);
          const lngs = withGeo.map((l) => l.geo!.lng!);
          mapRef.current.fitBounds(
            [
              [Math.min(...lngs), Math.min(...lats)],
              [Math.max(...lngs), Math.max(...lats)],
            ],
            { padding: 60, maxZoom: 8, duration: 0 },
          );
          hasFitBoundsRef.current = true;
        }
      }}
    >
      <NavigationControl position="top-right" />

      {withGeo.map((loc) => (
        <Marker
          key={loc.location_id}
          longitude={loc.geo!.lng!}
          latitude={loc.geo!.lat!}
          anchor="bottom"
          onClick={(e) => {
            e.originalEvent.stopPropagation();
            onSelect(loc.location_id);
          }}
        >
          <ExplorePin active={selectedId === loc.location_id} />
        </Marker>
      ))}

      <VnSovereigntyOverlay />
    </Map>
  );
}

function ExplorePin({ active }: { active: boolean }) {
  return (
    <div className="relative -translate-y-1 cursor-pointer">
      <div
        className={cn(
          "bg-primary size-7 rounded-full border-2 border-white shadow-md transition-transform",
          active && "ring-primary/40 scale-125 ring-2",
        )}
      />
      <div className="bg-primary absolute -bottom-1 left-1/2 size-1.5 -translate-x-1/2 rotate-45" />
    </div>
  );
}
