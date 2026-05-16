"use client";

import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Compass, AlertCircle, Loader2, Search, X, ChevronRight } from "lucide-react";
import { useLocationsQuery } from "@/hooks/use-locations-query";
import { ExploreMap } from "@/components/explore/explore-map";
import { LocationDetail } from "@/components/explore/location-detail";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { ExploreLocation } from "@/lib/types";

const MAX_SUGGESTIONS = 8;

type FindState = { results: ExploreLocation[]; index: number; term: string };

/**
 * Match một location chống lại query string (lowercased).
 * Match trên `metadata.name` và `metadata.tags`.
 */
function matchesQuery(loc: ExploreLocation, q: string): boolean {
  const name = ((loc.metadata?.name as string | undefined) ?? loc.location_id).toLowerCase();
  if (name.includes(q)) return true;
  const tags = Array.isArray(loc.metadata?.tags) ? (loc.metadata!.tags as string[]) : [];
  return tags.some((t) => t.toLowerCase().includes(q));
}

/**
 * /explore — chế độ Khám phá.
 *
 * Search flow:
 *   - Gõ → dropdown suggestions (tối đa 8). Click → chọn location đó.
 *   - Enter → "Find mode": cycle qua tất cả match bằng nút Next, vẫn thấy đầy đủ pin.
 *   - X / Close → thoát Find mode về search bình thường.
 */
export default function ExplorePage() {
  const { data, isLoading, isError, error } = useLocationsQuery();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [findMode, setFindMode] = useState<FindState | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const locations = useMemo(() => data?.data ?? [], [data]);

  const suggestions = useMemo(() => {
    if (findMode) return [];
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return locations.filter((l) => matchesQuery(l, q)).slice(0, MAX_SUGGESTIONS);
  }, [findMode, query, locations]);

  const selected = useMemo(
    () => locations.find((l) => l.location_id === selectedId) ?? null,
    [locations, selectedId],
  );

  const enterFindMode = () => {
    const q = query.trim().toLowerCase();
    if (!q) return;
    const results = locations.filter((l) => matchesQuery(l, q));
    if (results.length === 0) return;
    setFindMode({ results, index: 0, term: query.trim() });
    setSelectedId(results[0].location_id);
    setQuery("");
  };

  const nextFind = () => {
    if (!findMode) return;
    const nextIdx = (findMode.index + 1) % findMode.results.length;
    setFindMode({ ...findMode, index: nextIdx });
    setSelectedId(findMode.results[nextIdx].location_id);
  };

  const closeFind = () => {
    setFindMode(null);
  };

  const onInputKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      enterFindMode();
    } else if (e.key === "Escape") {
      setQuery("");
    }
  };

  const pickSuggestion = (loc: ExploreLocation) => {
    setSelectedId(loc.location_id);
    setQuery("");
    inputRef.current?.blur();
  };

  if (isLoading) {
    return (
      <div className="text-muted-foreground flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-3">
        <Loader2 className="text-primary size-8 animate-spin" />
        <p className="text-sm">Đang tải danh sách địa điểm…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-3 px-4 text-center">
        <AlertCircle className="text-destructive size-8" />
        <p className="text-muted-foreground text-sm">Không tải được danh sách địa điểm.</p>
        <code className="bg-muted rounded px-2 py-1 text-xs">
          {error instanceof Error ? error.message : "Unknown error"}
        </code>
      </div>
    );
  }

  if (locations.length === 0) {
    return (
      <div className="text-muted-foreground flex h-[calc(100vh-3.5rem)] flex-col items-center justify-center gap-3">
        <Compass className="size-10 opacity-40" />
        <p className="text-sm">Database hiện chưa có địa điểm nào.</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] w-full">
      <div className={`relative transition-[width] duration-300 ${selected ? "w-3/5" : "w-full"}`}>
        {/* Floating search / find overlay */}
        <div className="pointer-events-none absolute top-3 left-3 z-10 flex w-full max-w-xs flex-col gap-1">
          {findMode ? (
            <FindBar state={findMode} onNext={nextFind} onClose={closeFind} />
          ) : (
            <>
              <div className="border-border/60 bg-background/95 pointer-events-auto flex items-center gap-2 rounded-xl border px-2 py-1.5 shadow-md backdrop-blur">
                <Search className="text-muted-foreground size-4 shrink-0" />
                <Input
                  ref={inputRef}
                  type="search"
                  placeholder="Tìm theo tên hoặc tag, Enter để duyệt…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onInputKeyDown}
                  className="h-7 border-0 bg-transparent shadow-none focus-visible:ring-0"
                />
                {query ? (
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={() => setQuery("")}
                    aria-label="Xoá tìm kiếm"
                    className="shrink-0"
                  >
                    <X className="size-3" />
                  </Button>
                ) : null}
              </div>

              {suggestions.length > 0 ? (
                <div className="border-border/60 bg-background/95 pointer-events-auto overflow-hidden rounded-xl border shadow-md backdrop-blur">
                  <ul className="max-h-72 overflow-y-auto py-1">
                    {suggestions.map((loc) => {
                      const name = (loc.metadata?.name as string | undefined) ?? loc.location_id;
                      return (
                        <li key={loc.location_id}>
                          <button
                            type="button"
                            onClick={() => pickSuggestion(loc)}
                            className="hover:bg-muted flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm"
                          >
                            <Search className="text-muted-foreground size-3 shrink-0" />
                            <span className="truncate">{name}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ) : query.trim() ? (
                <div className="border-border/60 bg-background/95 text-muted-foreground pointer-events-auto rounded-xl border px-3 py-2 text-xs shadow-md backdrop-blur">
                  Không có kết quả phù hợp.
                </div>
              ) : null}
            </>
          )}
        </div>

        <ExploreMap locations={locations} selectedId={selectedId} onSelect={setSelectedId} />
      </div>

      {selected ? (
        <div className="w-2/5">
          <LocationDetail location={selected} onClose={() => setSelectedId(null)} />
        </div>
      ) : null}
    </div>
  );
}

function FindBar({
  state,
  onNext,
  onClose,
}: {
  state: FindState;
  onNext: () => void;
  onClose: () => void;
}) {
  return (
    <div className="border-primary/40 bg-background/95 pointer-events-auto flex items-center gap-2 rounded-xl border px-2 py-1.5 shadow-md backdrop-blur">
      <Search className="text-primary size-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="text-foreground truncate text-sm font-semibold">“{state.term}”</div>
        <div className="text-muted-foreground font-mono text-[10px]">
          {state.index + 1} / {state.results.length}
        </div>
      </div>
      <Button variant="outline" size="xs" onClick={onNext} disabled={state.results.length <= 1}>
        Next
        <ChevronRight className="size-3" />
      </Button>
      <Button variant="ghost" size="icon-xs" onClick={onClose} aria-label="Thoát Find mode">
        <X className="size-3" />
      </Button>
    </div>
  );
}
