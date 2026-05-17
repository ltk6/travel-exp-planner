"use client";

import Link from "next/link";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MessageSquareDashed, Send, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function FeedbackPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [text, setText] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.info("Form chưa kết nối backend", {
      description:
        "Đây là placeholder. Endpoint /feedback (cho app feedback) sẽ được phát triển sau.",
    });
  };

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 pt-12 pb-24">
      <div className="space-y-3">
        <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-1.5 size-4" />
          Quay lại trang chủ
        </Link>

        <Badge variant="outline" className="border-primary/40 bg-brand-soft text-primary">
          <MessageSquareDashed className="mr-1 size-3" />
          Đang phát triển
        </Badge>
        <h1 className="text-foreground text-4xl font-extrabold tracking-tight sm:text-5xl">
          Gửi{" "}
          <span className="from-primary to-teal bg-gradient-to-r bg-clip-text text-transparent">
            feedback
          </span>
        </h1>
        <p className="text-muted-foreground text-base">
          Bạn có ý tưởng cải thiện hệ thống? Tìm thấy bug? Phản hồi của bạn sẽ giúp chúng tôi nâng
          cấp Travel Planner ở các phiên bản sau.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              <Sparkles className="size-5" />
            </div>
            <div>
              <CardTitle>Ý kiến của bạn</CardTitle>
              <CardDescription>
                Form chưa kết nối backend. Khi sẵn sàng sẽ gửi về Google Form / email nhóm.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="name">Họ tên (tuỳ chọn)</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nguyễn Văn A"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email (tuỳ chọn)</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="example@hcmus.edu.vn"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="text">Nội dung *</Label>
              <Textarea
                id="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ví dụ: 'Map bị lag khi zoom quá xa', 'Muốn thêm filter theo ngân sách', 'Đề xuất...' "
                className="min-h-[140px] resize-y"
                required
              />
            </div>
            <Button type="submit" disabled={!text.trim()} className="w-full sm:w-auto">
              <Send className="mr-2 size-4" />
              Gửi feedback
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">Hoặc liên hệ trực tiếp</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground space-y-1 text-sm">
          <p>
            📧 Email nhóm: <span className="text-foreground font-mono">tba@hcmus.edu.vn</span>
          </p>
          <p>💬 GitHub Issues: trong repo nội bộ HCMUS</p>
        </CardContent>
      </Card>
    </main>
  );
}
