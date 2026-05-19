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
  const storePayload = usePlannerStore((s) => s.payload);
  const storeSelectedKeys = usePlannerStore((s) => s.selectedKeys);
  const storeFreeformText = usePlannerStore((s) => s.freeformText);
  const setActivityResult = usePlannerStore((s) => s.setActivityResult);

  // Cache key chỉ dùng cho lần fetch không filter — khi user chọn chip thì
  // không cache để tránh hiển thị nhầm với danh sách mặc định.
  const results = usePlannerStore((s) => s.results);
  const activityResults = usePlannerStore((s) => s.activityResults);
  const baseCache = activityResults[loc.location_id];
  const useCache = preferredTypes.length === 0;
  const cached = useCache ? baseCache : undefined;

  // Hỗ trợ tải tuần tự (Sequential loading): Chỉ bắt đầu fetch địa điểm này
  // nếu địa điểm xếp hạng ngay trên nó đã hoàn thành tải dữ liệu.
  const locations = results?.locations ?? [];
  const currentIndex = locations.findIndex((l) => l.location_id === loc.location_id);
  const previousLocation = currentIndex > 0 ? locations[currentIndex - 1] : null;
  const previousFetched = previousLocation ? !!activityResults[previousLocation.location_id] : true;

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

  // Tạo signature cho sở thích của người dùng để tránh trùng lặp cache khi đổi gu/sở thích tìm kiếm mới
  const preferenceSignature = `${payload.text}|${[...payload.tags].sort().join(",")}|${payload.img_desc}`;

  return useQuery({
    queryKey: [
      "activities",
      loc.location_id,
      preferenceSignature,
      [...preferredTypes].sort().join(","),
    ],
    queryFn: async () => {
      const data = await apiClient.activities(payload);
      if (preferredTypes.length === 0) setActivityResult(loc.location_id, data);
      return data;
    },
    enabled: enabled && !!loc.geo && !cached && previousFetched,
    initialData: cached,
    staleTime: Infinity,
    retry: 1,
  });
}
