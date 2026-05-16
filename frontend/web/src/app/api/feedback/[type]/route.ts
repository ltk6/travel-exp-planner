import { proxyToBackend } from "@/lib/proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ALLOWED = new Set(["recommend", "activities"]);

export async function POST(req: Request, ctx: { params: Promise<{ type: string }> }) {
  const { type } = await ctx.params;
  if (!ALLOWED.has(type)) {
    return Response.json({ error: `Unknown feedback type: ${type}` }, { status: 400 });
  }
  const body = await req.json();
  return proxyToBackend(`/feedback/${type}`, body);
}
