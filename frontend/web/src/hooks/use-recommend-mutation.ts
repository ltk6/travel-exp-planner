"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { usePlannerStore } from "@/store/planner-store";
import type { RecommendPayload } from "@/lib/types";

export function useRecommendMutation() {
  const router = useRouter();
  const setResults = usePlannerStore((s) => s.setResults);
  const clearActivities = usePlannerStore((s) => s.clearActivityResults);
  const setPayload = usePlannerStore((s) => s.setPayload);

  return useMutation({
    mutationFn: (payload: RecommendPayload) => apiClient.recommend(payload),
    onMutate: (payload) => {
      setPayload(payload);
    },
    onSuccess: (data) => {
      setResults(data);
      clearActivities();
      router.push("/results");
      toast.success(`Đã tìm thấy ${data.locations?.length ?? 0} địa điểm phù hợp.`);
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error("Không thể tải gợi ý.", { description: msg });
    },
  });
}
