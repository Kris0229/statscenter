import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  bootstrapLeagueAdmin,
  createLeague,
  fetchLeagues,
} from "../../api/client";

export function LeaguesPage() {
  const queryClient = useQueryClient();
  const leaguesQuery = useQuery({ queryKey: ["admin", "leagues"], queryFn: fetchLeagues });

  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [adminFormLeagueId, setAdminFormLeagueId] = useState<number | null>(null);
  const [adminEmail, setAdminEmail] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [adminError, setAdminError] = useState<string | null>(null);
  const [adminSubmitting, setAdminSubmitting] = useState(false);
  const [adminSuccess, setAdminSuccess] = useState<string | null>(null);

  function refresh() {
    queryClient.invalidateQueries({ queryKey: ["admin", "leagues"] });
  }

  async function handleCreateLeague(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createLeague({ name, slug });
      setName("");
      setSlug("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立聯盟失敗");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateAdmin(e: FormEvent) {
    e.preventDefault();
    if (adminFormLeagueId === null) return;
    setAdminError(null);
    setAdminSuccess(null);
    setAdminSubmitting(true);
    try {
      const created = await bootstrapLeagueAdmin(adminFormLeagueId, {
        email: adminEmail, display_name: adminName, password: adminPassword,
      });
      setAdminSuccess(`已建立管理員:${created.email}`);
      setAdminEmail("");
      setAdminName("");
      setAdminPassword("");
    } catch (err) {
      setAdminError(err instanceof ApiError ? err.message : "指派管理員失敗");
    } finally {
      setAdminSubmitting(false);
    }
  }

  if (leaguesQuery.isLoading) return <p>載入中…</p>;

  return (
    <div style={{ maxWidth: 720 }}>
      <h1>聯盟管理</h1>

      <h2 style={{ fontSize: "1.1rem" }}>新增聯盟</h2>
      <form onSubmit={handleCreateLeague} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        <input placeholder="聯盟名稱" value={name} onChange={(e) => setName(e.target.value)} required />
        <input placeholder="slug (英數/連字號)" value={slug} onChange={(e) => setSlug(e.target.value)} required />
        <button type="submit" disabled={submitting}>
          {submitting ? "建立中…" : "建立"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <h2 style={{ fontSize: "1.1rem" }}>聯盟列表</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={thStyle}>名稱</th>
            <th style={thStyle}>Slug</th>
            <th style={thStyle}>狀態</th>
            <th style={thStyle}></th>
          </tr>
        </thead>
        <tbody>
          {leaguesQuery.data?.map((league) => (
            <tr key={league.id}>
              <td style={tdStyle}>{league.name}</td>
              <td style={tdStyle}>{league.slug}</td>
              <td style={tdStyle}>{league.status}</td>
              <td style={tdStyle}>
                <button
                  type="button"
                  onClick={() => {
                    setAdminFormLeagueId(league.id);
                    setAdminError(null);
                    setAdminSuccess(null);
                  }}
                >
                  指派管理員
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {adminFormLeagueId !== null && (
        <div style={{ marginTop: "1.5rem", border: "1px solid #ddd", padding: "1rem" }}>
          <h2 style={{ fontSize: "1.1rem", marginTop: 0 }}>
            指派管理員 —{" "}
            {leaguesQuery.data?.find((l) => l.id === adminFormLeagueId)?.name}
          </h2>
          <form onSubmit={handleCreateAdmin}>
            <label style={fieldStyle}>
              Email
              <input
                type="email"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                required
                style={inputStyle}
              />
            </label>
            <label style={fieldStyle}>
              姓名
              <input
                value={adminName}
                onChange={(e) => setAdminName(e.target.value)}
                required
                style={inputStyle}
              />
            </label>
            <label style={fieldStyle}>
              初始密碼
              <input
                type="password"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                required
                style={inputStyle}
              />
            </label>
            {adminError && <p style={{ color: "crimson" }}>{adminError}</p>}
            {adminSuccess && <p style={{ color: "green" }}>{adminSuccess}</p>}
            <button type="submit" disabled={adminSubmitting}>
              {adminSubmitting ? "建立中…" : "建立管理員帳號"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

const thStyle = { textAlign: "left" as const, borderBottom: "1px solid #ddd", padding: "0.4rem" };
const tdStyle = { borderBottom: "1px solid #eee", padding: "0.4rem" };
const fieldStyle = { display: "block", marginBottom: "0.75rem" };
const inputStyle = { display: "block", width: "100%", padding: "0.4rem", marginTop: "0.25rem" };
