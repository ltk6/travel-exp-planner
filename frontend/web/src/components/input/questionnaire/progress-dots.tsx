import { cn } from "@/lib/utils";

type Props = {
  answered: number;
  total: number;
};

export function ProgressDots({ answered, total }: Props) {
  return (
    <div className="space-y-1.5">
      <div className="text-muted-foreground flex items-center justify-between text-xs">
        <span>
          Đã trả lời <span className="text-foreground font-semibold">{answered}</span>/{total} câu
          hỏi
        </span>
        <span className="font-mono text-[10px] tracking-wider uppercase">
          {total > 0 ? Math.round((answered / total) * 100) : 0}%
        </span>
      </div>
      <div className="flex gap-1.5">
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i < answered ? "bg-primary" : "bg-border",
            )}
          />
        ))}
      </div>
    </div>
  );
}
