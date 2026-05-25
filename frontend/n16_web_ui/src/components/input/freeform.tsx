"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { MessageSquareText } from "lucide-react";
import { usePlannerStore } from "@/store/planner-store";

export function Freeform() {
  const value = usePlannerStore((s) => s.freeformText);
  const setValue = usePlannerStore((s) => s.setFreeformText);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 text-primary rounded-lg p-2">
            <MessageSquareText className="size-5" />
          </div>
          <div>
            <CardTitle>Văn bản tự do</CardTitle>
            <CardDescription>Mô tả chuyến đi trong mơ — càng chi tiết càng tốt.</CardDescription>
          </div>
          <Badge variant="outline" className="ml-auto">
            {value.length} ký tự
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ví dụ: Tôi muốn thức dậy bằng tiếng sóng vỗ vào bờ, ăn hải sản tươi sống, đi lặn, và tìm một nơi yên tĩnh để đọc sách..."
          className="min-h-[220px] resize-y text-base leading-relaxed"
        />
      </CardContent>
    </Card>
  );
}
