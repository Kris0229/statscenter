import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, createGame, fetchSeasons, fetchTeams } from "../api/client";

export function NewGamePage() {
  const navigate = useNavigate();
  const seasonsQuery = useQuery({ queryKey: ["seasons"], queryFn: fetchSeasons });
  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  const [gameDate, setGameDate] = useState("");
  const [venue, setVenue] = useState("");
  const [code, setCode] = useState("");
  const [homeTeamId, setHomeTeamId] = useState<number | "">("");
  const [awayTeamId, setAwayTeamId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const currentSeason = seasonsQuery.data?.find((s) => s.is_current) ?? seasonsQuery.data?.[0];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!currentSeason || homeTeamId === "" || awayTeamId === "") return;
    if (homeTeamId === awayTeamId) {
      setError("主隊與客隊不可相同");
      return;
    }
    setSubmitting(true);
    try {
      const game = await createGame({
        season_id: currentSeason.id,
        game_date: gameDate,
        venue: venue || undefined,
        code: code || undefined,
        home_team_id: homeTeamId,
        away_team_id: awayTeamId,
      });
      navigate(`/games/${game.id}/score-entry`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "建立比賽失敗");
    } finally {
      setSubmitting(false);
    }
  }

  if (seasonsQuery.isLoading || teamsQuery.isLoading) return <p>載入中…</p>;

  return (
    <div style={{ maxWidth: 420 }}>
      <h1>新增比賽</h1>
      {currentSeason && (
        <p>
          球季:{currentSeason.name}({currentSeason.year})
        </p>
      )}
      <form onSubmit={handleSubmit}>
        <label style={fieldStyle}>
          日期
          <input
            type="date"
            value={gameDate}
            onChange={(e) => setGameDate(e.target.value)}
            required
            style={inputStyle}
          />
        </label>
        <label style={fieldStyle}>
          客隊
          <select
            value={awayTeamId}
            onChange={(e) => setAwayTeamId(e.target.value ? Number(e.target.value) : "")}
            required
            style={inputStyle}
          >
            <option value="">請選擇</option>
            {teamsQuery.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label style={fieldStyle}>
          主隊
          <select
            value={homeTeamId}
            onChange={(e) => setHomeTeamId(e.target.value ? Number(e.target.value) : "")}
            required
            style={inputStyle}
          >
            <option value="">請選擇</option>
            {teamsQuery.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label style={fieldStyle}>
          場地
          <input value={venue} onChange={(e) => setVenue(e.target.value)} style={inputStyle} />
        </label>
        <label style={fieldStyle}>
          賽事代碼
          <input value={code} onChange={(e) => setCode(e.target.value)} style={inputStyle} />
        </label>
        {error && <p style={{ color: "crimson" }}>{error}</p>}
        <button type="submit" disabled={submitting || !currentSeason}>
          {submitting ? "建立中…" : "建立比賽並開始計分"}
        </button>
      </form>
    </div>
  );
}

const fieldStyle = { display: "block", marginBottom: "0.75rem" };
const inputStyle = { display: "block", width: "100%", padding: "0.4rem", marginTop: "0.25rem" };
