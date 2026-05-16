"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, MessageSquareDashed, Info, Compass } from "lucide-react";
import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  Icon: typeof Home;
  /** Marks routes whose feature is still under construction. */
  badge?: string;
};

const NAV: NavItem[] = [
  { href: "/", label: "Trang chủ", Icon: Home },
  { href: "/feedback", label: "Feedback", Icon: MessageSquareDashed, badge: "WIP" },
  { href: "/about", label: "Về dự án", Icon: Info },
];

export function AppTopbar() {
  const pathname = usePathname();

  return (
    <header className="border-border/60 bg-background/85 supports-[backdrop-filter]:bg-background/70 sticky top-0 z-40 flex h-14 items-center justify-between gap-4 border-b px-4 backdrop-blur sm:px-6">
      <Link
        href="/"
        className="text-foreground flex items-center gap-2 font-extrabold tracking-tight"
      >
        <span className="from-primary to-brand-dim flex size-7 items-center justify-center rounded-lg bg-gradient-to-br text-white">
          <Compass className="size-4" />
        </span>
        <span className="hidden text-sm sm:inline">Travel Planner</span>
      </Link>

      <nav className="flex items-center gap-1">
        {NAV.map(({ href, label, Icon, badge }) => {
          const active =
            href === "/" ? pathname === "/" || pathname === "/results" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "relative inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                active
                  ? "bg-brand-soft text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="size-3.5" />
              <span className="hidden sm:inline">{label}</span>
              {badge ? (
                <span className="bg-muted text-muted-foreground rounded-full px-1.5 py-0.5 font-mono text-[9px] tracking-wider uppercase">
                  {badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
