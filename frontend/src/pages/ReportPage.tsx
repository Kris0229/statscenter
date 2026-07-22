import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  fetchGameMedia,
  fetchMe,
  fetchReport,
  publishReport,
  resolveMediaUrl,
  updateReport,
} from "../api/client";

export function ReportPage() {
  const params = useParams<{ reportId: string }>();
  const reportId = Number(params.reportId);
  const queryClient = useQueryClient();

  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => fetchReport(reportId),
    enabled: Number.isFinite(reportId),
  });
  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe });

  const gameId = reportQuery.data?.game_id;
  const mediaQuery = useQuery({
    queryKey: ["media", "game", gameId],
    queryFn: () => fetchGameMedia(gameId!),
    enabled: gameId !== undefined,
  });

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (reportQuery.data) {
      setTitle(reportQuery.data.title);
      setContent(reportQuery.data.content ?? "");
    }
  }, [reportQuery.data]);

  async function handleSave() {
    if (!reportQuery.data) return;
    setSaving(true);
    setError(null);
    try {
      await updateReport(reportQuery.data.id, { title, content });
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (!reportQuery.data) return;
    setPublishing(true);
    setError(null);
    try {
      await publishReport(reportQuery.data.id);
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "發布失敗");
    } finally {
      setPublishing(false);
    }
  }

  if (reportQuery.isLoading) return <p>載入中…</p>;
  if (reportQuery.isError || !reportQuery.data) {
    return <p style={{ color: "crimson" }}>無法載入報導(可能尚未發布)</p>;
  }

  const report = reportQuery.data;
  const isAdmin = meQuery.data?.role === "admin";
  const cover = mediaQuery.data?.find((m) => m.id === report.cover_media_id);

  return (
    <div style={{ maxWidth: 720 }}>
      <p>
        <Link to={`/games/${report.game_id}/boxscore`}>← 回比賽紀錄表</Link>
      </p>

      {cover && cover.type === "photo" && (
        <img
          src={resolveMediaUrl(cover.url)}
          alt=""
          style={{ maxWidth: "100%", marginBottom: "1rem" }}
        />
      )}

      {isAdmin ? (
        <>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ display: "block", width: "100%", fontSize: "1.5rem", marginBottom: "0.5rem" }}
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={12}
            style={{ display: "block", width: "100%", marginBottom: "0.5rem" }}
          />
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button type="button" onClick={handleSave} disabled={saving}>
              {saving ? "儲存中…" : "儲存"}
            </button>
            <button type="button" onClick={handlePublish} disabled={publishing || !!report.published_at}>
              {report.published_at ? "已發布" : publishing ? "發布中…" : "發布"}
            </button>
          </div>
          {error && <p style={{ color: "crimson" }}>{error}</p>}
        </>
      ) : (
        <>
          <h1>{report.title}</h1>
          <div style={{ whiteSpace: "pre-wrap" }}>{report.content}</div>
        </>
      )}
    </div>
  );
}
