"use client";

import { Badge } from "@/components/ui/badge";
import { usePlannerStore } from "@/store/planner-store";
import { deriveTags } from "@/lib/questionnaire-helpers";
import { AnimatePresence, motion } from "framer-motion";

export function TagSummary() {
  const selectedKeys = usePlannerStore((s) => s.selectedKeys);
  const tags = deriveTags(selectedKeys);
  if (tags.length === 0) return null;

  return (
    <div className="border-primary/20 bg-primary/5 rounded-xl border p-3">
      <div className="text-primary mb-2 flex items-center gap-2 text-xs font-semibold tracking-wider uppercase">
        <span>{tags.length} tag đã chọn</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        <AnimatePresence>
          {tags.map((t) => (
            <motion.div
              key={t}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
            >
              <Badge variant="outline" className="border-primary/40 bg-background text-primary">
                {t}
              </Badge>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
