"use client";

import { usePlannerStore } from "@/store/planner-store";
import { deriveTags } from "@/lib/questionnaire-helpers";
import { Hash, ImageIcon, Type } from "lucide-react";
import { cn } from "@/lib/utils";

export function StatsBar() {
  const selectedKeys = usePlannerStore((s) => s.selectedKeys);
  const text = usePlannerStore((s) => s.freeformText);
  const images = usePlannerStore((s) => s.imagesB64);
  const tags = deriveTags(selectedKeys);

  const stats = [
    { Icon: Hash, value: tags.length, label: "tags", active: tags.length > 0 },
    { Icon: Type, value: text.trim().length, label: "ký tự", active: text.trim().length > 0 },
    { Icon: ImageIcon, value: images.length, label: "ảnh", active: images.length > 0 },
  ];

  return (
    <div className="flex items-center justify-center gap-2 text-xs">
      {stats.map(({ Icon, value, label, active }) => (
        <div
          key={label}
          className={cn(
            "flex items-center gap-1.5 rounded-full border px-2.5 py-1 transition-colors",
            active
              ? "border-primary/40 bg-primary/10 text-primary"
              : "border-border/60 bg-muted/30 text-muted-foreground",
          )}
        >
          <Icon className="size-3" />
          <span className="font-mono font-semibold tabular-nums">{value}</span>
          <span className="text-[10px] tracking-wider uppercase">{label}</span>
        </div>
      ))}
    </div>
  );
}
