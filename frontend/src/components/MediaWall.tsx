import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link2, Play } from "lucide-react";

import {
  ApiError,
  deleteMedia,
  fetchGameMedia,
  resolveMediaUrl,
  updateMediaStatus,
  uploadMediaLink,
  uploadPhoto,
} from "@/api/client";
import type { Media } from "@/api/types";
import { useMe } from "@/hooks/useMe";
import { FormError } from "@/components/FormStatus";
import { EmptyState } from "@/components/EmptyState";
import { LoadingBlock } from "@/components/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export function MediaWall({ gameId }: { gameId: number }) {
  const queryClient = useQueryClient();
  const mediaQuery = useQuery({
    queryKey: ["media", "game", gameId],
    queryFn: () => fetchGameMedia(gameId),
  });
  const meQuery = useMe();

  const [linkType, setLinkType] = useState<"video" | "link">("video");
  const [linkUrl, setLinkUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["media", "game", gameId] });
  }

  async function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await uploadPhoto(gameId, file);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "上傳失敗");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  async function handleLinkSubmit(e: FormEvent) {
    e.preventDefault();
    if (!linkUrl) return;
    setBusy(true);
    setError(null);
    try {
      await uploadMediaLink(gameId, linkType, linkUrl);
      setLinkUrl("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "新增失敗");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggleHide(media: Media) {
    await updateMediaStatus(media.id, media.status === "active" ? "inactive" : "active");
    refresh();
  }

  async function handleDelete(media: Media) {
    await deleteMedia(media.id);
    refresh();
  }

  const isAdmin = meQuery.data?.role === "admin";
  const myUserId = meQuery.data?.id;

  return (
    <div className="no-print mt-8">
      <h2 className="mb-3 text-lg font-semibold text-foreground">媒體牆</h2>
      {mediaQuery.isLoading && <LoadingBlock />}
      {mediaQuery.data && mediaQuery.data.length === 0 && <EmptyState message="尚無媒體。" />}

      {mediaQuery.data && mediaQuery.data.length > 0 && (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {mediaQuery.data.map((m) => (
            <Card
              key={m.id}
              className={cn("gap-2 overflow-hidden py-3", m.status === "inactive" && "opacity-40")}
            >
              <CardContent className="px-3">
                {m.type === "photo" ? (
                  <img src={resolveMediaUrl(m.url)} alt="" className="block w-full rounded-md object-cover" />
                ) : (
                  <a
                    href={m.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-sm text-primary hover:underline"
                  >
                    {m.type === "video" ? <Play className="size-4" /> : <Link2 className="size-4" />}
                    {m.type === "video" ? "影片連結" : "連結"}
                  </a>
                )}
                {m.status === "inactive" && (
                  <div className="mt-1 text-xs text-muted-foreground">(已隱藏)</div>
                )}
                <div className="mt-2 flex gap-3">
                  {isAdmin && (
                    <button
                      type="button"
                      onClick={() => handleToggleHide(m)}
                      className="text-xs text-muted-foreground hover:text-foreground hover:underline"
                    >
                      {m.status === "active" ? "隱藏" : "顯示"}
                    </button>
                  )}
                  {(isAdmin || m.uploader_id === myUserId) && (
                    <button
                      type="button"
                      onClick={() => handleDelete(m)}
                      className="text-xs text-destructive hover:underline"
                    >
                      刪除
                    </button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-foreground">
          上傳照片
          <Input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleFileChange}
            disabled={busy}
            className="w-auto"
          />
        </label>
      </div>
      <form onSubmit={handleLinkSubmit} className="mt-2 flex flex-wrap items-center gap-2">
        <Select value={linkType} onValueChange={(v) => setLinkType(v as "video" | "link")}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="video">影片連結（YouTube）</SelectItem>
            <SelectItem value="link">其他連結</SelectItem>
          </SelectContent>
        </Select>
        <Input
          type="url"
          placeholder="https://..."
          value={linkUrl}
          onChange={(e) => setLinkUrl(e.target.value)}
          className="max-w-sm flex-1"
        />
        <Button type="submit" disabled={busy}>
          新增
        </Button>
      </form>
      <FormError message={error} />
    </div>
  );
}
