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

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = sessionStorage.getItem("auth_user");
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed.token || null;
    }
  } catch {
    // ignore
  }
  return null;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json() as Promise<T>;
}

async function getJson<T>(url: string): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url, { method: "GET", headers });
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

  submitAppFeedback: (body: { name?: string; email?: string; content: string }) =>
    postJson<{ status: string; message: string }>("/api/feedback", body),

  profile: {
    getHistory: (userId: number) => getJson<HistoryResponse>(`/api/profile/history/${userId}`),
    saveHistory: (body: {
      user_id: number;
      input_data: RecommendPayload;
      output_data: RecommendResponse | Record<string, unknown>;
      history_id?: number;
    }) =>
      postJson<{ status: string; message: string; history_id?: number }>(
        "/api/profile/history",
        body,
      ),
  },
};
