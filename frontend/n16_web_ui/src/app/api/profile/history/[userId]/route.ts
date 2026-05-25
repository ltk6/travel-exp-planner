import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request, { params }: { params: Promise<{ userId: string }> }) {
  const { userId } = await params;

  const authHeader = req.headers.get("Authorization");
  const headers: Record<string, string> = {
    "X-Internal-Key": env.INTERNAL_API_KEY,
  };
  if (authHeader) {
    headers["Authorization"] = authHeader;
  }

  const upstream = await fetch(`${env.BACKEND_URL}/api/profile/history/${userId}`, {
    headers,
    cache: "no-store",
  });

  const text = await upstream.text();
  return new Response(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
