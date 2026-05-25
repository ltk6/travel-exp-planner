"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Loader2, Send, Sparkle } from "lucide-react";
import { useActivityFeedback } from "@/hooks/use-feedback-mutation";
import { usePlannerStore } from "@/store/planner-store";
import type { LocationResult } from "@/lib/types";

type Props = { loc: LocationResult };

export function FeedbackBox({ loc }: Props) {
  const [text, setText] = useState("");
  const userTrace = usePlannerStore((s) => s.results?.trace?.user);
  const mutation = useActivityFeedback(loc.location_id);

  const onSubmit = () => {
    if (!text.trim()) return;
    const store = usePlannerStore.getState();
    const storePayload = store.payload;
    const storeFreeformText = store.freeformText;
    const storeSelectedKeys = store.selectedKeys;
    const preferLlm = store.preferLlmActivities[loc.location_id] ?? false;

    mutation.mutate({
      feedback: text.trim(),
      text: userTrace?.input?.text || storePayload?.text || storeFreeformText || "",
      tags: userTrace?.input?.tags || storePayload?.tags || storeSelectedKeys || [],
      img_desc: userTrace?.n2_image?.img_desc || storePayload?.img_desc || "",
      text_k: userTrace?.n1_embedding?.text_k ?? 0,
      tags_k: userTrace?.n1_embedding?.tags_k ?? 0,
      user_vectors: userTrace?.user_vectors ?? {},
      location: { location_id: loc.location_id, metadata: loc.metadata ?? {} },
      v2: !preferLlm,
      prefer_llm: preferLlm,
    });
    setText("");
  };

  return (
    <div className="border-border bg-card/40 rounded-xl border p-3">
      <div className="text-primary mb-2 flex items-center gap-2 text-[10px] font-bold tracking-wider uppercase">
        <Sparkle className="size-3" />
        Tinh chỉnh hoạt động
      </div>
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Ví dụ: 'Tìm thêm quán cafe có view thung lũng', 'Thêm hoạt động trekking nhẹ cho gia đình'…"
        className="min-h-[72px] resize-y text-xs"
      />
      <Button
        size="sm"
        onClick={onSubmit}
        disabled={!text.trim() || mutation.isPending}
        className="mt-2 w-full"
      >
        {mutation.isPending ? (
          <>
            <Loader2 className="mr-1.5 size-3.5 animate-spin" />
            Đang xử lý…
          </>
        ) : (
          <>
            <Send className="mr-1.5 size-3.5" />
            Cập nhật
          </>
        )}
      </Button>
    </div>
  );
}
