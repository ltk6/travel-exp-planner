"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { LocationCard } from "./location-card";
import { GlobalFeedback } from "./global-feedback";
import { MapView } from "./map-view";
import { usePlannerStore } from "@/store/planner-store";
import { ArrowLeft, MapIcon, Sparkles } from "lucide-react";

export function ResultView() {
  const results = usePlannerStore((s) => s.results);

  const locations = results?.locations ?? [];
  const topLocations = locations.slice(0, 5);

  if (topLocations.length === 0) {
    return (
      <div className="border-border flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-12 text-center">
        <Sparkles className="text-muted-foreground/40 size-8" />
        <p className="text-muted-foreground text-sm">
          Chưa có kết quả. Hãy gửi đầu vào ở trang chủ.
        </p>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft className="mr-2 size-4" />
          Quay lại nhập liệu
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="bg-primary text-primary-foreground flex size-10 items-center justify-center rounded-full text-lg font-bold">
          {topLocations.length}
        </div>
        <div>
          <h2 className="text-foreground text-2xl font-bold">
            Top {topLocations.length} địa điểm phù hợp
          </h2>
          <p className="text-muted-foreground text-sm">
            Click vào ô{" "}
            <Badge variant="outline" className="mx-0.5 text-xs">
              Tinh chỉnh
            </Badge>{" "}
            để điều chỉnh từng địa điểm.
          </p>
        </div>
      </div>

      <section id="result-map" className="scroll-mt-24 space-y-3">
        <div className="text-muted-foreground flex items-center gap-2 text-sm font-semibold tracking-wider uppercase">
          <MapIcon className="text-primary size-4" />
          Bản đồ Việt Nam — chủ quyền Hoàng Sa &amp; Trường Sa
        </div>
        <MapView locations={topLocations} />
      </section>

      <div className="space-y-4">
        {topLocations.map((loc, i) => (
          <LocationCard key={loc.location_id} loc={loc} rank={i + 1} />
        ))}
      </div>

      <GlobalFeedback />
    </div>
  );
}
