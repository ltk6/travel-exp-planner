"use client";

import { cn } from "@/lib/utils";
import { emojiFor } from "@/lib/emoji-map";
import { Check } from "lucide-react";

type Props = {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onToggle: () => void;
};

export function OptionCard({ label, checked, disabled, onToggle }: Props) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled && !checked}
      aria-pressed={checked}
      className={cn(
        "group relative flex w-full items-center gap-2.5 rounded-xl border-2 px-3 py-3 text-left transition-all",
        "focus-visible:ring-primary/60 shadow-sm hover:-translate-y-0.5 hover:shadow-md focus-visible:ring-2 focus-visible:outline-none",
        checked
          ? "border-primary bg-primary/10 shadow-primary/20"
          : "border-border bg-card hover:border-foreground/30",
        disabled && !checked && "cursor-not-allowed opacity-40 hover:translate-y-0 hover:shadow-sm",
      )}
    >
      <span className="shrink-0 text-lg leading-none" aria-hidden>
        {emojiFor(label)}
      </span>
      <span className="flex-1 text-sm leading-tight font-medium">{label}</span>
      <span
        className={cn(
          "flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-all",
          checked
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border bg-transparent",
        )}
      >
        {checked && <Check className="size-3" strokeWidth={3} />}
      </span>
    </button>
  );
}
