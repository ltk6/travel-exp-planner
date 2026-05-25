"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Props = { score: number; label?: string; className?: string };

export function ScoreBar({ score, label = "Match score", className }: Props) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  return (
    <div className={cn("space-y-1", className)}>
      <div className="text-muted-foreground flex items-center justify-between text-[10px] font-semibold tracking-wider uppercase">
        <span>{label}</span>
        <span className="text-foreground font-mono">{score.toFixed(2)}</span>
      </div>
      <div className="bg-border h-1.5 overflow-hidden rounded-full">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="from-brand-dim to-primary h-full rounded-full bg-gradient-to-r"
        />
      </div>
    </div>
  );
}
