"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import { LocationCard } from "./location-card";
import { GlobalFeedback } from "./global-feedback";
import { MapView } from "./map-view";
import { usePlannerStore } from "@/store/planner-store";
import { ArrowLeft, Download, MapIcon, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

export function ResultView() {
  const results = usePlannerStore((s) => s.results);
  const activityResults = usePlannerStore((s) => s.activityResults);
  const activityResultsLlm = usePlannerStore((s) => s.activityResultsLlm);
  const preferLlmActivities = usePlannerStore((s) => s.preferLlmActivities);

  const locations = results?.locations ?? [];
  const topLocations = locations.slice(0, 5);

  function handleSave() {
    const data = {
      saved_at: new Date().toISOString(),
      locations: topLocations.map((loc, i) => {
        const preferLlm = preferLlmActivities[loc.location_id] ?? false;
        const currentActivities = preferLlm
          ? activityResultsLlm[loc.location_id]
          : activityResults[loc.location_id];
        return {
          rank: i + 1,
          location_id: loc.location_id,
          score: loc.score,
          reason: loc.reason,
          metadata: loc.metadata,
          images: loc.images,
          geo: loc.geo,
          activities: currentActivities?.activities?.slice(0, 5) ?? [],
        };
      }),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `travel-plan-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

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
        <div className="flex-1">
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

        <Button variant="outline" size="sm" onClick={handleSave} title="Lưu kết quả ra file JSON">
          <Download className="size-3.5" />
          Lưu
        </Button>
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
