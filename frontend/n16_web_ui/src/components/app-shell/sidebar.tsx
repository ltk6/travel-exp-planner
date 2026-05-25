"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Compass, List, Moon, Sun, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

type ItemProps = {
  Icon: typeof Compass;
  label: string;
  href?: string;
  onClick?: () => void;
  active?: boolean;
  disabled?: boolean;
};

function RailItem({ Icon, label, href, onClick, active, disabled }: ItemProps) {
  const className = cn(
    "relative flex size-10 items-center justify-center rounded-xl transition-all",
    active && "bg-brand-soft text-primary shadow-sm",
    !active && !disabled && "text-muted-foreground hover:bg-muted hover:text-foreground",
    disabled && "cursor-not-allowed text-muted-foreground/40",
  );

  const inner = (
    <>
      <Icon className="size-4" />
      {disabled ? (
        <Lock className="bg-background/80 text-muted-foreground/60 absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full p-0.5" />
      ) : null}
    </>
  );

  const trigger =
    href && !disabled ? (
      <Link href={href} aria-label={label} className={className}>
        {inner}
      </Link>
    ) : (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className={className}
      >
        {inner}
      </button>
    );

  return (
    <Tooltip>
      <TooltipTrigger render={trigger} />
      <TooltipContent side="right" sideOffset={8}>
        {label}
        {disabled ? <span className="ml-1 opacity-70">· sắp ra mắt</span> : null}
      </TooltipContent>
    </Tooltip>
  );
}

export function AppSidebar() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const pathname = usePathname();

  return (
    <aside className="border-border/60 bg-background/60 fixed top-14 bottom-0 left-0 z-30 hidden w-14 flex-col items-center gap-1 border-r py-3 backdrop-blur md:flex">
      {/* View modes */}
      <RailItem Icon={List} label="Chế độ danh sách" active disabled />
      <RailItem
        Icon={Compass}
        label="Chế độ Khám phá"
        href="/explore"
        active={pathname.startsWith("/explore")}
      />

      <div className="bg-border/60 my-2 h-px w-7" />

      {/* Theme toggle */}
      <RailItem
        Icon={isDark ? Sun : Moon}
        label={isDark ? "Chuyển sang sáng" : "Chuyển sang tối"}
        onClick={() => setTheme(isDark ? "light" : "dark")}
      />
    </aside>
  );
}
