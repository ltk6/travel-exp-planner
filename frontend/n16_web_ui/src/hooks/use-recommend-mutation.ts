"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { usePlannerStore } from "@/store/planner-store";
import { useAuth } from "@/lib/auth-context";
import type { RecommendPayload } from "@/lib/types";
import { prefetchLocationImages } from "@/lib/prefetch";

export function useRecommendMutation() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const setResults = usePlannerStore((s) => s.setResults);
  const clearActivities = usePlannerStore((s) => s.clearActivityResults);
  const setPayload = usePlannerStore((s) => s.setPayload);
  const setCurrentSessionId = usePlannerStore((s) => s.setCurrentSessionId);
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: RecommendPayload) => apiClient.recommend(payload),
    onMutate: (payload) => {
      setPayload(payload);
    },
    onSuccess: async (data, payload) => {
      // Prefetch images for the top locations right after recommend succeeds to warm cache
      prefetchLocationImages(data);

      setResults(data);
      clearActivities();
      qc.removeQueries({ queryKey: ["activities"] });
      setCurrentSessionId(null);

      // Auto-save search history if logged in
      if (user?.userId) {
        if (!user.token) {
          console.warn("Stale session without token. Logging out...");
          logout();
        } else {
          try {
            const res = await apiClient.profile.saveHistory({
              user_id: user.userId,
              input_data: payload,
              output_data: data,
            });
            if (res.status === "success" && res.history_id) {
              setCurrentSessionId(res.history_id);
            }
          } catch (e) {
            console.error("Auto-save history error:", e);
            if (e instanceof Error && e.message.includes("401")) {
              toast.error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
              logout();
            }
          }
        }
      }

      router.push("/results");
      toast.success(`Đã tìm thấy ${data.locations?.length ?? 0} địa điểm phù hợp.`);
    },
    onError: (err) => {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error("Không thể tải gợi ý.", { description: msg });
    },
  });
}
