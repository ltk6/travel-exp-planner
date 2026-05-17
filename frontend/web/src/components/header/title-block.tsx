import { Badge } from "@/components/ui/badge";
import { Compass } from "lucide-react";

export function TitleBlock() {
  return (
    <div className="relative space-y-6 pt-6 pb-10">
      {/* Hero image slot — replace with <img src="/hero.jpg" .../> */}
      <div className="image-slot border-border/60 relative h-48 w-full overflow-hidden rounded-3xl border shadow-sm sm:h-64">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-background/80 text-muted-foreground rounded-2xl px-4 py-3 text-center text-xs font-medium backdrop-blur">
            📸 Chèn ảnh hero (banner du lịch) tại đây
            <div className="mt-0.5 font-mono text-[10px] opacity-70">
              ~ 1600×600 · /public/hero.jpg
            </div>
          </div>
        </div>
        {/* Decorative blobs */}
        <div className="bg-brand-soft absolute -top-10 -right-10 size-40 rounded-full blur-3xl" />
        <div className="bg-teal-soft absolute -bottom-12 -left-12 size-48 rounded-full blur-3xl" />
      </div>

      <div className="space-y-3 text-center">
        <Badge variant="outline" className="border-primary/40 bg-brand-soft text-primary">
          <Compass className="mr-1 size-3" />
          AI · Vietnamese travel
        </Badge>
        <h1 className="text-foreground text-4xl font-extrabold tracking-tight sm:text-5xl">
          Travel{" "}
          <span className="from-primary via-brand-dim to-teal bg-gradient-to-r bg-clip-text text-transparent">
            Experience
          </span>{" "}
          Planner
        </h1>
        <p className="text-muted-foreground mx-auto max-w-xl text-base">
          Hãy trả lời trắc nghiệm, viết vài dòng hoặc tải lên hình ảnh — chúng tôi gợi ý những trải
          nghiệm du lịch dành riêng cho bạn.
        </p>
      </div>
    </div>
  );
}
