import type {
  ActivitiesPayload,
  ActivitiesResponse,
  AuthPayload,
  AuthResponse,
  ExploreLocationsResponse,
  FeedbackEndpoint,
  FeedbackPayload,
  HistoryResponse,
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

  /** v2: real map-source activities (N9-N14 processor) instead of N5 LLM. */
  activitiesV2: (payload: ActivitiesPayload) =>
    postJson<ActivitiesResponse>("/api/activities/v2", payload),

  feedback: <T>(endpoint: FeedbackEndpoint, body: FeedbackPayload) =>
    postJson<T>(`/api/feedback/${endpoint}`, body),

  locations: () => getJson<ExploreLocationsResponse>("/api/locations"),

  auth: {
    register: (payload: AuthPayload) => postJson<AuthResponse>("/api/auth/register", payload),
    login: (payload: AuthPayload) => postJson<AuthResponse>("/api/auth/login", payload),
  },

  profile: {
    getHistory: (userId: number) => getJson<HistoryResponse>(`/api/profile/history/${userId}`),
  },
};
