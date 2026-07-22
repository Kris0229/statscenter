import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  ApiError,
  deleteMedia,
  fetchGameMedia,
  fetchMe,
  resolveMediaUrl,
  updateMediaStatus,
  uploadMediaLink,
  uploadPhoto,
} from "../api/client";
import type { Media } from "../api/types";

export function MediaWall({ gameId }: { gameId: number }) {
  const queryClient = useQueryClient();
  const mediaQuery = useQuery({
    queryKey: ["media", "game", gameId],
    queryFn: () => fetchGameMedia(gameId),
  });
  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe });

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
    <div className="no-print" style={{ marginTop: "2rem" }}>
      <h2>媒體牆</h2>
      {mediaQuery.isLoading && <p>載入中…</p>}
      {mediaQuery.data && mediaQuery.data.length === 0 && <p>尚無媒體。</p>}

      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
        {mediaQuery.data?.map((m) => (
          <div
            key={m.id}
            style={{
              border: "1px solid #ddd", padding: "0.5rem", width: 180,
              opacity: m.status === "inactive" ? 0.4 : 1,
            }}
          >
            {m.type === "photo" ? (
              <img
                src={resolveMediaUrl(m.url)}
                alt=""
                style={{ maxWidth: "100%", display: "block" }}
              />
            ) : (
              <a href={m.url} target="_blank" rel="noreferrer">
                {m.type === "video" ? "▶ 影片連結" : "🔗 連結"}
              </a>
            )}
            {m.status === "inactive" && <div style={{ fontSize: "0.75rem" }}>(已隱藏)</div>}
            <div style={{ fontSize: "0.75rem", marginTop: "0.25rem", display: "flex", gap: "0.5rem" }}>
              {isAdmin && (
                <button type="button" onClick={() => handleToggleHide(m)}>
                  {m.status === "active" ? "隱藏" : "顯示"}
                </button>
              )}
              {(isAdmin || m.uploader_id === myUserId) && (
                <button type="button" onClick={() => handleDelete(m)}>
                  刪除
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: "1rem" }}>
        <label>
          上傳照片:{" "}
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={handleFileChange}
            disabled={busy}
          />
        </label>
      </div>
      <form onSubmit={handleLinkSubmit} style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem" }}>
        <select value={linkType} onChange={(e) => setLinkType(e.target.value as "video" | "link")}>
          <option value="video">影片連結(YouTube)</option>
          <option value="link">其他連結</option>
        </select>
        <input
          type="url"
          placeholder="https://..."
          value={linkUrl}
          onChange={(e) => setLinkUrl(e.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={busy}>
          新增
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
    </div>
  );
}
