import type { NextConfig } from "next";
import withSerwistInit from "@serwist/next";

const withSerwist = withSerwistInit({
  swSrc: "src/app/sw.ts",
  swDest: "public/sw.js",
  cacheOnNavigation: true,
  reloadOnOnline: true,
  disable: process.env.NODE_ENV === "development",
});

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:5000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [{ protocol: "https", hostname: "**" }],
  },
  async rewrites() {
    return [
      // Browser hits /api/images/* → Next.js proxies to Flask backend.
      // Lets <img src="/api/images/loc_001_0.jpg"> work without baking
      // BACKEND_URL into client bundle.
      { source: "/api/images/:path*", destination: `${BACKEND_URL}/api/images/:path*` },
    ];
  },
};

export default withSerwist(nextConfig);
