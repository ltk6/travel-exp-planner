import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${env.BACKEND_URL}/health`, {
      method: "GET",
      headers: { "X-Internal-Key": env.INTERNAL_API_KEY },
      cache: "no-store",
    });
    if (!res.ok) {
      return Response.json({ status: "error" }, { status: res.status });
    }
    const data = await res.json();
    return Response.json(data);
  } catch (err) {
    return Response.json(
      { status: "error", message: err instanceof Error ? err.message : "Failed to fetch health" },
      { status: 502 },
    );
  }
}
