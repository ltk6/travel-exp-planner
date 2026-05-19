"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { usePlannerStore } from "@/store/planner-store";
import type { ActivitiesPayload, LocationResult } from "@/lib/types";

export function useActivitiesQuery(
  loc: LocationResult,
  options?: { enabled?: boolean; preferredTypes?: string[] },
) {
  const enabled = options?.enabled ?? true;
  const preferredTypes = options?.preferredTypes ?? [];

  // `trace` chỉ có khi backend chạy với API_DEBUG=True; v2 không cần trace,
  // chỉ cần location.geo + top_k. Giữ các field user_* để nếu sau này quay lại
  // v1 (N5 LLM gen, cần user_vectors) thì có sẵn.
  const userTrace = usePlannerStore((s) => s.results?.trace?.user);
  const setActivityResult = usePlannerStore((s) => s.setActivityResult);

  // Cache key chỉ dùng cho lần fetch không filter — khi user chọn chip thì
  // không cache để tránh hiển thị nhầm với danh sách mặc định.
  const baseCache = usePlannerStore((s) => s.activityResults[loc.location_id]);
  const useCache = preferredTypes.length === 0;
  const cached = useCache ? baseCache : undefined;

  const payload: ActivitiesPayload = {
    text: userTrace?.input?.text ?? "",
    tags: userTrace?.input?.tags ?? [],
    img_desc: userTrace?.n2_image?.img_desc ?? "",
    text_k: userTrace?.n1_embedding?.text_k ?? 0,
    tags_k: userTrace?.n1_embedding?.tags_k ?? 0,
    user_vectors: userTrace?.user_vectors ?? {},
    location: {
      location_id: loc.location_id,
      metadata: loc.metadata ?? {},
      geo: loc.geo,
    },
    top_k_activities: 5,
    ...(preferredTypes.length > 0 ? { preferred_types: preferredTypes } : {}),
  };

  return useQuery({
    queryKey: ["activities", loc.location_id, [...preferredTypes].sort().join(",")],
    queryFn: async () => {
      const data = await apiClient.activities(payload);
      if (preferredTypes.length === 0) setActivityResult(loc.location_id, data);
      return data;
    },
    enabled: enabled && !!loc.geo && !cached,
    initialData: cached,
    staleTime: Infinity,
    retry: 1,
  });
}
