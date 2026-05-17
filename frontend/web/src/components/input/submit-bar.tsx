"use client";

import { Button } from "@/components/ui/button";
import { Loader2, RotateCcw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { usePlannerStore } from "@/store/planner-store";
import { useRecommendMutation } from "@/hooks/use-recommend-mutation";
import { deriveTags } from "@/lib/questionnaire-helpers";
import type { RecommendPayload } from "@/lib/types";

export function SubmitBar() {
  const selectedKeys = usePlannerStore((s) => s.selectedKeys);
  const text = usePlannerStore((s) => s.freeformText);
  const images = usePlannerStore((s) => s.imagesB64);
  const reset = usePlannerStore((s) => s.reset);

  const mutation = useRecommendMutation();

  const tags = deriveTags(selectedKeys);
  const hasAnyInput = tags.length > 0 || text.trim().length > 0 || images.length > 0;

  const onSubmit = () => {
    if (!hasAnyInput) {
      toast.warning("Cần ít nhất 1 input.", {
        description: "Hãy chọn tag, viết mô tả, hoặc tải lên 1 ảnh.",
      });
      return;
    }
    const payload: RecommendPayload = {
      text: text.trim(),
      image: images[0] ?? "",
      tags,
      constraints: {},
    };
    mutation.mutate(payload);
  };

  const onReset = () => {
    reset();
    toast.success("Đã đặt lại toàn bộ.");
  };

  return (
    <div className="border-border/60 bg-background/85 supports-[backdrop-filter]:bg-background/70 sticky bottom-4 z-20 mt-6 flex items-stretch gap-3 rounded-2xl border p-2 shadow-xl backdrop-blur">
      <Button
        size="lg"
        onClick={onSubmit}
        disabled={mutation.isPending}
        className="shadow-primary/20 h-14 flex-1 rounded-xl text-base font-semibold shadow-lg"
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="mr-2 size-5 animate-spin" />
            Đang phân tích hồ sơ du lịch…
          </>
        ) : (
          <>
            <Sparkles className="mr-2 size-5" />
            Gợi ý trải nghiệm du lịch
          </>
        )}
      </Button>
      <Button
        size="lg"
        variant="outline"
        onClick={onReset}
        disabled={mutation.isPending}
        className="h-14 rounded-xl"
        title="Đặt lại toàn bộ"
      >
        <RotateCcw className="size-5" />
        <span className="ml-2 hidden sm:inline">Đặt lại</span>
      </Button>
    </div>
  );
}
