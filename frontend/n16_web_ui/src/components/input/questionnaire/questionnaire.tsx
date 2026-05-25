"use client";

import { useState } from "react";
import { QUESTIONNAIRE_CONFIG } from "@/lib/questionnaire-config";
import { countAnswered } from "@/lib/questionnaire-helpers";
import { usePlannerStore } from "@/store/planner-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProgressDots } from "./progress-dots";
import { QuestionBlock } from "./question-block";
import { QuestionnaireWizard } from "./wizard";
import { TagSummary } from "./tag-summary";
import { Separator } from "@/components/ui/separator";
import { List, PlayCircle } from "lucide-react";
import { cn } from "@/lib/utils";

type ViewMode = "scroll" | "wizard";

export function Questionnaire() {
  const selected = usePlannerStore((s) => s.selectedKeys);
  const answered = countAnswered(selected);
  const total = QUESTIONNAIRE_CONFIG.length;

  const [viewMode, setViewMode] = useState<ViewMode>("scroll");
  const [wizardIdx, setWizardIdx] = useState(0);

  return (
    <Card>
      <CardContent className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <ProgressDots answered={answered} total={total} />
          <ViewModeToggle viewMode={viewMode} setViewMode={setViewMode} />
        </div>

        {viewMode === "scroll" ? (
          <div className="space-y-8">
            {QUESTIONNAIRE_CONFIG.map((q, i) => (
              <div key={q.id} className="space-y-4">
                <QuestionBlock question={q} index={i} />
                {i < total - 1 && <Separator className="mt-6" />}
              </div>
            ))}
          </div>
        ) : (
          <QuestionnaireWizard idx={wizardIdx} setIdx={setWizardIdx} />
        )}

        <TagSummary />
      </CardContent>
    </Card>
  );
}

function ViewModeToggle({
  viewMode,
  setViewMode,
}: {
  viewMode: ViewMode;
  setViewMode: (m: ViewMode) => void;
}) {
  return (
    <div className="border-border bg-muted/30 inline-flex items-center rounded-full border p-0.5">
      <ViewModeButton active={viewMode === "scroll"} onClick={() => setViewMode("scroll")}>
        <List className="size-3.5" />
        <span className="hidden sm:inline">Cuộn dọc</span>
      </ViewModeButton>
      <ViewModeButton active={viewMode === "wizard"} onClick={() => setViewMode("wizard")}>
        <PlayCircle className="size-3.5" />
        <span className="hidden sm:inline">Wizard</span>
      </ViewModeButton>
    </div>
  );
}

function ViewModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      className={cn("gap-1.5 rounded-full", active && "bg-background text-foreground shadow-sm")}
    >
      {children}
    </Button>
  );
}
