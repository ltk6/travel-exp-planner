"use client";

import { usePathname, useRouter } from "next/navigation";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePlannerStore, type InputTab } from "@/store/planner-store";
import { ClipboardList, MessageSquareText, ImagePlus, Sparkles } from "lucide-react";

type TabDef =
  | { value: InputTab; label: string; Icon: typeof ClipboardList; kind: "input" }
  | { value: "result"; label: string; Icon: typeof ClipboardList; kind: "result" };

const TABS: TabDef[] = [
  { value: "questionnaire", label: "Trắc nghiệm", Icon: ClipboardList, kind: "input" },
  { value: "freeform", label: "Văn bản", Icon: MessageSquareText, kind: "input" },
  { value: "image", label: "Hình ảnh", Icon: ImagePlus, kind: "input" },
  { value: "result", label: "Kết quả", Icon: Sparkles, kind: "result" },
];

export function ModeTabs() {
  const pathname = usePathname();
  const router = useRouter();
  const inputTab = usePlannerStore((s) => s.inputTab);
  const setInputTab = usePlannerStore((s) => s.setInputTab);
  const hasResults = usePlannerStore((s) => Boolean(s.results));

  const isResultsRoute = pathname === "/results";
  const activeValue = isResultsRoute ? "result" : inputTab;

  const handleChange = (value: string) => {
    if (value === "result") {
      if (hasResults) router.push("/results");
      return;
    }
    setInputTab(value as InputTab);
    if (pathname !== "/") router.push("/");
  };

  return (
    <div className="border-border/60 bg-background/85 supports-[backdrop-filter]:bg-background/60 sticky top-14 z-30 -mx-4 border-b px-4 py-3 backdrop-blur">
      <div className="mx-auto flex max-w-4xl justify-center">
        <Tabs value={activeValue} onValueChange={handleChange}>
          <TabsList variant="default" className="h-10 gap-1 p-1">
            {TABS.map(({ value, label, Icon, kind }) => {
              const disabled = kind === "result" && !hasResults;
              return (
                <TabsTrigger
                  key={value}
                  value={value}
                  disabled={disabled}
                  className="h-8 px-3 text-sm font-medium"
                >
                  <Icon className="mr-1.5 size-4" />
                  <span className="hidden sm:inline">{label}</span>
                </TabsTrigger>
              );
            })}
          </TabsList>
        </Tabs>
      </div>
    </div>
  );
}
