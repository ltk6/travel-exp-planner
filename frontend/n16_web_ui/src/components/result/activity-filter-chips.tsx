"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { ACTIVITY_TYPE_META, ACTIVITY_TYPE_ORDER } from "@/lib/activity-types";
import { cn } from "@/lib/utils";
import type { ActivityType } from "@/lib/types";

type Props = {
  selected: ActivityType[];
  onChange: (next: ActivityType[]) => void;
};

/**
 * Hàng chip toggle để user "tinh chỉnh" hoạt động cho 1 location:
 *   - chip không chọn → outline, icon mờ
 *   - chip đã chọn → fill bằng màu của type, có icon ✓
 *   - chọn ≥1 chip → query refetch với preferred_types (backend boost 70/30)
 *   - không chọn gì → trở về cân bằng mặc định (sightseeing 40%)
 */
export function ActivityFilterChips({ selected, onChange }: Props) {
  const toggle = (t: ActivityType) => {
    onChange(selected.includes(t) ? selected.filter((x) => x !== t) : [...selected, t]);
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-muted-foreground mr-1 text-[10px] font-semibold tracking-wider uppercase">
        Ưu tiên
      </span>
      {ACTIVITY_TYPE_ORDER.map((t) => {
        const meta = ACTIVITY_TYPE_META[t];
        const Icon = meta.Icon;
        const isOn = selected.includes(t);
        return (
          <motion.button
            key={t}
            type="button"
            whileTap={{ scale: 0.94 }}
            onClick={() => toggle(t)}
            className={cn(
              "inline-flex h-6 items-center gap-1 rounded-full border px-2 text-[11px] transition-colors",
              isOn
                ? meta.classes
                : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
            aria-pressed={isOn}
          >
            {isOn ? <Check className="size-3" /> : <Icon className="size-3" />}
            <span className="font-semibold tracking-wide uppercase">{meta.label}</span>
          </motion.button>
        );
      })}
      {selected.length > 0 ? (
        <button
          type="button"
          onClick={() => onChange([])}
          className="text-muted-foreground hover:text-foreground ml-1 inline-flex items-center gap-1 text-[10px] underline-offset-2 hover:underline"
        >
          <X className="size-3" />
          Xoá
        </button>
      ) : null}
    </div>
  );
}
