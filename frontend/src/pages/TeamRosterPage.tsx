import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { useParams } from "react-router-dom";

import {
  addPlayer,
  ApiError,
  createPlayerAccount,
  createTeamCaptainAccount,
  downloadRosterTemplate,
  fetchMe,
  fetchPlayerDetail,
  fetchTeam,
  fetchTeamPlayers,
  importRoster,
} from "../api/client";
import type { ImportResult } from "../api/types";

const TITLE_LABELS: Record<string, string> = {
  manager: "領隊",
  coach: "教練",
  captain: "隊長",
  member: "隊員",
};

export function TeamRosterPage() {
  const { teamId: teamIdParam } = useParams();
  const teamId = Number(teamIdParam);
  const queryClient = useQueryClient();

  const meQuery = useQuery({ queryKey: ["me"], queryFn: fetchMe });
  const teamQuery = useQuery({ queryKey: ["team", teamId], queryFn: () => fetchTeam(teamId) });
  const playersQuery = useQuery({
    queryKey: ["team", teamId, "players"],
    queryFn: () => fetchTeamPlayers(teamId),
  });

  const isAdmin = meQuery.data?.role === "admin";

  function refreshPlayers() {
    queryClient.invalidateQueries({ queryKey: ["team", teamId, "players"] });
  }
  function refreshTeam() {
    queryClient.invalidateQueries({ queryKey: ["team", teamId] });
  }

  // --- national_id on-demand reveal ---
  const [revealed, setRevealed] = useState<Record<number, string | null>>({});
  async function handleReveal(playerId: number) {
    const detail = await fetchPlayerDetail(playerId);
    setRevealed((prev) => ({ ...prev, [playerId]: detail.national_id }));
  }

  // --- captain account ---
  const [showCaptainForm, setShowCaptainForm] = useState(false);
  const [captainEmail, setCaptainEmail] = useState("");
  const [captainName, setCaptainName] = useState("");
  const [captainPassword, setCaptainPassword] = useState("");
  const [captainError, setCaptainError] = useState<string | null>(null);
  const [captainSubmitting, setCaptainSubmitting] = useState(false);

  async function handleCreateCaptain(e: FormEvent) {
    e.preventDefault();
    setCaptainError(null);
    setCaptainSubmitting(true);
    try {
      await createTeamCaptainAccount(teamId, {
        email: captainEmail, password: captainPassword, display_name: captainName,
      });
      setShowCaptainForm(false);
      setCaptainEmail("");
      setCaptainName("");
      setCaptainPassword("");
      refreshTeam();
    } catch (err) {
      setCaptainError(err instanceof ApiError ? err.message : "建立隊長帳號失敗");
    } finally {
      setCaptainSubmitting(false);
    }
  }

  // --- per-player account creation ---
  const [accountFormPlayerId, setAccountFormPlayerId] = useState<number | null>(null);
  const [accountEmail, setAccountEmail] = useState("");
  const [accountPassword, setAccountPassword] = useState("");
  const [accountError, setAccountError] = useState<string | null>(null);
  const [accountSubmitting, setAccountSubmitting] = useState(false);

  async function handleCreatePlayerAccount(e: FormEvent) {
    e.preventDefault();
    if (accountFormPlayerId === null) return;
    setAccountError(null);
    setAccountSubmitting(true);
    try {
      await createPlayerAccount(accountFormPlayerId, { email: accountEmail, password: accountPassword });
      setAccountFormPlayerId(null);
      setAccountEmail("");
      setAccountPassword("");
      refreshPlayers();
    } catch (err) {
      setAccountError(err instanceof ApiError ? err.message : "建立帳號失敗");
    } finally {
      setAccountSubmitting(false);
    }
  }

  // --- manual add player ---
  const [pName, setPName] = useState("");
  const [pNumber, setPNumber] = useState("");
  const [pPositions, setPPositions] = useState("");
  const [pTitle, setPTitle] = useState("member");
  const [pBirthdate, setPBirthdate] = useState("");
  const [pNationalId, setPNationalId] = useState("");
  const [pEmail, setPEmail] = useState("");
  const [pPhone, setPPhone] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [addSubmitting, setAddSubmitting] = useState(false);

  async function handleAddPlayer(e: FormEvent) {
    e.preventDefault();
    setAddError(null);
    setAddSubmitting(true);
    try {
      await addPlayer(teamId, {
        name: pName,
        number: Number(pNumber),
        positions: pPositions || undefined,
        title: pTitle,
        birthdate: pBirthdate || undefined,
        national_id: pNationalId || undefined,
        email: pEmail || undefined,
        phone: pPhone || undefined,
      });
      setPName("");
      setPNumber("");
      setPPositions("");
      setPTitle("member");
      setPBirthdate("");
      setPNationalId("");
      setPEmail("");
      setPPhone("");
      refreshPlayers();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : "新增球員失敗");
    } finally {
      setAddSubmitting(false);
    }
  }

  // --- excel import ---
  const [importMode, setImportMode] = useState<"append" | "replace">("append");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);

  async function handleImportFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportError(null);
    setImportResult(null);
    setImportBusy(true);
    try {
      const result = await importRoster(teamId, file, { mode: importMode });
      setImportResult(result);
      if (result.committed) {
        refreshPlayers();
        setPendingFile(null);
      } else if (result.errors.length === 0) {
        // replace mode preview — needs a second confirm call
        setPendingFile(file);
      }
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
      e.target.value = "";
    }
  }

  async function handleConfirmReplace() {
    if (!pendingFile) return;
    setImportBusy(true);
    setImportError(null);
    try {
      const result = await importRoster(teamId, pendingFile, { mode: "replace", confirm: true });
      setImportResult(result);
      setPendingFile(null);
      refreshPlayers();
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "匯入失敗");
    } finally {
      setImportBusy(false);
    }
  }

  if (teamQuery.isLoading || playersQuery.isLoading) return <p>載入中…</p>;

  const team = teamQuery.data;

  return (
    <div style={{ maxWidth: 960 }}>
      <h1>{team?.name}</h1>

      {isAdmin && (
        <div style={{ marginBottom: "1.5rem" }}>
          {team?.captain_user_id ? (
            <p style={{ color: "#666" }}>此球隊已有隊長帳號。</p>
          ) : showCaptainForm ? (
            <form onSubmit={handleCreateCaptain} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <input
                type="email" placeholder="隊長 Email" value={captainEmail}
                onChange={(e) => setCaptainEmail(e.target.value)} required
              />
              <input
                placeholder="姓名" value={captainName}
                onChange={(e) => setCaptainName(e.target.value)} required
              />
              <input
                type="password" placeholder="初始密碼" value={captainPassword}
                onChange={(e) => setCaptainPassword(e.target.value)} required
              />
              <button type="submit" disabled={captainSubmitting}>
                {captainSubmitting ? "建立中…" : "建立"}
              </button>
              <button type="button" onClick={() => setShowCaptainForm(false)}>
                取消
              </button>
            </form>
          ) : (
            <button type="button" onClick={() => setShowCaptainForm(true)}>
              建立隊長帳號
            </button>
          )}
          {captainError && <p style={{ color: "crimson" }}>{captainError}</p>}
        </div>
      )}

      <h2 style={{ fontSize: "1.1rem" }}>球員名單</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
        <thead>
          <tr>
            <th style={thStyle}>背號</th>
            <th style={thStyle}>姓名</th>
            <th style={thStyle}>職稱</th>
            <th style={thStyle}>守位</th>
            <th style={thStyle}>生日</th>
            <th style={thStyle}>Email</th>
            <th style={thStyle}>電話</th>
            <th style={thStyle}>身分證字號</th>
            {isAdmin && <th style={thStyle}>帳號</th>}
          </tr>
        </thead>
        <tbody>
          {playersQuery.data?.map((p) => (
            <tr key={p.id}>
              <td style={tdStyle}>{p.number}</td>
              <td style={tdStyle}>{p.name}</td>
              <td style={tdStyle}>{TITLE_LABELS[p.title] ?? p.title}</td>
              <td style={tdStyle}>{p.positions ?? ""}</td>
              <td style={tdStyle}>{p.birthdate ?? ""}</td>
              <td style={tdStyle}>{p.email ?? ""}</td>
              <td style={tdStyle}>{p.phone ?? ""}</td>
              <td style={tdStyle}>
                {revealed[p.id] !== undefined ? (
                  revealed[p.id] ?? "(未填)"
                ) : (
                  <button type="button" onClick={() => handleReveal(p.id)}>
                    顯示
                  </button>
                )}
              </td>
              {isAdmin && (
                <td style={tdStyle}>
                  {p.user_id ? (
                    "已建立"
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        setAccountFormPlayerId(p.id);
                        setAccountError(null);
                      }}
                    >
                      建立登入帳號
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
          {playersQuery.data?.length === 0 && (
            <tr>
              <td style={tdStyle} colSpan={isAdmin ? 9 : 8}>
                尚無球員。
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {accountFormPlayerId !== null && (
        <form
          onSubmit={handleCreatePlayerAccount}
          style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", alignItems: "center" }}
        >
          <span>為球員建立登入帳號:</span>
          <input
            type="email" placeholder="Email" value={accountEmail}
            onChange={(e) => setAccountEmail(e.target.value)} required
          />
          <input
            type="password" placeholder="初始密碼" value={accountPassword}
            onChange={(e) => setAccountPassword(e.target.value)} required
          />
          <button type="submit" disabled={accountSubmitting}>
            {accountSubmitting ? "建立中…" : "建立"}
          </button>
          <button type="button" onClick={() => setAccountFormPlayerId(null)}>
            取消
          </button>
        </form>
      )}
      {accountError && <p style={{ color: "crimson" }}>{accountError}</p>}

      {isAdmin && (
        <>
          <h2 style={{ fontSize: "1.1rem", marginTop: "2rem" }}>手動新增球員</h2>
          <form onSubmit={handleAddPlayer} style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
            <input placeholder="姓名" value={pName} onChange={(e) => setPName(e.target.value)} required />
            <input
              placeholder="背號" type="number" value={pNumber}
              onChange={(e) => setPNumber(e.target.value)} required style={{ width: 80 }}
            />
            <input placeholder="守位" value={pPositions} onChange={(e) => setPPositions(e.target.value)} />
            <select value={pTitle} onChange={(e) => setPTitle(e.target.value)}>
              {Object.entries(TITLE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input type="date" value={pBirthdate} onChange={(e) => setPBirthdate(e.target.value)} />
            <input
              placeholder="身分證字號" value={pNationalId}
              onChange={(e) => setPNationalId(e.target.value)}
            />
            <input placeholder="Email" type="email" value={pEmail} onChange={(e) => setPEmail(e.target.value)} />
            <input placeholder="電話" value={pPhone} onChange={(e) => setPPhone(e.target.value)} />
            <button type="submit" disabled={addSubmitting}>
              {addSubmitting ? "新增中…" : "新增球員"}
            </button>
          </form>
          {addError && <p style={{ color: "crimson" }}>{addError}</p>}

          <h2 style={{ fontSize: "1.1rem", marginTop: "2rem" }}>Excel 匯入球員名單</h2>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.5rem" }}>
            <button type="button" onClick={() => downloadRosterTemplate(teamId)}>
              下載範本
            </button>
            <select value={importMode} onChange={(e) => setImportMode(e.target.value as "append" | "replace")}>
              <option value="append">附加(保留原名單)</option>
              <option value="replace">取代(原名單設為離隊)</option>
            </select>
            <input type="file" accept=".xlsx" onChange={handleImportFile} disabled={importBusy} />
          </div>
          {pendingFile && (
            <div style={{ marginBottom: "0.5rem" }}>
              <p>
                預覽通過,共 {importResult?.valid_rows} 筆。確定要取代目前名單嗎?此動作會將現有球員標記為離隊。
              </p>
              <button type="button" onClick={handleConfirmReplace} disabled={importBusy}>
                {importBusy ? "處理中…" : "確認取代"}
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
            <p style={{ color: "green" }}>匯入成功,共 {importResult.valid_rows} 筆。</p>
          )}
        </>
      )}
    </div>
  );
}

const thStyle = { textAlign: "left" as const, borderBottom: "1px solid #ddd", padding: "0.4rem" };
const tdStyle = { borderBottom: "1px solid #eee", padding: "0.4rem" };
