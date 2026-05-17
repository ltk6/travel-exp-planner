"use client";

import { useCallback, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ImagePlus, Upload, X, ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { usePlannerStore } from "@/store/planner-store";

const ACCEPTED = ["image/png", "image/jpeg", "image/jpg"];
const MAX_FILE_BYTES = 5 * 1024 * 1024; // 5MB
/** Backend accepts ONE image per request (see services.py:142 `image = body.get("image")`). */
const MAX_FILES = 1;

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // strip data URL prefix: "data:image/png;base64,XXXX" → "XXXX"
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export function ImageUpload() {
  const images = usePlannerStore((s) => s.imagesB64);
  const setImages = usePlannerStore((s) => s.setImages);
  const removeImageAt = usePlannerStore((s) => s.removeImageAt);

  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const acceptFiles = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      if (list.length === 0) return;

      const available = MAX_FILES - images.length;
      if (available <= 0) {
        toast.warning(`Tối đa ${MAX_FILES} ảnh. Vui lòng xóa bớt trước khi tải thêm.`);
        return;
      }

      const accepted: File[] = [];
      for (const f of list.slice(0, available)) {
        if (!ACCEPTED.includes(f.type)) {
          toast.error(`Bỏ qua "${f.name}" — chỉ chấp nhận PNG/JPG.`);
          continue;
        }
        if (f.size > MAX_FILE_BYTES) {
          toast.error(`Bỏ qua "${f.name}" — vượt quá 5MB.`);
          continue;
        }
        accepted.push(f);
      }

      if (accepted.length === 0) return;

      setLoading(true);
      try {
        const b64s = await Promise.all(accepted.map(fileToBase64));
        setImages([...images, ...b64s]);
        toast.success(`Đã thêm ${b64s.length} ảnh.`);
      } catch (err) {
        toast.error("Không đọc được ảnh.", {
          description: err instanceof Error ? err.message : undefined,
        });
      } finally {
        setLoading(false);
      }
    },
    [images, setImages],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 text-primary rounded-lg p-2">
            <ImagePlus className="size-5" />
          </div>
          <div className="flex-1">
            <CardTitle>Hình ảnh</CardTitle>
            <CardDescription>
              Tải lên 1 ảnh mô tả phong cảnh — AI sẽ phân tích để tìm địa điểm tương tự. Tối đa 5MB
              · PNG/JPG.
            </CardDescription>
          </div>
          <Badge variant="outline">
            {images.length}/{MAX_FILES}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            void acceptFiles(e.dataTransfer.files);
          }}
          disabled={loading || images.length >= MAX_FILES}
          className={cn(
            "group flex w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed py-10 transition-all",
            dragging
              ? "border-primary bg-primary/10"
              : "border-border bg-muted/30 hover:border-foreground/40 hover:bg-muted/50",
            (loading || images.length >= MAX_FILES) && "cursor-not-allowed opacity-50",
          )}
        >
          <div className="bg-primary/10 text-primary rounded-full p-3 transition-transform group-hover:scale-110">
            <Upload className="size-6" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold">
              {dragging ? "Thả ảnh vào đây" : "Kéo-thả ảnh hoặc click để chọn"}
            </p>
            <p className="text-muted-foreground mt-0.5 text-xs">
              {loading
                ? "Đang xử lý…"
                : images.length >= MAX_FILES
                  ? `Đã đạt giới hạn ${MAX_FILES} ảnh`
                  : `Hỗ trợ nhiều ảnh · còn ${MAX_FILES - images.length} chỗ`}
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED.join(",")}
            className="hidden"
            onChange={(e) => {
              if (e.target.files) void acceptFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </button>

        {images.length > 0 ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {images.map((b64, i) => (
              <ImagePreview
                key={i}
                src={`data:image/jpeg;base64,${b64}`}
                index={i}
                onRemove={() => removeImageAt(i)}
              />
            ))}
          </div>
        ) : (
          <div className="border-border/60 rounded-lg border border-dashed p-4 text-center">
            <ImageIcon className="text-muted-foreground/50 mx-auto size-6" />
            <p className="text-muted-foreground mt-1 text-xs">Chưa có ảnh nào được tải lên</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ImagePreview({
  src,
  index,
  onRemove,
}: {
  src: string;
  index: number;
  onRemove: () => void;
}) {
  return (
    <div className="group border-border relative overflow-hidden rounded-lg border">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={`Ảnh ${index + 1}`} className="aspect-square w-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      <Button
        size="icon-sm"
        variant="destructive"
        onClick={onRemove}
        className="absolute top-1.5 right-1.5 opacity-0 transition-opacity group-hover:opacity-100"
        title={`Xóa ảnh ${index + 1}`}
      >
        <X className="size-3.5" />
      </Button>
      <Badge
        variant="outline"
        className="absolute bottom-1.5 left-1.5 border-white/30 bg-black/60 text-white"
      >
        #{index + 1}
      </Badge>
    </div>
  );
}
