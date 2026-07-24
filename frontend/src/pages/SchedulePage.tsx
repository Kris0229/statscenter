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
} from "../api/client";
import type { ImportResult } from "../api/types";

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

  if (seasonsQuery.isLoading || teamsQuery.isLoading) return <p>載入中…</p>;

  if (!currentSeason) {
    return (
      <div style={{ maxWidth: 420 }}>
        <h1>賽程管理</h1>
        <p>尚未建立球季,請先建立球季才能安排賽程。</p>
        <form onSubmit={handleCreateSeason}>
          <label style={fieldStyle}>
            年度
            <input
              type="number" value={seasonYear}
              onChange={(e) => setSeasonYear(Number(e.target.value))} required style={inputStyle}
            />
          </label>
          <label style={fieldStyle}>
            球季名稱
            <input value={seasonName} onChange={(e) => setSeasonName(e.target.value)} required style={inputStyle} />
          </label>
          {seasonError && <p style={{ color: "crimson" }}>{seasonError}</p>}
          <button type="submit" disabled={seasonSubmitting}>
            {seasonSubmitting ? "建立中…" : "建立球季"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 900 }}>
      <h1>賽程管理</h1>
      <p>
        球季:{currentSeason.name}({currentSeason.year})
      </p>

      <h2 style={{ fontSize: "1.1rem" }}>手動新增賽程</h2>
      <form onSubmit={handleSubmitManual}>
        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "0.5rem" }}>
          <thead>
            <tr>
              <th style={thStyle}>場次</th>
              <th style={thStyle}>日期</th>
              <th style={thStyle}>時間</th>
              <th style={thStyle}>場地</th>
              <th style={thStyle}>先攻(客隊)</th>
              <th style={thStyle}>後攻(主隊)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td style={tdStyle}>
                  <input
                    value={row.matchNo} onChange={(e) => updateRow(i, { matchNo: e.target.value })}
                    style={{ width: 60 }}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    type="date" value={row.gameDate}
                    onChange={(e) => updateRow(i, { gameDate: e.target.value })}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    type="time" value={row.startTime}
                    onChange={(e) => updateRow(i, { startTime: e.target.value })}
                  />
                </td>
                <td style={tdStyle}>
                  <input
                    value={row.venue} onChange={(e) => updateRow(i, { venue: e.target.value })}
                    style={{ width: 100 }}
                  />
                </td>
                <td style={tdStyle}>
                  <select
                    value={row.awayTeamId}
                    onChange={(e) => updateRow(i, { awayTeamId: e.target.value ? Number(e.target.value) : "" })}
                  >
                    <option value="">請選擇</option>
                    {teamsQuery.data?.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td style={tdStyle}>
                  <select
                    value={row.homeTeamId}
                    onChange={(e) => updateRow(i, { homeTeamId: e.target.value ? Number(e.target.value) : "" })}
                  >
                    <option value="">請選擇</option>
                    {teamsQuery.data?.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" onClick={() => setRows((prev) => [...prev, emptyRow()])}>
          + 新增一列
        </button>{" "}
        <button type="submit" disabled={manualSubmitting}>
          {manualSubmitting ? "建立中…" : "全部建立"}
        </button>
        {manualError && <p style={{ color: "crimson" }}>{manualError}</p>}
        {manualResult && <p style={{ color: "green" }}>{manualResult}</p>}
      </form>

      <h2 style={{ fontSize: "1.1rem", marginTop: "2rem" }}>Excel 批次匯入賽程</h2>
      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.5rem" }}>
        <button type="button" onClick={() => downloadScheduleTemplate(currentSeason.id)}>
          下載範本
        </button>
        <input type="file" accept=".xlsx" onChange={handleImportFile} disabled={importBusy} />
      </div>
      {pendingFile && (
        <div style={{ marginBottom: "0.5rem" }}>
          <p>預覽通過,共 {importResult?.valid_rows} 場。確認要建立這些比賽嗎?</p>
          <button type="button" onClick={handleConfirmImport} disabled={importBusy}>
            {importBusy ? "處理中…" : "確認建立"}
          </button>
        </div>
      )}
      {importError && <p style={{ color: "crimson" }}>{importError}</p>}
      {importResult && importResult.errors.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr>
              <th style={thStyle}>列</th>
              <th style={thStyle}>欄位</th>
              <th style={thStyle}>錯誤</th>
            </tr>
          </thead>
          <tbody>
            {importResult.errors.map((e, i) => (
              <tr key={i}>
                <td style={tdStyle}>{e.row}</td>
                <td style={tdStyle}>{e.field}</td>
                <td style={tdStyle}>{e.msg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {importResult && importResult.committed && (
        <p style={{ color: "green" }}>匯入成功,共 {importResult.valid_rows} 場。</p>
      )}
    </div>
  );
}

const thStyle = { textAlign: "left" as const, borderBottom: "1px solid #ddd", padding: "0.4rem" };
const tdStyle = { borderBottom: "1px solid #eee", padding: "0.4rem" };
const fieldStyle = { display: "block", marginBottom: "0.75rem" };
const inputStyle = { display: "block", width: "100%", padding: "0.4rem", marginTop: "0.25rem" };
