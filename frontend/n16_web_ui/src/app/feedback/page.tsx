"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, MessageSquareDashed, Send, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";

export default function FeedbackPage() {
  const { user } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);

  // Default Name field to username if logged in
  useEffect(() => {
    if (user?.username) {
      setName(user.username);
    }
  }, [user]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;

    setLoading(true);
    try {
      const res = await apiClient.submitAppFeedback({
        name: name.trim() || undefined,
        email: email.trim() || undefined,
        content: text.trim(),
      });

      if (res.status === "success") {
        toast.success("Cảm ơn bạn đã gửi feedback!", {
          description: "Phản hồi của bạn đã được ghi nhận trực tiếp vào hệ thống.",
        });
        setText("");
      } else {
        toast.error("Không gửi được feedback", {
          description: res.message || "Vui lòng thử lại sau.",
        });
      }
    } catch (err) {
      toast.error("Không gửi được feedback", {
        description: err instanceof Error ? err.message : "Không thể kết nối đến máy chủ",
      });
    } finally {
      setLoading(false);
    }
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
          Phản hồi hệ thống
        </Badge>
        <h1 className="text-foreground text-4xl font-extrabold tracking-tight sm:text-5xl">
          Gửi{" "}
          <span className="from-primary to-teal bg-gradient-to-r bg-clip-text text-transparent">
            feedback
          </span>
        </h1>
        <p className="text-muted-foreground text-base">
          Bạn có ý tưởng cải thiện hệ thống hoặc tìm thấy lỗi? Phản hồi nhanh của bạn sẽ giúp chúng tôi nâng
          cấp Travel Planner tốt hơn mỗi ngày.
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
                Viết ý kiến bên dưới để gửi trực tiếp phản hồi của bạn đến đội ngũ phát triển.
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
                  disabled={loading}
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
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="text">Nội dung phản hồi *</Label>
              <Textarea
                id="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ví dụ: 'Bản đồ tải chậm khi zoom xa', 'Muốn thêm chức năng lọc theo chi phí', 'Đề xuất ý tưởng...'"
                className="min-h-[160px] resize-y text-base"
                required
                disabled={loading}
              />
            </div>
            <Button type="submit" disabled={!text.trim() || loading} className="w-full sm:w-auto">
              {loading ? (
                <Loader2 className="mr-2 size-4 animate-spin" />
              ) : (
                <Send className="mr-2 size-4" />
              )}
              Gửi feedback
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
