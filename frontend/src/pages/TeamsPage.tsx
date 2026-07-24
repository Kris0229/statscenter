import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import { ApiError, createTeam, fetchTeams } from "../api/client";

export function TeamsPage() {
  const queryClient = useQueryClient();
  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createTeam({ name });
      setName("");
      queryClient.invalidateQueries({ queryKey: ["teams"] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立球隊失敗");
    } finally {
      setSubmitting(false);
    }
  }

  if (teamsQuery.isLoading) return <p>載入中…</p>;

  return (
    <div style={{ maxWidth: 560 }}>
      <h1>球隊</h1>

      <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
        <input
          placeholder="新增球隊名稱"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "建立中…" : "新增球隊"}
        </button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}

      <ul style={{ listStyle: "none", padding: 0 }}>
        {teamsQuery.data?.map((team) => (
          <li
            key={team.id}
            style={{ padding: "0.5rem 0", borderBottom: "1px solid #eee" }}
          >
            <Link to={`/teams/${team.id}`}>{team.name}</Link>
          </li>
        ))}
        {teamsQuery.data?.length === 0 && <p>尚無球隊。</p>}
      </ul>
    </div>
  );
}
