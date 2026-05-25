"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { usePlannerStore } from "@/store/planner-store";
import type {
  ActivitiesResponse,
  FeedbackEndpoint,
  RecommendResponse,
  RefinedFeedback,
} from "@/lib/types";
import { prefetchLocationImages } from "@/lib/prefetch";


type ActivityFeedbackBody = {
  feedback: string;
  text: string;
  tags: string[];
  img_desc: string;
  text_k: number;
  tags_k: number;
  user_vectors: Record<string, unknown>;
  location: { location_id: string; metadata: Record<string, unknown> };
};

type RecommendFeedbackBody = {
  feedback: string;
  user_input: { text: string; tags: string[]; img_desc: string };
  image: string;
  constraints: Record<string, unknown>;
  context: Record<string, unknown>;
};

/** Display the N17 refinement explanation when present, otherwise a generic success. */
function showRefinedToast(refined: RefinedFeedback | undefined, fallback: string) {
  const explanation = refined?.explanation?.trim();
  if (explanation) {
    toast.success("✨ AI đã hiểu yêu cầu của bạn", {
      description: explanation,
      duration: 6000,
    });
  } else {
    toast.success(fallback);
  }
}

export function useActivityFeedback(locId: string) {
  const setActivityResult = usePlannerStore((s) => s.setActivityResult);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ActivityFeedbackBody) =>
      apiClient.feedback<ActivitiesResponse>("activities", body),
    onSuccess: (data) => {
      const finalLocId = data.location_id ?? locId;
      setActivityResult(finalLocId, data);
      qc.setQueryData(["activities", finalLocId], data);
      showRefinedToast(data.refined, "Đã cập nhật danh sách hoạt động.");
    },
    onError: (err) => {
      toast.error("Không cập nhật được hoạt động.", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });
}

export function useRecommendFeedback() {
  const setResults = usePlannerStore((s) => s.setResults);
  const clearActivities = usePlannerStore((s) => s.clearActivityResults);
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecommendFeedbackBody) =>
      apiClient.feedback<RecommendResponse>("recommend", body),
    onSuccess: (data) => {
      prefetchLocationImages(data);
      setResults(data);
      clearActivities();
      qc.removeQueries({ queryKey: ["activities"] });
      showRefinedToast(data.refined, "Đã tạo lại lộ trình theo phản hồi của bạn.");
    },
    onError: (err) => {
      toast.error("Không tạo lại được lộ trình.", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });
}

export type { ActivityFeedbackBody, RecommendFeedbackBody, FeedbackEndpoint };
