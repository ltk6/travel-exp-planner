"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { metaForActivityType } from "@/lib/activity-types";
import { cn } from "@/lib/utils";
import type { ActivityResult } from "@/lib/types";

export function ActivityCard({ activity, index }: { activity: ActivityResult; index: number }) {
  const meta = activity.metadata ?? {};
  const name = meta.name ?? "Hoạt động";
  const typeMeta = metaForActivityType(meta.activity_type);
  const desc = meta.description;
  const Icon = typeMeta.Icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: index * 0.04 }}
      className="border-border bg-card/70 hover:border-primary/30 rounded-lg border p-3.5 transition-colors"
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-foreground text-base leading-tight font-semibold">{name}</div>
        <Badge
          variant="outline"
          className="border-primary/40 bg-primary/10 text-primary font-mono text-sm"
        >
          {activity.score.toFixed(2)}
        </Badge>
      </div>
      {meta.activity_type ? (
        <Badge
          variant="outline"
          className={cn("mt-1.5 inline-flex items-center gap-1 border", typeMeta.classes)}
        >
          <Icon className="size-3" />
          <span className="text-[11px] font-semibold tracking-wider uppercase">
            {typeMeta.label}
          </span>
        </Badge>
      ) : null}
      {activity.reason ? (
        <p className="text-muted-foreground mt-2 text-sm leading-relaxed">💡 {activity.reason}</p>
      ) : null}
      {desc ? (
        <p className="text-muted-foreground/80 mt-1 text-sm leading-relaxed">{desc}</p>
      ) : null}
    </motion.div>
  );
}
