"use client";

import { X, MapPin, ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { labelForTag } from "@/lib/tag-map";
import type { ExploreLocation } from "@/lib/types";

type Props = {
  location: ExploreLocation;
  onClose: () => void;
};

export function LocationDetail({ location, onClose }: Props) {
  const meta = location.metadata ?? {};
  const name = (meta.name as string | undefined) ?? location.location_id;
  const desc = (meta.description as string | undefined) ?? "";
  const tags = Array.isArray(meta.tags) ? (meta.tags as string[]) : [];
  const hasGeo = typeof location.geo?.lat === "number" && typeof location.geo?.lng === "number";

  return (
    <aside className="border-border bg-background flex h-full flex-col border-l">
      <div className="border-border/60 flex items-center justify-between gap-2 border-b px-4 py-3">
        <div className="min-w-0 flex-1">
          <h2 className="text-foreground truncate text-base font-bold">{name}</h2>
          {hasGeo ? (
            <p className="text-muted-foreground font-mono text-[10px]">
              <MapPin className="mr-1 inline size-2.5" />
              {location.geo!.lat!.toFixed(4)}, {location.geo!.lng!.toFixed(4)}
            </p>
          ) : null}
        </div>
        <Button variant="ghost" size="icon-sm" onClick={onClose} aria-label="Đóng">
          <X className="size-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-4 p-4">
          {/* Image */}
          <div className="from-primary/30 to-brand-dim/30 relative aspect-video w-full overflow-hidden rounded-xl bg-gradient-to-br">
            {location.image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={location.image}
                alt={name}
                className="size-full object-cover"
                loading="lazy"
              />
            ) : (
              <div className="text-muted-foreground flex size-full items-center justify-center">
                <ImageIcon className="size-8 opacity-40" />
              </div>
            )}
            {location.images_count > 1 ? (
              <Badge
                variant="outline"
                className="absolute right-2 bottom-2 border-white/30 bg-black/60 text-[10px] text-white"
              >
                +{location.images_count - 1} ảnh
              </Badge>
            ) : null}
          </div>

          {/* Description */}
          {desc ? (
            <div>
              <h3 className="text-muted-foreground mb-1.5 text-[10px] font-semibold tracking-wider uppercase">
                Mô tả
              </h3>
              <p className="text-foreground/90 text-sm leading-relaxed">{desc}</p>
            </div>
          ) : null}

          {/* Tags */}
          {tags.length > 0 ? (
            <div>
              <h3 className="text-muted-foreground mb-1.5 text-[10px] font-semibold tracking-wider uppercase">
                Thẻ
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((t) => (
                  <Badge
                    key={t}
                    variant="outline"
                    className="border-teal/40 bg-teal-soft text-foreground text-xs"
                  >
                    {labelForTag(t)}
                  </Badge>
                ))}
              </div>
            </div>
          ) : null}

          {/* Extra metadata fields (best-effort, skip known) */}
          {Object.entries(meta)
            .filter(
              ([k, v]) => !["name", "description", "tags"].includes(k) && v != null && v !== "",
            )
            .slice(0, 8)
            .map(([k, v]) => (
              <div key={k}>
                <h3 className="text-muted-foreground mb-1 text-[10px] font-semibold tracking-wider uppercase">
                  {k}
                </h3>
                <p className="text-foreground/80 text-xs leading-relaxed">
                  {typeof v === "object" ? JSON.stringify(v) : String(v)}
                </p>
              </div>
            ))}
        </div>
      </ScrollArea>
    </aside>
  );
}
