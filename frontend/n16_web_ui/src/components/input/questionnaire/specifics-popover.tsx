"use client";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, Settings2 } from "lucide-react";
import { OptionCard } from "./option-card";
import { optionKey, specificKeysForSection } from "@/lib/questionnaire-helpers";
import { usePlannerStore } from "@/store/planner-store";
import type { QuestionSection } from "@/lib/questionnaire-config";
import { SPECIFICS_MAX } from "@/lib/questionnaire-config";

type Props = {
  qId: string;
  specifics: QuestionSection;
};

export function SpecificsPopover({ qId, specifics }: Props) {
  const selected = usePlannerStore((s) => s.selectedKeys);
  const selectedSet = new Set(selected);

  let totalSelected = 0;
  for (const section of Object.keys(specifics)) {
    for (const key of specificKeysForSection(qId, section)) {
      if (selectedSet.has(key)) totalSelected += 1;
    }
  }

  return (
    <Popover>
      <PopoverTrigger
        render={(props) => (
          <Button
            {...props}
            variant="outline"
            size="lg"
            className="h-12 w-full justify-between rounded-xl"
          >
            <span className="flex items-center gap-2">
              <Settings2 className="size-4" />
              <span className="text-sm font-medium">Tùy chọn chi tiết</span>
              {totalSelected > 0 && (
                <Badge variant="outline" className="border-primary/40 text-primary">
                  {totalSelected} đã chọn
                </Badge>
              )}
            </span>
            <ChevronDown className="size-4 opacity-60" />
          </Button>
        )}
      />
      <PopoverContent className="w-[min(560px,calc(100vw-2rem))] overflow-hidden p-0">
        <div className="max-h-[60vh] overflow-y-auto p-4">
          <div className="space-y-5">
            {Object.entries(specifics).map(([section, opts]) => (
              <SpecificsSection key={section} qId={qId} section={section} opts={opts} />
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function SpecificsSection({
  qId,
  section,
  opts,
}: {
  qId: string;
  section: string;
  opts: Record<string, string[]>;
}) {
  const selected = usePlannerStore((s) => s.selectedKeys);
  const toggle = usePlannerStore((s) => s.toggleKey);
  const selectedSet = new Set(selected);
  const sectionKeys = specificKeysForSection(qId, section);
  const count = sectionKeys.filter((k) => selectedSet.has(k)).length;
  const remaining = SPECIFICS_MAX - count;

  return (
    <div className="space-y-2.5">
      <div className="border-primary/30 flex items-center justify-between border-b pb-1.5">
        <h4 className="text-foreground text-sm font-bold">{section}</h4>
        <span className="text-primary text-[10px] font-semibold tracking-wider uppercase">
          {remaining > 0
            ? `còn ${remaining}/${SPECIFICS_MAX}`
            : `đủ ${SPECIFICS_MAX}/${SPECIFICS_MAX}`}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {Object.keys(opts).map((opt) => {
          const key = optionKey(qId, "spec", section, opt);
          const checked = selectedSet.has(key);
          const disabled = count >= SPECIFICS_MAX && !checked;
          return (
            <OptionCard
              key={key}
              label={opt}
              checked={checked}
              disabled={disabled}
              onToggle={() => toggle(key)}
            />
          );
        })}
      </div>
    </div>
  );
}
