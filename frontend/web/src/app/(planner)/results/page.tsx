import { ModeTabs } from "@/components/header/mode-tabs";
import { ResultView } from "@/components/result/result-view";
import { Badge } from "@/components/ui/badge";

export default function ResultsPage() {
  return (
    <>
      <div className="space-y-3 pt-8 pb-4 text-center">
        <Badge variant="outline" className="border-primary/40 bg-brand-soft text-primary">
          Kết quả từ AI
        </Badge>
        <h1 className="text-foreground text-4xl font-extrabold tracking-tight sm:text-5xl">
          Top 5 điểm đến phù hợp
        </h1>
        <p className="text-muted-foreground mx-auto max-w-xl text-base">
          Tinh chỉnh từng địa điểm hoặc tạo lại toàn bộ lộ trình ở cuối trang.
        </p>
      </div>
      <div className="space-y-5">
        <ModeTabs />
        <ResultView />
      </div>
    </>
  );
}
