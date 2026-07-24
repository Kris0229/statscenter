import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

import {
  ApiError,
  fetchGameMedia,
  fetchReport,
  publishReport,
  resolveMediaUrl,
  updateReport,
} from "@/api/client";
import { useMe } from "@/hooks/useMe";
import { FormField } from "@/components/FormField";
import { FormError } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { ReportStatusBadge } from "@/components/StatusBadge";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function ReportPage() {
  const params = useParams<{ reportId: string }>();
  const reportId = Number(params.reportId);
  const queryClient = useQueryClient();

  const reportQuery = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => fetchReport(reportId),
    enabled: Number.isFinite(reportId),
  });
  const meQuery = useMe();

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
  const [confirmPublishOpen, setConfirmPublishOpen] = useState(false);

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
      setConfirmPublishOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "發布失敗");
    } finally {
      setPublishing(false);
    }
  }

  if (reportQuery.isLoading) return <LoadingBlock />;
  if (reportQuery.isError || !reportQuery.data) {
    return <FormError message="無法載入報導（可能尚未發布）" />;
  }

  const report = reportQuery.data;
  const isAdmin = meQuery.data?.role === "admin";
  const cover = mediaQuery.data?.find((m) => m.id === report.cover_media_id);

  return (
    <div className="max-w-2xl">
      <Link
        to={`/games/${report.game_id}/boxscore`}
        className="mb-4 inline-flex items-center gap-1 text-sm text-primary hover:underline"
      >
        <ArrowLeft className="size-4" />
        回比賽紀錄表
      </Link>

      {cover && cover.type === "photo" && (
        <img src={resolveMediaUrl(cover.url)} alt="" className="mb-4 w-full rounded-lg object-cover" />
      )}

      {isAdmin ? (
        <Card>
          <CardContent className="grid gap-4">
            <div className="flex items-center gap-2">
              <ReportStatusBadge publishedAt={report.published_at} />
            </div>
            <FormField label="標題" htmlFor="report-title">
              <Input
                id="report-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="text-lg font-semibold"
              />
            </FormField>
            <FormField label="內容" htmlFor="report-content">
              <Textarea
                id="report-content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={12}
              />
            </FormField>
            <FormError message={error} />
            <div className="flex gap-3">
              <Button type="button" variant="outline" onClick={handleSave} disabled={saving}>
                {saving ? "儲存中…" : "儲存"}
              </Button>
              <Button
                type="button"
                onClick={() => setConfirmPublishOpen(true)}
                disabled={publishing || !!report.published_at}
              >
                {report.published_at ? "已發布" : publishing ? "發布中…" : "發布"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{report.title}</h1>
          <div className="mt-4 whitespace-pre-wrap text-foreground">{report.content}</div>
        </>
      )}

      <ConfirmDialog
        open={confirmPublishOpen}
        onOpenChange={setConfirmPublishOpen}
        title="確認發布這篇報導？"
        description="發布後將公開顯示，此動作無法復原。"
        confirmLabel="確認發布"
        onConfirm={handlePublish}
        busy={publishing}
      />
    </div>
  );
}
