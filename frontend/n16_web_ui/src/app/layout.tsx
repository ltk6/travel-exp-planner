import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Be_Vietnam_Pro, Geist_Mono } from "next/font/google";
import { Providers } from "@/components/providers";
import { AppTopbar } from "@/components/app-shell/topbar";
import { AppSidebar } from "@/components/app-shell/sidebar";
import "./globals.css";

const beVietnamPro = Be_Vietnam_Pro({
  variable: "--font-be-vietnam-pro",
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Travel Experience Planner",
  description: "Gợi ý trải nghiệm du lịch Việt Nam bằng AI",
  manifest: "/manifest.webmanifest",
  applicationName: "Travel Planner",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Travel Planner",
  },
};

export const viewport: Viewport = {
  themeColor: "#ff6b6b",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${beVietnamPro.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="bg-background text-foreground flex min-h-full flex-col font-sans">
        <Providers>
          {/* Ambient gradient — coral mist at top, teal mist at bottom */}
          <div className="pointer-events-none fixed inset-0 -z-10">
            <div className="absolute inset-x-0 top-0 h-[60vh] bg-[radial-gradient(ellipse_80%_50%_at_50%_0%,oklch(0.95_0.06_22),transparent_70%)]" />
            <div className="absolute inset-x-0 bottom-0 h-[40vh] bg-[radial-gradient(ellipse_80%_50%_at_50%_100%,oklch(0.95_0.05_195),transparent_70%)]" />
          </div>

          <AppTopbar />
          <AppSidebar />

          <div className="flex flex-1 flex-col md:pl-14">
            {children}
            <SiteFooter />
          </div>
        </Providers>
      </body>
    </html>
  );
}

function SiteFooter() {
  return (
    <footer className="border-border/60 mx-auto mt-20 w-full max-w-5xl space-y-4 border-t px-4 pt-8 pb-6 text-center">
      <p className="text-muted-foreground text-xs">
        <Link href="/" className="hover:text-primary">
          Trang chủ
        </Link>
        {" · "}
        <Link href="/results" className="hover:text-primary">
          Kết quả
        </Link>
        {" · "}
        <Link href="/feedback" className="hover:text-primary">
          Feedback
        </Link>
        {" · "}
        <Link href="/about" className="hover:text-primary">
          Về dự án
        </Link>
        {" · "}HCMUS · Built with Next.js · shadcn/ui
      </p>
    </footer>
  );
}
