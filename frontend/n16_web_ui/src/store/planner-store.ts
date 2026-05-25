import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { ActivitiesResponse, RecommendPayload, RecommendResponse } from "@/lib/types";
import { apiClient } from "@/lib/api-client";

// One-time cleanup: previous versions persisted to localStorage, which leaked
// stale tags/text/images across browser sessions. Strip the old key on load.
if (typeof window !== "undefined") {
  try {
    window.localStorage.removeItem("travel-planner-state");
  } catch {
    // localStorage might be disabled (private mode etc.) — safe to ignore.
  }
}

/**
 * Sub-mode within the input page (`/`). Not a route — routing lives in Next App Router.
 *   - `questionnaire` · `freeform` · `image` correspond to the 3 input tabs.
 *   - Result viewing is handled by the `/results` route, not by this enum.
 */
export type InputTab = "questionnaire" | "freeform" | "image";

type PlannerState = {
  inputTab: InputTab;
  setInputTab: (m: InputTab) => void;

  selectedKeys: string[];
  toggleKey: (key: string) => void;
  setKeyOn: (key: string, on: boolean) => void;
  setKeysExclusive: (selectedKey: string, allKeysInGroup: string[]) => void;
  clearKeys: () => void;

  freeformText: string;
  setFreeformText: (t: string) => void;

  imagesB64: string[];
  setImages: (imgs: string[]) => void;
  removeImageAt: (idx: number) => void;

  payload: RecommendPayload | null;
  setPayload: (p: RecommendPayload | null) => void;

  results: RecommendResponse | null;
  setResults: (r: RecommendResponse | null) => void;

  activityResults: Record<string, ActivitiesResponse>;
  activityResultsLlm: Record<string, ActivitiesResponse>;
  setActivityResult: (locId: string, data: ActivitiesResponse) => void;
  setActivityResultLlm: (locId: string, data: ActivitiesResponse) => void;
  clearActivityResults: () => void;

  /** ID of the current history session (set after /recommend save, used to update with activities). */
  currentSessionId: number | null;
  setCurrentSessionId: (id: number | null) => void;

  /**
   * Map focus signal — bumped each time the user asks the map to fly to a
   * specific location (e.g. by clicking a result card). `focusedAt` is a tick
   * so re-focusing the same id still triggers the effect.
   */
  focusedLocationId: string | null;
  focusedAt: number;
  setFocusedLocation: (id: string | null) => void;

  preferLlmActivities: Record<string, boolean>;
  setPreferLlmActivities: (locId: string, p: boolean) => void;
  clearActivityResultForLocation: (locId: string) => void;

  saveHistorySession: (userId: number) => Promise<void>;

  reset: () => void;
};

export const usePlannerStore = create<PlannerState>()(
  persist(
    (set) => ({
      inputTab: "questionnaire",
      setInputTab: (inputTab) => set({ inputTab }),

      selectedKeys: [],
      toggleKey: (key) =>
        set((s) => ({
          selectedKeys: s.selectedKeys.includes(key)
            ? s.selectedKeys.filter((k) => k !== key)
            : [...s.selectedKeys, key],
        })),
      setKeyOn: (key, on) =>
        set((s) => ({
          selectedKeys: on
            ? s.selectedKeys.includes(key)
              ? s.selectedKeys
              : [...s.selectedKeys, key]
            : s.selectedKeys.filter((k) => k !== key),
        })),
      setKeysExclusive: (selectedKey, allKeysInGroup) =>
        set((s) => {
          const groupSet = new Set(allKeysInGroup);
          const withoutGroup = s.selectedKeys.filter((k) => !groupSet.has(k));
          return { selectedKeys: [...withoutGroup, selectedKey] };
        }),
      clearKeys: () => set({ selectedKeys: [] }),

      freeformText: "",
      setFreeformText: (freeformText) => set({ freeformText }),

      imagesB64: [],
      setImages: (imagesB64) => set({ imagesB64 }),
      removeImageAt: (idx) => set((s) => ({ imagesB64: s.imagesB64.filter((_, i) => i !== idx) })),

      payload: null,
      setPayload: (payload) => set({ payload }),

      results: null,
      setResults: (results) => set({ results }),

      activityResults: {},
      activityResultsLlm: {},
      setActivityResult: (locId, data) =>
        set((s) => ({ activityResults: { ...s.activityResults, [locId]: data } })),
      setActivityResultLlm: (locId, data) =>
        set((s) => ({ activityResultsLlm: { ...s.activityResultsLlm, [locId]: data } })),
      clearActivityResults: () => set({ activityResults: {}, activityResultsLlm: {} }),

      currentSessionId: null,
      setCurrentSessionId: (currentSessionId) => set({ currentSessionId }),

      focusedLocationId: null,
      focusedAt: 0,
      setFocusedLocation: (id) => set({ focusedLocationId: id, focusedAt: Date.now() }),

      preferLlmActivities: {},
      setPreferLlmActivities: (locId, preferLlm) =>
        set((s) => ({
          preferLlmActivities: { ...s.preferLlmActivities, [locId]: preferLlm },
        })),
      clearActivityResultForLocation: (locId) =>
        set((s) => {
          const next = { ...s.activityResults };
          const nextLlm = { ...s.activityResultsLlm };
          delete next[locId];
          delete nextLlm[locId];
          return { activityResults: next, activityResultsLlm: nextLlm };
        }),

      saveHistorySession: async (userId) => {
        const { payload, results, preferLlmActivities, activityResults, activityResultsLlm, currentSessionId } = usePlannerStore.getState();
        if (!payload || !results) return;

        try {
          const res = await apiClient.profile.saveHistory({
            user_id: userId,
            input_data: payload,
            output_data: {
              ...results,
              preferLlmActivities,
              activityResults,
              activityResultsLlm,
            },
            history_id: currentSessionId || undefined,
          });
          if (res.status === "success" && res.history_id) {
            set({ currentSessionId: res.history_id });
          }
        } catch (e) {
          console.error("Failed to update history session:", e);
        }
      },

      reset: () =>
        set({
          inputTab: "questionnaire",
          selectedKeys: [],
          freeformText: "",
          imagesB64: [],
          payload: null,
          results: null,
          activityResults: {},
          activityResultsLlm: {},
          currentSessionId: null,
          focusedLocationId: null,
          focusedAt: 0,
          preferLlmActivities: {},
        }),
    }),
    {
      name: "travel-planner-state",
      version: 5,
      // sessionStorage: state survives HMR & navigation, but a fresh browser tab
      // (e.g. opened by run.bat) starts empty. Avoids stale data from a previous session leaking.
      storage: createJSONStorage(() =>
        typeof window !== "undefined" ? window.sessionStorage : (undefined as unknown as Storage),
      ),
      partialize: (s) => ({
        inputTab: s.inputTab,
        selectedKeys: s.selectedKeys,
        freeformText: s.freeformText,
        imagesB64: s.imagesB64,
      }),
      migrate: (_persisted, version) => {
        if (version < 5) {
          return {
            inputTab: "questionnaire" as const,
            selectedKeys: [],
            freeformText: "",
            imagesB64: [],
          };
        }
        return _persisted;
      },
    },
  ),
);
