"use client";

import { useEffect, useMemo, useRef } from "react";
import { Map, Marker, Popup, NavigationControl, type MapRef } from "react-map-gl/maplibre";
import type { LocationResult } from "@/lib/types";
import { usePlannerStore } from "@/store/planner-store";
import {
  applyVnLocalization,
  MAP_STYLE_URL,
  VN_INITIAL_VIEW,
} from "@/components/map/vn-localization";
import { VnSovereigntyOverlay } from "@/components/map/vn-sovereignty-overlay";
import { cn } from "@/lib/utils";

type Props = { locations: LocationResult[] };

export function MapInner({ locations }: Props) {
  const withGeo = useMemo(
    () => locations.filter((l) => typeof l.geo?.lat === "number" && typeof l.geo?.lng === "number"),
    [locations],
  );
  const mapRef = useRef<MapRef>(null);

  const focusedLocationId = usePlannerStore((s) => s.focusedLocationId);
  const focusedAt = usePlannerStore((s) => s.focusedAt);
  const setFocusedLocation = usePlannerStore((s) => s.setFocusedLocation);

  useEffect(() => {
    if (!focusedAt || !focusedLocationId || !mapRef.current) return;
    const target = withGeo.find((l) => l.location_id === focusedLocationId);
    if (!target) return;
    mapRef.current.flyTo({
      center: [target.geo!.lng!, target.geo!.lat!],
      zoom: 10,
      duration: 900,
      essential: true,
    });
  }, [focusedAt, focusedLocationId, withGeo]);

  if (withGeo.length === 0) {
    return (
      <div className="image-slot border-border text-muted-foreground flex h-[460px] items-center justify-center rounded-2xl border text-sm">
        Các địa điểm hiện tại chưa có toạ độ{" "}
        <code className="bg-muted mx-1 rounded px-1.5">geo.lat/lng</code>
      </div>
    );
  }

  const active = focusedLocationId
    ? withGeo.find((l) => l.location_id === focusedLocationId)
    : null;

  return (
    <div className="border-border overflow-hidden rounded-2xl border shadow-sm">
      <Map
        ref={mapRef}
        initialViewState={VN_INITIAL_VIEW}
        mapStyle={MAP_STYLE_URL}
        style={{ width: "100%", height: 460 }}
        onLoad={(e) => {
          applyVnLocalization(e.target);
          if (withGeo.length > 1 && mapRef.current) {
            const lats = withGeo.map((l) => l.geo!.lat!);
            const lngs = withGeo.map((l) => l.geo!.lng!);
            mapRef.current.fitBounds(
              [
                [Math.min(...lngs), Math.min(...lats)],
                [Math.max(...lngs), Math.max(...lats)],
              ],
              { padding: 80, maxZoom: 9, duration: 800 },
            );
          } else if (withGeo.length === 1 && mapRef.current) {
            mapRef.current.flyTo({
              center: [withGeo[0].geo!.lng!, withGeo[0].geo!.lat!],
              zoom: 8,
              duration: 800,
            });
          }
        }}
      >
        <NavigationControl position="top-right" />

        {/* Result markers */}
        {withGeo.map((loc, i) => (
          <Marker
            key={loc.location_id}
            longitude={loc.geo!.lng!}
            latitude={loc.geo!.lat!}
            anchor="bottom"
            onClick={(e) => {
              e.originalEvent.stopPropagation();
              setFocusedLocation(loc.location_id);
            }}
          >
            <ResultPin rank={i + 1} active={focusedLocationId === loc.location_id} />
          </Marker>
        ))}

        <VnSovereigntyOverlay />

        {active ? (
          <Popup
            longitude={active.geo!.lng!}
            latitude={active.geo!.lat!}
            anchor="bottom"
            offset={36}
            onClose={() => setFocusedLocation(null)}
            closeOnClick={false}
            closeButton
          >
            <div className="space-y-1 p-1">
              <div className="text-foreground text-sm font-bold">
                {active.metadata?.name ?? active.location_id}
              </div>
              <div className="text-muted-foreground text-xs">
                Match score{" "}
                <span className="text-primary font-mono font-semibold">
                  {Math.round(active.score * 100)}%
                </span>
              </div>
              <a
                href={`#loc-${active.location_id}`}
                className="text-primary text-[11px] font-semibold hover:underline"
                onClick={() => setFocusedLocation(null)}
              >
                Xem chi tiết ↓
              </a>
            </div>
          </Popup>
        ) : null}
      </Map>
    </div>
  );
}

function ResultPin({ rank, active }: { rank: number; active: boolean }) {
  return (
    <div className="relative -translate-y-1 cursor-pointer">
      <div
        className={cn(
          "bg-primary text-primary-foreground flex size-9 items-center justify-center rounded-full border-2 border-white text-sm font-extrabold shadow-lg transition-transform",
          active && "shadow-primary/40 scale-125",
        )}
      >
        {rank}
      </div>
      <div className="bg-primary absolute -bottom-1 left-1/2 size-2 -translate-x-1/2 rotate-45" />
    </div>
  );
}
