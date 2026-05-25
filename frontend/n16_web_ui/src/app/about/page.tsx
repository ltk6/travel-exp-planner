import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { ArrowLeft, Compass, Code, Sparkles, MapIcon, Code2 } from "lucide-react";

export default function AboutPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 pt-16 pb-24">
      <div className="space-y-3">
        <Link href="/" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="mr-1.5 size-4" />
          Quay lại trang chủ
        </Link>

        <Badge variant="outline" className="border-primary/40 bg-brand-soft text-primary">
          <Compass className="mr-1 size-3" />
          Về dự án
        </Badge>
        <h1 className="text-foreground text-4xl font-extrabold tracking-tight sm:text-5xl">
          Travel{" "}
          <span className="from-primary via-brand-dim to-teal bg-gradient-to-r bg-clip-text text-transparent">
            Experience
          </span>{" "}
          Planner
        </h1>
        <p className="text-muted-foreground text-base">
          Đồ án CTT009 · Khoa CNTT · Trường ĐH Khoa học Tự nhiên — ĐHQG TP.HCM
        </p>
      </div>

      {/* Image slot — team or product hero */}
      <div className="border-border/60 relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-2xl border bg-white p-2 sm:p-4">
        <img
          src="/about-hero.png"
          alt="Kiến trúc hệ thống Travel Experience Planner"
          className="max-h-full max-w-full object-contain"
        />
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              <Sparkles className="size-5" />
            </div>
            <div>
              <CardTitle>Mục tiêu</CardTitle>
              <CardDescription>
                Gợi ý trải nghiệm du lịch Việt Nam được cá nhân hoá bằng AI
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm leading-relaxed">
          Hệ thống kết hợp <span className="text-foreground">semantic retrieval</span> (embedding
          tiếng Việt), <span className="text-foreground">multimodal input</span> (text · trắc nghiệm
          · hình ảnh) và <span className="text-foreground">LLM-driven activity generation</span> để
          đề xuất 5 địa điểm + 5 hoạt động phù hợp cho mỗi nơi. Người dùng có thể tinh chỉnh kết quả
          qua feedback tự nhiên — pipeline N17 refine input và chạy lại.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              <Code2 className="size-5" />
            </div>
            <div>
              <CardTitle>Stack kỹ thuật</CardTitle>
              <CardDescription>Frontend modern · Backend Flask + LLM chain</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed">
          <div>
            <div className="text-foreground font-semibold">Frontend</div>
            <ul className="text-muted-foreground mt-1 list-inside list-disc space-y-0.5">
              <li>Next.js 16 (App Router) · React 19 · TypeScript</li>
              <li>Tailwind CSS 4 · shadcn/ui · framer-motion</li>
              <li>Zustand (state) · TanStack Query (data) · Zod (schema)</li>
              <li>MapLibre GL + Carto Positron (tích hợp bộ lọc chủ quyền biển đảo Việt Nam)</li>
              <li>Serwist (PWA)</li>
            </ul>
          </div>
          <div>
            <div className="text-foreground font-semibold">Backend</div>
            <ul className="text-muted-foreground mt-1 list-inside list-disc space-y-0.5">
              <li>Flask N8 Orchestrator (port 5000)</li>
              <li>N1 Embedding (BGE-M3) · N2 Image Processing · N3 PostgreSQL</li>
              <li>N4/N6 ranking · N5 activity generation · N17 feedback</li>
              <li>LLM chain: Groq (llama-3.3-70b → qwen-32b → llama-3.1-8b → scout)</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 text-primary rounded-lg p-2">
              <MapIcon className="size-5" />
            </div>
            <div>
              <CardTitle>Chủ quyền biển đảo Việt Nam</CardTitle>
              <CardDescription>Cơ chế định vị và hiển thị chủ quyền tự phát triển</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-muted-foreground text-sm leading-relaxed">
          Hệ thống tích hợp bộ lọc địa giới{" "}
          <span className="text-foreground">applyVnLocalization</span> kết hợp lớp phủ{" "}
          <span className="text-foreground">VnSovereigntyOverlay</span> tự phát triển trên nền bản
          đồ mở. Cơ chế này tự động ẩn các tên gọi quốc tế sai lệch trong khu vực tranh chấp, hiển
          thị đúng chủ quyền của Việt Nam đối với{" "}
          <span className="text-foreground">quần đảo Hoàng Sa</span> và{" "}
          <span className="text-foreground">quần đảo Trường Sa</span> theo đúng quy chuẩn địa giới
          quốc gia.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Thành viên</CardTitle>
          <CardDescription>Nhóm sinh viên Khóa 2024 CNTT — HCMUS</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {[
            ["Huỳnh Huy Hoàng", "24120181"],
            ["Nguyễn Thanh Hải", "24120302"],
            ["Lâm Tuấn Khanh", "24120337"],
            ["Hoàng Lê Đăng Khoa", "24120343"],
            ["Phan Lê Thành Nhân", "24120400"],
            ["Chu Văn Thái", "24120440"],
            ["Nguyễn Việt Thắng", "24120444"],
            ["Trương Huệ Trí", "24120472"],
          ].map(([name, mssv]) => (
            <div
              key={mssv}
              className="border-border/40 flex items-center justify-between border-b py-1 last:border-0"
            >
              <span className="text-foreground">{name}</span>
              <span className="text-muted-foreground font-mono text-xs">{mssv}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      <p className="text-muted-foreground text-center text-xs">
        <Code className="mr-1 inline size-3" />
        Source code trong repo nội bộ HCMUS
      </p>
    </main>
  );
}
