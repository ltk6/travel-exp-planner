"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Loader2, Repeat2, RefreshCw } from "lucide-react";
import { useRecommendFeedback } from "@/hooks/use-feedback-mutation";
import { usePlannerStore } from "@/store/planner-store";

export function GlobalFeedback() {
  const [text, setText] = useState("");
  const userTrace = usePlannerStore((s) => s.results?.trace?.user);
  const mutation = useRecommendFeedback();

  const onSubmit = () => {
    if (!text.trim() || !userTrace) return;
    mutation.mutate({
      feedback: text.trim(),
      user_input: {
        text: userTrace.input?.text ?? "",
        tags: userTrace.input?.tags ?? [],
        img_desc: userTrace.n2_image?.img_desc ?? "",
      },
      image: "",
      constraints: userTrace.input?.constraints ?? {},
      context: userTrace.input?.context ?? {},
    });
    setText("");
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 text-primary rounded-lg p-2">
            <Repeat2 className="size-5" />
          </div>
          <div>
            <CardTitle>Thay đổi toàn bộ lộ trình?</CardTitle>
            <CardDescription>
              Gửi yêu cầu mới — AI tính toán lại toàn bộ theo gu của bạn (xóa lộ trình hiện tại).
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ví dụ: 'Tôi muốn tìm những nơi yên tĩnh và ít khách du lịch hơn', 'Đổi sang điểm đến gần biển', hoặc 'Tối ưu lộ trình với ngân sách tiết kiệm'…"
          className="min-h-[100px] resize-y"
        />
        <Button onClick={onSubmit} disabled={!text.trim() || mutation.isPending} className="w-full">
          {mutation.isPending ? (
            <>
              <Loader2 className="mr-2 size-4 animate-spin" />
              Đang tính toán lại lộ trình…
            </>
          ) : (
            <>
              <RefreshCw className="mr-2 size-4" />
              Cập nhật toàn bộ lộ trình
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
