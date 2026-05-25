import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(_req: Request, { params }: { params: Promise<{ filename: string[] }> }) {
  const { filename } = await params;
  const filePath = filename.join("/");

  const upstream = await fetch(`${env.BACKEND_URL}/api/images/${filePath}`, {
    headers: { "X-Internal-Key": env.INTERNAL_API_KEY },
    cache: "no-store",
  });

  if (!upstream.ok) {
    return new Response(null, { status: upstream.status });
  }

  const contentType = upstream.headers.get("Content-Type") ?? "image/jpeg";
  const buffer = await upstream.arrayBuffer();
  return new Response(buffer, {
    status: 200,
    headers: {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=86400",
    },
  });
}
