"use client";

import { motion } from "framer-motion";
import { Clock, ExternalLink, Home, MapPin, Star, Trees } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { metaForActivityType } from "@/lib/activity-types";
import { cn } from "@/lib/utils";
import { labelForTag } from "@/lib/tag-map";
import type { ActivityResult } from "@/lib/types";

// Wikimedia returns http URLs; upgrade so the page can load them over https.
function toHttps(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  return url.startsWith("http://") ? "https://" + url.slice("http://".length) : url;
}

function formatDistance(m: number | null | undefined): string | null {
  if (m == null || !Number.isFinite(m)) return null;
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

export function ActivityCard({ activity, index }: { activity: ActivityResult; index: number }) {
  const meta = activity.metadata ?? {};
  const name = meta.name ?? "Hoạt động";
  const typeMeta = metaForActivityType(meta.activity_type);
  const desc = meta.description;
  const Icon = typeMeta.Icon;

  const imgSrc = toHttps(meta.image_url);
  const distance = formatDistance(meta.distance_m);
  const websiteHref = toHttps(meta.website);
  const tagList = (meta.tags ?? []).filter(Boolean).slice(0, 3);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="border-border bg-card/70 hover:border-primary/30 overflow-hidden rounded-lg border transition-colors"
    >
      <div className="p-3.5">
        <div className="flex items-baseline justify-between gap-2">
          <div className="text-foreground text-base leading-tight font-semibold">{name}</div>
          <Badge
            variant="outline"
            className="border-primary/40 bg-primary/10 text-primary font-mono text-sm"
          >
            {activity.score.toFixed(2)}
          </Badge>
        </div>

        <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
          {meta.activity_type ? (
            <Badge
              variant="outline"
              className={cn("inline-flex items-center gap-1 border", typeMeta.classes)}
            >
              <Icon className="size-3" />
              <span className="text-[11px] font-semibold tracking-wider uppercase">
                {typeMeta.label}
              </span>
            </Badge>
          ) : null}

          {meta.rating != null ? (
            <Badge variant="outline" className="border-amber-400/50 bg-amber-50 text-amber-700">
              <Star className="size-3 fill-current" />
              <span className="font-mono text-[11px]">{meta.rating.toFixed(1)}</span>
            </Badge>
          ) : null}

          {distance ? (
            <Badge variant="outline" className="text-muted-foreground">
              <MapPin className="size-3" />
              <span className="text-[11px]">{distance}</span>
            </Badge>
          ) : null}

          {meta.indoor_outdoor === "indoor" ? (
            <Badge variant="outline" className="text-muted-foreground">
              <Home className="size-3" />
              <span className="text-[11px]">Trong nhà</span>
            </Badge>
          ) : meta.indoor_outdoor === "outdoor" ? (
            <Badge variant="outline" className="text-muted-foreground">
              <Trees className="size-3" />
              <span className="text-[11px]">Ngoài trời</span>
            </Badge>
          ) : meta.indoor_outdoor === "mixed" ? (
            <Badge variant="outline" className="text-muted-foreground">
              <Home className="size-3" />
              <span className="text-[11px]">Trong &amp; ngoài</span>
            </Badge>
          ) : null}
        </div>

        {desc ? (
          <p className="text-muted-foreground mt-2 text-sm leading-relaxed">{desc}</p>
        ) : activity.reason ? (
          <p className="text-muted-foreground mt-2 text-sm leading-relaxed">💡 {activity.reason}</p>
        ) : null}

        {meta.opening_hours ? (
          <p className="text-muted-foreground/80 mt-2 flex items-start gap-1.5 text-xs">
            <Clock className="mt-0.5 size-3 shrink-0" />
            <span>{meta.opening_hours}</span>
          </p>
        ) : null}

        {tagList.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1">
            {tagList.map((t) => (
              <Badge key={t} variant="ghost" className="text-muted-foreground text-[10px]">
                {labelForTag(t)}
              </Badge>
            ))}
          </div>
        ) : null}

        {(websiteHref || meta.source) && (
          <div className="text-muted-foreground/70 mt-2.5 flex items-center justify-between gap-2 text-[10px]">
            {websiteHref ? (
              <a
                href={websiteHref}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary inline-flex items-center gap-1 underline-offset-2 hover:underline"
              >
                <ExternalLink className="size-3" />
                Website
              </a>
            ) : (
              <span />
            )}
            {meta.source ? (
              <span className="font-mono tracking-wide uppercase">via {meta.source}</span>
            ) : null}
          </div>
        )}
      </div>
    </motion.div>
  );
}
