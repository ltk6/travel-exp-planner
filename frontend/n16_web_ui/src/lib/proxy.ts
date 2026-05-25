import { env } from "./env";

export async function proxyToBackend(path: string, body: unknown, customHeaders?: Record<string, string>) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), env.BACKEND_TIMEOUT_MS);

  try {
    const upstream = await fetch(`${env.BACKEND_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Key": env.INTERNAL_API_KEY,
        ...customHeaders,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
      cache: "no-store",
    });

    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upstream request failed";
    const status = message.includes("aborted") ? 504 : 502;
    return Response.json({ error: message }, { status });
  } finally {
    clearTimeout(timer);
  }
}
