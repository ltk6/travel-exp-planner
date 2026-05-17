"use client";

import { OptionCard } from "./option-card";
import { SpecificsPopover } from "./specifics-popover";
import { categoryKeysFor, optionKey } from "@/lib/questionnaire-helpers";
import { usePlannerStore } from "@/store/planner-store";
import type { Question } from "@/lib/questionnaire-config";

type Props = { question: Question; index: number };

export function QuestionBlock({ question, index }: Props) {
  const selected = usePlannerStore((s) => s.selectedKeys);
  const toggle = usePlannerStore((s) => s.toggleKey);
  const setExclusive = usePlannerStore((s) => s.setKeysExclusive);
  const setKeyOn = usePlannerStore((s) => s.setKeyOn);

  const selectedSet = new Set(selected);
  const allCatKeys = categoryKeysFor(question.id);
  const catCount = allCatKeys.filter((k) => selectedSet.has(k)).length;
  const max = question.maxSelect;
  const remaining = max ? max - catCount : null;

  return (
    <section className="space-y-4">
      <div className="space-y-1.5">
        <div className="text-primary flex items-center gap-2 text-xs font-semibold tracking-wider uppercase">
          <span className="bg-primary text-primary-foreground flex size-5 items-center justify-center rounded-full text-[10px]">
            {index + 1}
          </span>
          <span>Câu hỏi {index + 1}/6</span>
        </div>
        <h3 className="text-foreground text-lg leading-snug font-semibold">{question.question}</h3>
        {question.multi && max ? (
          <p className="text-muted-foreground text-xs">
            {remaining! > 0 ? `Còn ${remaining} lựa chọn` : `✅ Đã chọn đủ ${max} lựa chọn`}
          </p>
        ) : null}
      </div>

      {question.categories && Object.keys(question.categories).length > 0 ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Object.entries(question.categories).map(([section, opts]) => (
            <div key={section} className="space-y-2">
              <div className="border-primary/40 text-foreground border-b-2 pb-1 text-center text-sm font-bold">
                {section}
              </div>
              <div className="grid gap-2">
                {Object.keys(opts).map((opt) => {
                  const key = optionKey(question.id, "cat", section, opt);
                  const checked = selectedSet.has(key);
                  const disabled = question.multi && max ? catCount >= max && !checked : false;
                  return (
                    <OptionCard
                      key={key}
                      label={opt}
                      checked={checked}
                      disabled={disabled}
                      onToggle={() => {
                        if (question.multi) {
                          toggle(key);
                        } else if (checked) {
                          setKeyOn(key, false);
                        } else {
                          setExclusive(key, allCatKeys);
                        }
                      }}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {question.specifics && Object.keys(question.specifics).length > 0 ? (
        <SpecificsPopover qId={question.id} specifics={question.specifics} />
      ) : null}
    </section>
  );
}
