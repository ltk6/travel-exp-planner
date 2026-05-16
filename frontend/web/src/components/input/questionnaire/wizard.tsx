"use client";

import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { QuestionBlock } from "./question-block";
import { QUESTIONNAIRE_CONFIG } from "@/lib/questionnaire-config";
import { allKeysForQuestion } from "@/lib/questionnaire-helpers";
import { usePlannerStore } from "@/store/planner-store";
import { ArrowLeft, ArrowRight, SkipForward } from "lucide-react";

const AUTO_ADVANCE_DELAY_MS = 450;

type Props = {
  idx: number;
  setIdx: (i: number) => void;
};

export function QuestionnaireWizard({ idx, setIdx }: Props) {
  const selectedKeys = usePlannerStore((s) => s.selectedKeys);
  const total = QUESTIONNAIRE_CONFIG.length;
  const current = QUESTIONNAIRE_CONFIG[idx];
  const isFirst = idx === 0;
  const isLast = idx === total - 1;
  const advancedRef = useRef<number>(-1);

  // Auto-advance on single-select questions once the user has picked an option.
  useEffect(() => {
    if (current.multi) return;
    if (advancedRef.current === idx) return; // don't advance same question twice
    const selectedSet = new Set(selectedKeys);
    const hasSelected = allKeysForQuestion(current.id).some((k) => selectedSet.has(k));
    if (!hasSelected) return;
    if (isLast) return;
    const t = setTimeout(() => {
      advancedRef.current = idx;
      setIdx(idx + 1);
    }, AUTO_ADVANCE_DELAY_MS);
    return () => clearTimeout(t);
  }, [current, idx, isLast, selectedKeys, setIdx]);

  const goPrev = () => {
    if (!isFirst) setIdx(idx - 1);
  };
  const goNext = () => {
    if (!isLast) setIdx(idx + 1);
  };

  return (
    <div className="space-y-6">
      <AnimatePresence mode="wait">
        <motion.div
          key={idx}
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -24 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
        >
          <QuestionBlock question={current} index={idx} />
        </motion.div>
      </AnimatePresence>

      <div className="border-border/60 flex items-center justify-between gap-3 border-t pt-4">
        <Button variant="outline" size="sm" onClick={goPrev} disabled={isFirst}>
          <ArrowLeft className="mr-1.5 size-3.5" />
          Quay lại
        </Button>

        <span className="text-muted-foreground text-xs">
          {!current.multi
            ? "Single-select · tự chuyển khi chọn xong"
            : "Multi-select · bấm Tiếp tục khi xong"}
        </span>

        {isLast ? (
          <Button variant="ghost" size="sm" disabled className="invisible">
            <SkipForward className="size-3.5" />
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={goNext}>
              <SkipForward className="mr-1.5 size-3.5" />
              Bỏ qua
            </Button>
            <Button size="sm" onClick={goNext}>
              Tiếp tục
              <ArrowRight className="ml-1.5 size-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
