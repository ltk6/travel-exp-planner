"use client";

import { useState } from "react";
import { AlertCircle, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ActivityCard } from "./activity-card";
import { ActivitySkeleton } from "./activity-skeleton";
import { ActivityFilterChips } from "./activity-filter-chips";
import { useActivitiesQuery } from "@/hooks/use-activities-query";
import { usePlannerStore } from "@/store/planner-store";
import { cn } from "@/lib/utils";
import type { ActivityType, LocationResult } from "@/lib/types";

export function ActivityList({ loc }: { loc: LocationResult }) {
  const [preferredTypes, setPreferredTypes] = useState<ActivityType[]>([]);
  const query = useActivitiesQuery(loc, { preferredTypes });

  const preferLlm = usePlannerStore((s) => s.preferLlmActivities[loc.location_id] ?? false);
  const setPreferLlmActivities = usePlannerStore((s) => s.setPreferLlmActivities);
  const clearActivityResultForLocation = usePlannerStore((s) => s.clearActivityResultForLocation);

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-1.5">
        <Sparkles className="text-primary size-4" />
        <span className="text-primary text-xs font-bold tracking-wider uppercase">
          Gợi ý hoạt động
        </span>
        
        <Button
          variant="ghost"
          size="icon"
          onClick={() => {
            setPreferLlmActivities(loc.location_id, !preferLlm);
          }}
          className={cn(
            "size-6 rounded-full border transition-all duration-300 ml-auto shrink-0",
            preferLlm
              ? "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30 hover:bg-purple-500/20"
              : "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20"
          )}
          title={preferLlm ? "Đang dùng AI LLM. Click để dùng Bản đồ thực tế" : "Đang dùng Bản đồ thực tế. Click để dùng AI LLM"}
        >
          <Sparkles className={cn("size-3", preferLlm ? "animate-pulse" : "")} />
        </Button>

        {query.data?.meta ? (
          <Badge
            variant="outline"
            className={cn(
              "text-[9px] px-1.5 shrink-0",
              query.data.meta.fallback_used
                ? "border-amber-400/60 bg-amber-50 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300"
                : "border-primary/30"
            )}
            title={
              query.data.meta.fallback_used
                ? `Bù dữ liệu bằng N5 LLM (${query.data.meta.fallback_n5_count} gợi ý)`
                : "Lấy từ N9-N14 (OSM, Wikidata, ...)"
            }
          >
            ✦ {query.data.meta.fallback_used ? "Map + LLM" : "Map"}
          </Badge>
        ) : null}
      </div>

      <ActivityFilterChips selected={preferredTypes} onChange={setPreferredTypes} />

      {query.isPending ? (
        <ActivitySkeleton />
      ) : query.isError ? (
        <div className="border-destructive/40 bg-destructive/5 text-destructive flex items-start gap-2 rounded-lg border p-3 text-xs">
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <div>
            <div className="font-semibold">Không tải được hoạt động</div>
            <div className="opacity-80">
              {query.error instanceof Error ? query.error.message : "Unknown error"}
            </div>
          </div>
        </div>
      ) : query.data && query.data.activities.length > 0 ? (
        <div className="space-y-2">
          {query.data.activities.slice(0, 5).map((a, i) => (
            <ActivityCard key={`${loc.location_id}-${i}`} activity={a} index={i} />
          ))}
        </div>
      ) : (
        <p className="border-border text-muted-foreground rounded-lg border border-dashed p-3 text-xs">
          Không tìm thấy hoạt động phù hợp.
        </p>
      )}
    </div>
  );
}
