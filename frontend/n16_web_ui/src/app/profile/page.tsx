"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { LogOut, User, Clock, MapPin, Tag, Play } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";
import type {
  HistoryItem,
  RecommendPayload,
  RecommendResponse,
  ActivitiesResponse,
} from "@/lib/types";
import { usePlannerStore } from "@/store/planner-store";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!user) {
      router.replace("/");
    } else if (!user.token) {
      console.warn("Stale session without token. Logging out...");
      logout();
      toast.error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
      router.replace("/");
    }
  }, [user, router, logout]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["profile-history", user?.userId],
    queryFn: () => apiClient.profile.getHistory(user!.userId),
    enabled: !!user && !!user.token,
  });

  useEffect(() => {
    if (error) {
      console.error("Failed to fetch history:", error);
      if (error instanceof Error && error.message.includes("401")) {
        toast.error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.");
        logout();
        router.push("/");
      }
    }
  }, [error, logout, router]);

  function handleLogout() {
    logout();
    usePlannerStore.getState().reset();
    toast.success("Đã đăng xuất");
    router.push("/");
  }

  if (!user) return null;

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-brand-soft text-primary flex size-10 items-center justify-center rounded-full">
            <User className="size-5" />
          </div>
          <div>
            <p className="font-semibold">{user.username}</p>
            <p className="text-muted-foreground text-xs">Tài khoản du lịch</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground">
          <LogOut className="size-4" />
          Đăng xuất
        </Button>
      </div>

      {/* History */}
      <section>
        <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold">
          <Clock className="size-4" />
          Lịch sử gợi ý
        </h2>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-xl" />
            ))}
          </div>
        ) : !data?.data?.length ? (
          <div className="text-muted-foreground rounded-xl border border-dashed py-12 text-center text-sm">
            Chưa có lịch sử gợi ý nào
          </div>
        ) : (
          <div className="space-y-3">
            {data.data.map((item) => (
              <HistoryCard key={item.history_id} item={item} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function HistoryCard({ item }: { item: HistoryItem }) {
  const input = item.input_data;
  const locations = item.output_data?.locations ?? [];
  const tags = input?.tags ?? [];
  const router = useRouter();

  const handleLoad = () => {
    const store = usePlannerStore.getState();
    store.reset();

    // Restore payload
    store.setPayload(item.input_data as RecommendPayload);

    const outputData = item.output_data as Record<string, unknown>;
    
    // Extract both activities caches and switcher preferences
    const preferLlm = (outputData.preferLlmActivities ?? {}) as Record<string, boolean>;
    const actResults = (outputData.activityResults ?? {}) as Record<string, ActivitiesResponse>;
    const actResultsLlm = (outputData.activityResultsLlm ?? {}) as Record<string, ActivitiesResponse>;
    
    // Backward compatibility for legacy recommendations
    const legacyActivities = outputData.activities as Record<string, ActivitiesResponse> | undefined;

    // Remove customized metadata keys before setting main location results
    const { preferLlmActivities, activityResults, activityResultsLlm, activities, ...results } = outputData;
    store.setResults(results as RecommendResponse);

    // Restore location switcher preferences
    Object.entries(preferLlm).forEach(([locId, val]) => {
      store.setPreferLlmActivities(locId, val);
    });

    // Clear and restore both activities caches
    store.clearActivityResults();
    
    Object.entries(actResults).forEach(([locId, data]) => {
      store.setActivityResult(locId, data);
    });

    Object.entries(actResultsLlm).forEach(([locId, data]) => {
      store.setActivityResultLlm(locId, data);
    });

    // Restore legacy data structure if present
    if (legacyActivities && typeof legacyActivities === "object") {
      Object.entries(legacyActivities).forEach(([locId, data]) => {
        store.setActivityResult(locId, data);
      });
    }

    // Restore session ID to continue the session
    store.setCurrentSessionId(item.history_id);

    toast.success("Recommendation session loaded successfully");
    router.push("/results");
  };

  return (
    <div className="bg-card group hover:border-primary/50 relative rounded-xl border p-4 transition-colors">
      <div className="mb-2 flex items-start justify-between gap-2 pr-20">
        <p className="text-foreground line-clamp-2 text-sm font-medium">
          {input?.text?.trim() || "Không có mô tả"}
        </p>
        <span className="text-muted-foreground absolute top-4 right-4 shrink-0 text-xs tabular-nums">
          {item.created_at.slice(0, 10)}
        </span>
      </div>

      {tags.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          <Tag className="text-muted-foreground mt-0.5 size-3 shrink-0" />
          {tags.slice(0, 5).map((t) => (
            <span
              key={t}
              className="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-[10px]"
            >
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-end justify-between">
        {locations.length > 0 && (
          <div className="flex flex-1 flex-wrap items-center gap-1.5 pr-4">
            <MapPin className="text-primary size-3 shrink-0" />
            {locations.slice(0, 4).map((loc) => (
              <span key={loc.location_id} className="text-muted-foreground text-xs">
                {loc.metadata?.name ?? loc.location_id}
              </span>
            ))}
            {locations.length > 4 && (
              <span className="text-muted-foreground text-xs">
                +{locations.length - 4} địa điểm
              </span>
            )}
          </div>
        )}

        <Button
          variant="secondary"
          size="sm"
          onClick={handleLoad}
          className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
        >
          <Play className="mr-1.5 size-3" />
          Tải phiên
        </Button>
      </div>
    </div>
  );
}
