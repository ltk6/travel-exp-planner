"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

/**
 * Fetch toàn bộ địa điểm DB cho chế độ Khám phá.
 * Cached lâu (staleTime: 5 phút) — payload có thể vài MB do kèm ảnh đại diện.
 */
export function useLocationsQuery() {
  return useQuery({
    queryKey: ["explore-locations"],
    queryFn: () => apiClient.locations(),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
