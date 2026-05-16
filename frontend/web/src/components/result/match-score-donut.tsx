"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Props = {
  /** 0..1 */
  score: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
};

/**
 * SVG donut chart for match score. Stroke animates from 0 → target in ~800ms.
 * Center label shows just the rounded percent (no extra "Match" sub-label).
 */
export function MatchScoreDonut({ score, size = 64, strokeWidth = 6, className }: Props) {
  const pct = Math.max(0, Math.min(1, score));
  const rounded = Math.round(pct * 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);
  const gradId = `match-grad-${Math.round(pct * 1000)}`;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      aria-label={`Match score ${rounded} percent`}
      title={`Match score ${rounded}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--brand-dim)" />
            <stop offset="100%" stopColor="var(--primary)" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeWidth}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </svg>
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <span className="text-foreground text-[15px] font-extrabold tabular-nums">
          {rounded}
          <span className="text-[10px] font-bold opacity-70">%</span>
        </span>
      </div>
    </div>
  );
}
