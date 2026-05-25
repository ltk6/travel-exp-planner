import { Badge } from "@/components/ui/badge";
import { Compass } from "lucide-react";

export function TitleBlock() {
  return (
    <div className="relative space-y-6 pt-6 pb-10">
      <div className="border-border/60 relative h-48 w-full overflow-hidden rounded-3xl border shadow-sm sm:h-64">
        <img
          src="/hero-light.jpg"
          alt="Banner du lịch"
          className="block h-full w-full object-cover dark:hidden"
        />
        <img
          src="/hero-dark.png"
          alt="Banner du lịch"
          className="hidden h-full w-full object-cover dark:block"
        />
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
