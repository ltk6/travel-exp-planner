import {
  Camera,
  Landmark,
  Leaf,
  Moon,
  Mountain,
  ShoppingBag,
  Sparkle,
  TreePine,
  Utensils,
  type LucideIcon,
} from "lucide-react";
import type { ActivityType } from "./types";

/**
 * Maps each of the 9 fixed `activity_type` values from backend N5/N6 to:
 *   - Vietnamese label
 *   - lucide-react icon
 *   - Tailwind class set (statically baked so JIT can detect them)
 *
 * See doc v2.0 §4.4 and backend `n5_activity_generation` for the source list.
 */
export type ActivityTypeMeta = {
  label: string;
  Icon: LucideIcon;
  classes: string;
};

export const ACTIVITY_TYPE_META: Record<ActivityType, ActivityTypeMeta> = {
  food: {
    label: "Ẩm thực",
    Icon: Utensils,
    classes:
      "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-500/15 dark:text-amber-300 dark:border-amber-500/40",
  },
  adventure: {
    label: "Phiêu lưu",
    Icon: Mountain,
    classes:
      "bg-red-100 text-red-700 border-red-300 dark:bg-red-500/15 dark:text-red-300 dark:border-red-500/40",
  },
  culture: {
    label: "Văn hoá",
    Icon: Landmark,
    classes:
      "bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-500/15 dark:text-purple-300 dark:border-purple-500/40",
  },
  nightlife: {
    label: "Về đêm",
    Icon: Moon,
    classes:
      "bg-indigo-100 text-indigo-700 border-indigo-300 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/40",
  },
  shopping: {
    label: "Mua sắm",
    Icon: ShoppingBag,
    classes:
      "bg-pink-100 text-pink-700 border-pink-300 dark:bg-pink-500/15 dark:text-pink-300 dark:border-pink-500/40",
  },
  relaxation: {
    label: "Thư giãn",
    Icon: Leaf,
    classes:
      "bg-teal-100 text-teal-700 border-teal-300 dark:bg-teal-500/15 dark:text-teal-300 dark:border-teal-500/40",
  },
  nature: {
    label: "Thiên nhiên",
    Icon: TreePine,
    classes:
      "bg-emerald-100 text-emerald-700 border-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/40",
  },
  photography: {
    label: "Chụp ảnh",
    Icon: Camera,
    classes:
      "bg-sky-100 text-sky-700 border-sky-300 dark:bg-sky-500/15 dark:text-sky-300 dark:border-sky-500/40",
  },
  experience: {
    label: "Trải nghiệm",
    Icon: Sparkle,
    classes:
      "bg-orange-100 text-orange-700 border-orange-300 dark:bg-orange-500/15 dark:text-orange-300 dark:border-orange-500/40",
  },
};

const FALLBACK: ActivityTypeMeta = {
  label: "Khác",
  Icon: Sparkle,
  classes: "bg-muted text-muted-foreground border-border",
};

export function metaForActivityType(t: string | undefined | null): ActivityTypeMeta {
  if (!t) return FALLBACK;
  return ACTIVITY_TYPE_META[t as ActivityType] ?? FALLBACK;
}
