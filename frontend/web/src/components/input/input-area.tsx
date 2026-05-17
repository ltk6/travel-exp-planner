"use client";

import { AnimatePresence, motion } from "framer-motion";
import { usePlannerStore } from "@/store/planner-store";
import { Questionnaire } from "./questionnaire/questionnaire";
import { Freeform } from "./freeform";
import { ImageUpload } from "./image-upload";

export function InputArea() {
  const tab = usePlannerStore((s) => s.inputTab);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={tab}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
      >
        {tab === "questionnaire" && <Questionnaire />}
        {tab === "freeform" && <Freeform />}
        {tab === "image" && <ImageUpload />}
      </motion.div>
    </AnimatePresence>
  );
}
