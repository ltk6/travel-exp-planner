import { proxyToBackend } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/locations — slim list of all DB locations for Explore mode.
 * Backend dùng POST (PROTECTED_ROUTES filter dùng path-based check), nên ta
 * cũng dùng POST với empty body upstream để qua được proxy hiện tại.
 */
export async function GET() {
  return proxyToBackend("/locations", {});
}
