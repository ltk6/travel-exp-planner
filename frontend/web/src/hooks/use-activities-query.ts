"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { usePlannerStore } from "@/store/planner-store";
import type { ActivitiesPayload, LocationResult } from "@/lib/types";

export function useActivitiesQuery(loc: LocationResult, enabled = true) {
  const userTrace = usePlannerStore((s) => s.results?.trace?.user);
  const setActivityResult = usePlannerStore((s) => s.setActivityResult);
  const cached = usePlannerStore((s) => s.activityResults[loc.location_id]);

  const payload: ActivitiesPayload | null = userTrace
    ? {
        text: userTrace.input?.text ?? "",
        tags: userTrace.input?.tags ?? [],
        img_desc: userTrace.n2_image?.img_desc ?? "",
        text_k: userTrace.n1_embedding?.text_k ?? 0,
        tags_k: userTrace.n1_embedding?.tags_k ?? 0,
        user_vectors: userTrace.user_vectors ?? {},
        location: { location_id: loc.location_id, metadata: loc.metadata ?? {} },
        top_k_activities: 5,
      }
    : null;

  return useQuery({
    queryKey: ["activities", loc.location_id],
    queryFn: async () => {
      if (!payload) throw new Error("Missing user trace for activities request");
      const data = await apiClient.activities(payload);
      setActivityResult(loc.location_id, data);
      return data;
    },
    enabled: enabled && !!payload && !cached,
    initialData: cached,
    staleTime: Infinity,
    retry: 1,
  });
}
