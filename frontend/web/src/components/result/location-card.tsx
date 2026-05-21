"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MatchScoreDonut } from "./match-score-donut";
import { ActivityList } from "./activity-list";
import { FeedbackBox } from "./feedback-box";
import { labelForTag } from "@/lib/tag-map";
import { usePlannerStore } from "@/store/planner-store";
import type { LocationResult } from "@/lib/types";
import { MapPin } from "lucide-react";

const TAG_DISPLAY_LIMIT = 5;

export function LocationCard({ loc, rank }: { loc: LocationResult; rank: number }) {
  const meta = loc.metadata ?? {};
  const name = meta.name ?? loc.location_id;
  const desc = meta.description ?? "";
  const img = loc.images?.[0];
  const tags = Array.isArray(meta.tags) ? (meta.tags as string[]) : [];
  const visibleTags = tags.slice(0, TAG_DISPLAY_LIMIT);
  const overflow = Math.max(0, tags.length - TAG_DISPLAY_LIMIT);
  const hasGeo = typeof loc.geo?.lat === "number" && typeof loc.geo?.lng === "number";
  const setFocusedLocation = usePlannerStore((s) => s.setFocusedLocation);

  const showOnMap = () => {
    setFocusedLocation(loc.location_id);
    if (typeof document !== "undefined") {
      document.getElementById("result-map")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <motion.div
      id={`loc-${loc.location_id}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: rank * 0.06 }}
    >
      <Card className="scroll-mt-24 overflow-hidden">
        <div className="grid grid-cols-1 gap-0 lg:grid-cols-[5fr_4fr]">
          {/* Left — Location */}
          <div className="flex flex-col">
            <div className="from-primary to-brand-dim relative aspect-video w-full overflow-hidden bg-gradient-to-br">
              {img ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={img} alt={name} className="size-full object-cover" loading="lazy" />
              ) : (
                <div className="flex size-full items-center justify-center text-5xl">🌏</div>
              )}
              {/* Rank badge — top-left */}
              <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-2.5 py-1 text-xs font-bold text-white backdrop-blur">
                <span className="bg-primary flex size-5 items-center justify-center rounded-full text-[10px]">
                  {rank}
                </span>
                <span>Top {rank}</span>
              </div>
              {/* Match score donut — top-right */}
              <div className="bg-background/90 absolute top-2.5 right-2.5 rounded-full p-1 shadow-md backdrop-blur">
                <MatchScoreDonut score={loc.score ?? 0} size={62} />
              </div>
              {/* Geo coords — bottom-right */}
              {loc.geo?.lat && loc.geo?.lng ? (
                <Badge
                  variant="outline"
                  className="absolute right-3 bottom-3 border-white/30 bg-black/60 font-mono text-white"
                  title={`${loc.geo.lat.toFixed(4)}, ${loc.geo.lng.toFixed(4)}`}
                >
                  <MapPin className="mr-1 size-3" />
                  {loc.geo.lat.toFixed(2)}, {loc.geo.lng.toFixed(2)}
                </Badge>
              ) : null}
            </div>

            <CardContent className="flex flex-1 flex-col gap-3.5 p-5">
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-foreground text-2xl leading-tight font-bold">{name}</h3>
                {hasGeo ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={showOnMap}
                    title="Hiển thị địa điểm này trên bản đồ"
                    className="shrink-0"
                  >
                    <MapPin className="size-3.5" />
                    Trên bản đồ
                  </Button>
                ) : null}
              </div>
              {loc.reason ? (
                <div className="border-primary bg-primary/5 rounded-lg border-l-2 p-3 text-sm leading-relaxed">
                  💡 {loc.reason}
                </div>
              ) : null}
              {desc ? (
                <p className="text-muted-foreground text-base leading-relaxed">{desc}</p>
              ) : null}
              {visibleTags.length > 0 ? (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {visibleTags.map((t) => (
                    <Badge
                      key={t}
                      variant="outline"
                      className="border-teal/40 bg-teal-soft text-foreground text-sm"
                    >
                      {labelForTag(t)}
                    </Badge>
                  ))}
                  {overflow > 0 ? (
                    <Badge
                      variant="outline"
                      className="border-border bg-muted text-muted-foreground text-sm"
                    >
                      +{overflow}
                    </Badge>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </div>

          {/* Right — Activities + Feedback */}
          <div className="border-border bg-muted/20 flex flex-col gap-4 border-t p-5 lg:border-t-0 lg:border-l">
            <ActivityList loc={loc} />
            <FeedbackBox loc={loc} />
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
