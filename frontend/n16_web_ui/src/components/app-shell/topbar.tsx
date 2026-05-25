"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, MessageSquareDashed, Info, Compass, User, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { AuthDialog } from "@/components/auth/auth-dialog";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

type NavItem = {
  href: string;
  label: string;
  Icon: typeof Home;
  badge?: string;
};

const NAV: NavItem[] = [
  { href: "/", label: "Trang chủ", Icon: Home },
  { href: "/feedback", label: "Phản hồi", Icon: MessageSquareDashed },
  { href: "/about", label: "Về dự án", Icon: Info },
];

export function AppTopbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);

  function handleLogout() {
    logout();
    toast.success("Đã đăng xuất");
  }

  return (
    <>
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
              href === "/"
                ? pathname === "/" || pathname === "/results"
                : pathname.startsWith(href);
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

        <div className="flex items-center gap-2">
          {user ? (
            <>
              <Link
                href="/profile"
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                  pathname.startsWith("/profile")
                    ? "bg-brand-soft text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <User className="size-3.5" />
                <span className="hidden sm:inline">{user.username}</span>
              </Link>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-muted-foreground h-8 px-2"
                title="Đăng xuất"
              >
                <LogOut className="size-3.5" />
                <span className="hidden sm:inline">Đăng xuất</span>
              </Button>
            </>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setAuthOpen(true)}
              className="h-8 gap-1.5 text-xs"
            >
              <User className="size-3.5" />
              Đăng nhập
            </Button>
          )}
        </div>
      </header>

      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} />
    </>
  );
}
