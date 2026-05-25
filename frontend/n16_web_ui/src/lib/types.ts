export type RecommendPayload = {
  text: string;
  /** Single base64 string (NOT data URI). Backend accepts one image per request. */
  image: string;
  tags: string[];
  /** Reserved object — backend reads `constraints` (plural, dict) but does not use it yet. */
  constraints: Record<string, unknown>;
  context?: Record<string, unknown>;
  top_k_locations?: number;
  top_k_activities?: number;
  img_desc?: string;
};

export type LocationGeo = {
  lat?: number;
  lng?: number;
};

export type LocationMetadata = {
  name?: string;
  description?: string;
  [k: string]: unknown;
};

export type LocationResult = {
  location_id: string;
  score: number;
  reason?: string;
  metadata?: LocationMetadata;
  /** Data URIs returned by backend (`data:image/jpeg;base64,...`). */
  images?: string[];
  geo?: LocationGeo;
};

/**
 * Slim shape from `GET /api/locations` (Explore mode).
 * 1 ảnh đại diện thay vì list, không có score/reason (không phải kết quả ranked).
 */
export type ExploreLocation = {
  location_id: string;
  metadata?: LocationMetadata;
  geo?: LocationGeo;
  /** Data URI for the representative image, or null if the location has no image. */
  image: string | null;
  images_count: number;
};

export type ExploreLocationsResponse = {
  status?: string;
  total?: number;
  data: ExploreLocation[];
};

export type ActivityType =
  | "food"
  | "adventure"
  | "culture"
  | "nightlife"
  | "shopping"
  | "relaxation"
  | "nature"
  | "photography"
  | "experience";

export type RefinedFeedback = {
  text?: string;
  tags?: string[];
  img_desc?: string;
  explanation?: string;
};

export type UserVectors = Record<string, unknown>;

export type RecommendResponse = {
  locations: LocationResult[];
  trace?: {
    user?: {
      input?: {
        text?: string;
        tags?: string[];
        constraints?: Record<string, unknown>;
        context?: Record<string, unknown>;
      };
      n1_embedding?: { text_k?: number; tags_k?: number };
      n2_image?: { img_desc?: string };
      user_vectors?: UserVectors;
    };
  };
  /** Present on feedback/recommend response — shows how N17 refined the original input. */
  refined?: RefinedFeedback;
};

export type ActivityMetadata = {
  name?: string;
  description?: string;
  activity_type?: ActivityType | string;
  tags?: string[];
  intensity?: number;
  physical_level?: number | null;
  social_level?: number | null;
  // v2 (N9-N14 processor) extras — undefined on v1 (LLM) responses.
  source?: string;
  coordinates?: { lat: number; lng: number } | null;
  distance_m?: number | null;
  rating?: number | null;
  image_url?: string | null;
  website?: string | null;
  opening_hours?: string | null;
  indoor_outdoor?: "indoor" | "outdoor" | string | null;
  [k: string]: unknown;
};

export type ActivityResult = {
  activity_id?: string;
  location_id?: string;
  score: number;
  reason?: string;
  metadata?: ActivityMetadata;
};

export type ActivitiesResponse = {
  status?: string;
  location_id?: string;
  activities: ActivityResult[];
  meta?: {
    provider_used?: string;
    model_used?: string;
    fallback_used?: boolean;
    fallback_n5_count?: number;
  };
  refined?: RefinedFeedback;
};

export type ActivitiesPayload = {
  text: string;
  img_desc: string;
  tags: string[];
  text_k: number;
  tags_k: number;
  user_vectors: UserVectors;
  location: { location_id: string; metadata: LocationMetadata; geo?: LocationGeo };
  /** UI chip selection — boost these activity_types in the N9-N14 processor. */
  preferred_types?: string[];
  provider?: string | null;
  top_k_activities?: number;
};

export type FeedbackEndpoint = "recommend" | "activities";

export type FeedbackPayload = {
  feedback: string;
  [k: string]: unknown;
};

export type AuthPayload = { username: string; password: string };

export type AuthResponse = {
  status: "success" | "error";
  message: string;
  user_id?: number;
  token?: string;
};


export type HistoryItem = {
  history_id: number;
  input_data: RecommendPayload;
  output_data: RecommendResponse;
  created_at: string;
};

export type HistoryResponse = {
  status: "success" | "error";
  data: HistoryItem[];
  message?: string;
};
