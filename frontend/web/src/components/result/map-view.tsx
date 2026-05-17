"use client";

import dynamic from "next/dynamic";
import { Skeleton } from "@/components/ui/skeleton";
import type { LocationResult } from "@/lib/types";

/**
 * MapLibre + OpenFreeMap (overridable via NEXT_PUBLIC_MAP_STYLE_URL).
 * Dynamic import so MapLibre (which touches `window`) is never loaded during SSR.
 */
const MapInner = dynamic(() => import("./map-inner").then((m) => ({ default: m.MapInner })), {
  ssr: false,
  loading: () => (
    <div className="border-border overflow-hidden rounded-2xl border">
      <Skeleton className="h-[420px] w-full" />
    </div>
  ),
});

export function MapView({ locations }: { locations: LocationResult[] }) {
  return <MapInner locations={locations} />;
}
