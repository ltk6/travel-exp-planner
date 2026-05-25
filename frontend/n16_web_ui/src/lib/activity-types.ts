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

// Pattern: bg-{color}-100 text-{color}-800 border-{color}-400 font-bold — bolder
// and clearer than the previous version (200/700/300) so each type is easy to distinguish on the card.
export const ACTIVITY_TYPE_META: Record<ActivityType, ActivityTypeMeta> = {
  food: {
    label: "Ẩm thực",
    Icon: Utensils,
    classes:
      "bg-amber-100 text-amber-800 border-amber-400 font-bold dark:bg-amber-500/20 dark:text-amber-200 dark:border-amber-500/60",
  },
  adventure: {
    label: "Phiêu lưu",
    Icon: Mountain,
    classes:
      "bg-red-100 text-red-800 border-red-400 font-bold dark:bg-red-500/20 dark:text-red-200 dark:border-red-500/60",
  },
  culture: {
    label: "Văn hoá",
    Icon: Landmark,
    classes:
      "bg-purple-100 text-purple-800 border-purple-400 font-bold dark:bg-purple-500/20 dark:text-purple-200 dark:border-purple-500/60",
  },
  nightlife: {
    label: "Về đêm",
    Icon: Moon,
    classes:
      "bg-indigo-100 text-indigo-800 border-indigo-400 font-bold dark:bg-indigo-500/20 dark:text-indigo-200 dark:border-indigo-500/60",
  },
  shopping: {
    label: "Mua sắm",
    Icon: ShoppingBag,
    classes:
      "bg-pink-100 text-pink-800 border-pink-400 font-bold dark:bg-pink-500/20 dark:text-pink-200 dark:border-pink-500/60",
  },
  relaxation: {
    label: "Thư giãn",
    Icon: Leaf,
    classes:
      "bg-teal-100 text-teal-800 border-teal-400 font-bold dark:bg-teal-500/20 dark:text-teal-200 dark:border-teal-500/60",
  },
  nature: {
    label: "Thiên nhiên",
    Icon: TreePine,
    classes:
      "bg-emerald-100 text-emerald-800 border-emerald-400 font-bold dark:bg-emerald-500/20 dark:text-emerald-200 dark:border-emerald-500/60",
  },
  photography: {
    label: "Chụp ảnh",
    Icon: Camera,
    classes:
      "bg-sky-100 text-sky-800 border-sky-400 font-bold dark:bg-sky-500/20 dark:text-sky-200 dark:border-sky-500/60",
  },
  experience: {
    label: "Trải nghiệm",
    Icon: Sparkle,
    classes:
      "bg-orange-100 text-orange-800 border-orange-400 font-bold dark:bg-orange-500/20 dark:text-orange-200 dark:border-orange-500/60",
  },
};

/** Display order for filter chips — sightseeing first, activities after. */
export const ACTIVITY_TYPE_ORDER: ActivityType[] = [
  "nature",
  "culture",
  "food",
  "adventure",
  "relaxation",
  "nightlife",
  "shopping",
  "photography",
  "experience",
];

const FALLBACK: ActivityTypeMeta = {
  label: "Khác",
  Icon: Sparkle,
  classes: "bg-muted text-muted-foreground border-border",
};

export function metaForActivityType(t: string | undefined | null): ActivityTypeMeta {
  if (!t) return FALLBACK;
  return ACTIVITY_TYPE_META[t as ActivityType] ?? FALLBACK;
}
