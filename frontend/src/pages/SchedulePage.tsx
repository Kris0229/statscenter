import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  ApiError,
  createGame,
  createSeason,
  downloadScheduleTemplate,
  fetchSeasons,
  fetchTeams,
  importSchedule,
} from "@/api/client";
import type { ImportResult } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { FormError, FormSuccess } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface ManualRow {
  gameDate: string;
  startTime: string;
  venue: string;
  matchNo: string;
  awayTeamId: number | "";
  homeTeamId: number | "";
}

function emptyRow(): ManualRow {
  return { gameDate: "", startTime: "", venue: "", matchNo: "", awayTeamId: "", homeTeamId: "" };
}

const nativeInputClass =
  "h-8 w-full rounded-md border border-input bg-transparent px-2 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50";

export function SchedulePage() {
  const queryClient = useQueryClient();
  const seasonsQuery = useQuery({ queryKey: ["seasons"], queryFn: fetchSeasons });
  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  const currentSeason = seasonsQuery.data?.find((s) => s.is_current) ?? seasonsQuery.data?.[0];

  // --- create season (only shown when none exists yet) ---
  const [seasonYear, setSeasonYear] = useState(new Date().getFullYear());
  const [seasonName, setSeasonName] = useState("");
  const [seasonError, setSeasonError] = useState<string | null>(null);
  const [seasonSubmitting, setSeasonSubmitting] = useState(false);

  async function handleCreateSeason(e: FormEvent) {
    e.preventDefault();
    setSeasonError(null);
    setSeasonSubmitting(true);
    try {
      await createSeason({ year: seasonYear, name: seasonName, is_current: true });
      setSeasonName("");
      queryClient.invalidateQueries({ queryKey: ["seasons"] });
    } catch (err) {
      setSeasonError(err instanceof ApiError ? err.message : "建立球季失敗");
    } finally {
      setSeasonSubmitting(false);
    }
  }

  // --- manual multi-row schedule entry ---
  const [rows, setRows] = useState<ManualRow[]>([emptyRow()]);
  const [manualError, setManualError] = useState<string | null>(null);
  const [manualSubmitting, setManualSubmitting] = useState(false);
  const [manualResult, setManualResult] = useState<string | null>(null);

  function updateRow(index: number, patch: Partial<ManualRow>) {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  async function handleSubmitManual(e: FormEvent) {
    e.preventDefault();
    if (!currentSeason) return;
    setManualError(null);
    setManualResult(null);
    setManualSubmitting(true);
    let created = 0;
    try {
      for (const row of rows) {
        if (row.gameDate === "" || row.awayTeamId === "" || row.homeTeamId === "") continue;
        await createGame({
          season_id: currentSeason.id,
          game_date: row.gameDate,
          start_time: row.startTime || undefined,
          venue: row.venue || undefined,
          code: row.matchNo || undefined,
          away_team_id: row.awayTeamId,
          home_team_id: row.homeTeamId,
        });
        created += 1;
      }
      setManualResult(`已建立 ${created} 場比賽。`);
      setRows([emptyRow()]);
      queryClient.invalidateQueries({ queryKey: ["games"] });
    } catch (err) {
      setManualError(
        (err instanceof ApiError ? err.message : "建立賽程失敗") + `(已成功建立 ${created} 場)`,
      );
    } finally {
      setManualSubmitting(false);
    }
  }

  // --- excel schedule import ---
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  async function handleImportFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !currentSeason) return;
    setImportError(null);
    setImportResult(null);
    setImportBusy(true);
    try {
      const result = await importSchedule(currentSeason.id, file);
      setImportResult(result);
      if (result.errors.length === 0 && !result.committed) {
        setPendingFile(file);
      }
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
      e.target.value = "";
    }
  }

  async function handleConfirmImport() {
    if (!pendingFile || !currentSeason) return;
    setImportBusy(true);
    setImportError(null);
    try {
      const result = await importSchedule(currentSeason.id, pendingFile, true);
      setImportResult(result);
      setPendingFile(null);
      queryClient.invalidateQueries({ queryKey: ["games"] });
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
    }
  }

  if (seasonsQuery.isLoading || teamsQuery.isLoading) return <LoadingBlock />;

  if (!currentSeason) {
    return (
      <div className="max-w-md">
        <PageHeader title="賽程管理" description="尚未建立球季，請先建立球季才能安排賽程。" />
        <Card>
          <CardContent>
            <form onSubmit={handleCreateSeason} className="grid gap-4">
              <FormField label="年度" htmlFor="season-year" required>
                <Input
                  id="season-year"
                  type="number"
                  value={seasonYear}
                  onChange={(e) => setSeasonYear(Number(e.target.value))}
                  required
                />
              </FormField>
              <FormField label="球季名稱" htmlFor="season-name" required>
                <Input id="season-name" value={seasonName} onChange={(e) => setSeasonName(e.target.value)} required />
              </FormField>
              <FormError message={seasonError} />
              <Button type="submit" disabled={seasonSubmitting}>
                {seasonSubmitting ? "建立中…" : "建立球季"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <PageHeader title="賽程管理" description={`球季：${currentSeason.name}（${currentSeason.year}）`} />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>手動新增賽程</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmitManual}>
            <Table className="mb-3">
              <TableHeader>
                <TableRow>
                  <TableHead>場次</TableHead>
                  <TableHead>日期</TableHead>
                  <TableHead>時間</TableHead>
                  <TableHead>場地</TableHead>
                  <TableHead>先攻（客隊）</TableHead>
                  <TableHead>後攻（主隊）</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <input
                        value={row.matchNo}
                        onChange={(e) => updateRow(i, { matchNo: e.target.value })}
                        className={nativeInputClass}
                      />
                    </TableCell>
                    <TableCell>
                      <input
                        type="date"
                        value={row.gameDate}
                        onChange={(e) => updateRow(i, { gameDate: e.target.value })}
                        className={nativeInputClass}
                      />
                    </TableCell>
                    <TableCell>
                      <input
                        type="time"
                        value={row.startTime}
                        onChange={(e) => updateRow(i, { startTime: e.target.value })}
                        className={nativeInputClass}
                      />
                    </TableCell>
                    <TableCell>
                      <input
                        value={row.venue}
                        onChange={(e) => updateRow(i, { venue: e.target.value })}
                        className={nativeInputClass}
                      />
                    </TableCell>
                    <TableCell>
                      <select
                        value={row.awayTeamId}
                        onChange={(e) => updateRow(i, { awayTeamId: e.target.value ? Number(e.target.value) : "" })}
                        className={nativeInputClass}
                      >
                        <option value="">請選擇</option>
                        {teamsQuery.data?.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </TableCell>
                    <TableCell>
                      <select
                        value={row.homeTeamId}
                        onChange={(e) => updateRow(i, { homeTeamId: e.target.value ? Number(e.target.value) : "" })}
                        className={nativeInputClass}
                      >
                        <option value="">請選擇</option>
                        {teamsQuery.data?.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={() => setRows((prev) => [...prev, emptyRow()])}>
                + 新增一列
              </Button>
              <Button type="submit" disabled={manualSubmitting}>
                {manualSubmitting ? "建立中…" : "全部建立"}
              </Button>
            </div>
            <FormError message={manualError} />
            <FormSuccess message={manualResult} />
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Excel 批次匯入賽程</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" onClick={() => downloadScheduleTemplate(currentSeason.id)}>
              下載範本
            </Button>
            <Input
              type="file"
              accept=".xlsx"
              onChange={handleImportFile}
              disabled={importBusy}
              className="max-w-xs"
            />
          </div>
          <FormError message={importError} />
          {importResult && importResult.errors.length > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>列</TableHead>
                  <TableHead>欄位</TableHead>
                  <TableHead>錯誤</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {importResult.errors.map((e, i) => (
                  <TableRow key={i}>
                    <TableCell>{e.row}</TableCell>
                    <TableCell>{e.field}</TableCell>
                    <TableCell>{e.msg}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {importResult && importResult.committed && (
            <FormSuccess message={`匯入成功，共 ${importResult.valid_rows} 場。`} />
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={pendingFile !== null}
        onOpenChange={(open) => {
          if (!open) setPendingFile(null);
        }}
        title="確認建立這些比賽？"
        description={`預覽通過，共 ${importResult?.valid_rows ?? 0} 場。`}
        confirmLabel="確認建立"
        onConfirm={handleConfirmImport}
        busy={importBusy}
      />
    </div>
  );
}
