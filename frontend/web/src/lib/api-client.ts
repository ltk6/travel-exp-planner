import type {
  ActivitiesPayload,
  ActivitiesResponse,
  ExploreLocationsResponse,
  FeedbackEndpoint,
  FeedbackPayload,
  RecommendPayload,
  RecommendResponse,
} from "./types";

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<T>;
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const apiClient = {
  recommend: (payload: RecommendPayload) => postJson<RecommendResponse>("/api/recommend", payload),

  activities: (payload: ActivitiesPayload) =>
    postJson<ActivitiesResponse>("/api/activities", payload),

  feedback: <T>(endpoint: FeedbackEndpoint, body: FeedbackPayload) =>
    postJson<T>(`/api/feedback/${endpoint}`, body),

  locations: () => getJson<ExploreLocationsResponse>("/api/locations"),
};
