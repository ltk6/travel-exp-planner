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

  // trace is only available when backend runs with API_DEBUG=True
  const userTrace = usePlannerStore((s) => s.results?.trace?.user);
  const storePayload = usePlannerStore((s) => s.payload);
  const storeSelectedKeys = usePlannerStore((s) => s.selectedKeys);
  const storeFreeformText = usePlannerStore((s) => s.freeformText);
  const setActivityResult = usePlannerStore((s) => s.setActivityResult);
  const setActivityResultLlm = usePlannerStore((s) => s.setActivityResultLlm);
  const preferLlmActivities = usePlannerStore((s) => s.preferLlmActivities[loc.location_id] ?? false);

  // Cache key only used for unfiltered fetches
  const results = usePlannerStore((s) => s.results);
  const activityResults = usePlannerStore((s) => s.activityResults);
  const activityResultsLlm = usePlannerStore((s) => s.activityResultsLlm);
  
  const baseCache = preferLlmActivities ? activityResultsLlm[loc.location_id] : activityResults[loc.location_id];
  const useCache = preferredTypes.length === 0;
  const cached = useCache ? baseCache : undefined;

  // Sequential loading support: start fetching only if the card above has finished loading
  const locations = results?.locations ?? [];
  const currentIndex = locations.findIndex((l) => l.location_id === loc.location_id);
  const previousLocation = currentIndex > 0 ? locations[currentIndex - 1] : null;
  const isCurrentFetched = !!activityResults[loc.location_id] || !!activityResultsLlm[loc.location_id];
  const previousFetched = previousLocation ? !!activityResults[previousLocation.location_id] || !!activityResultsLlm[previousLocation.location_id] : true;

  const payload: ActivitiesPayload = {
    text: userTrace?.input?.text || storePayload?.text || storeFreeformText || "",
    tags: userTrace?.input?.tags || storePayload?.tags || storeSelectedKeys || [],
    img_desc: userTrace?.n2_image?.img_desc || storePayload?.img_desc || "",
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

  // Generate preference signature to prevent cache pollution
  const preferenceSignature = `${payload.text}|${[...payload.tags].sort().join(",")}|${payload.img_desc}`;

  return useQuery({
    queryKey: [
      "activities",
      loc.location_id,
      preferenceSignature,
      [...preferredTypes].sort().join(","),
      preferLlmActivities,
    ],
    queryFn: async () => {
      const data = preferLlmActivities
        ? await apiClient.activities(payload)
        : await apiClient.activitiesV2(payload);
      
      if (preferredTypes.length === 0) {
        if (preferLlmActivities) {
          setActivityResultLlm(loc.location_id, data);
        } else {
          setActivityResult(loc.location_id, data);
        }

        // Auto-save/update history session if user is logged in
        if (typeof window !== "undefined") {
          try {
            const user = sessionStorage.getItem("auth_user");
            if (user) {
              const parsed = JSON.parse(user);
              if (parsed?.userId) {
                // Async database update
                usePlannerStore.getState().saveHistorySession(parsed.userId);
              }
            }
          } catch (e) {
            // Ignore storage errors
          }
        }
      }
      return data;
    },
    enabled: enabled && !!loc.geo && !cached && (isCurrentFetched || previousFetched),
    initialData: cached,
    staleTime: Infinity,
    retry: 1,
  });
}
