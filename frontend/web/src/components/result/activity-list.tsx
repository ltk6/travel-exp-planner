"use client";

import { Badge } from "@/components/ui/badge";
import { ActivityCard } from "./activity-card";
import { ActivitySkeleton } from "./activity-skeleton";
import { useActivitiesQuery } from "@/hooks/use-activities-query";
import type { LocationResult } from "@/lib/types";
import { AlertCircle, Sparkles } from "lucide-react";

export function ActivityList({ loc }: { loc: LocationResult }) {
  const query = useActivitiesQuery(loc);

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-2">
        <Sparkles className="text-primary size-4" />
        <span className="text-primary text-xs font-bold tracking-wider uppercase">
          Gợi ý hoạt động
        </span>
        {query.data?.meta?.provider_used ? (
          <Badge variant="outline" className="border-primary/30 ml-auto text-[10px]">
            ✦ {query.data.meta.provider_used}
            {query.data.meta.model_used ? ` · ${query.data.meta.model_used.split("/").pop()}` : ""}
          </Badge>
        ) : null}
      </div>

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
