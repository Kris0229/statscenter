import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  ApiError,
  fetchBattingLines,
  fetchGame,
  fetchPitchingLines,
  fetchSeasons,
  fetchTeam,
  fetchTeamPlayers,
  finalizeGame,
  patchGameLineScore,
  putBattingLines,
  putPitchingLines,
  validateGame,
} from "@/api/client";
import type { BattingLine, GameLineScore, PitchingLine, ValidateResult } from "@/api/types";
import { FormError } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { BattingRow } from "./scoreEntry/BattingGrid";
import { BattingGrid, blankBattingRow } from "./scoreEntry/BattingGrid";
import { LineScoreEntry } from "./scoreEntry/LineScoreEntry";
import type { PitchingRowState } from "./scoreEntry/PitchingGrid";
import { PitchingGrid, blankPitchingLine, blankPitchingRow } from "./scoreEntry/PitchingGrid";
import "./scoreEntry/ScoreEntryPage.css";
import { computeRLobPo } from "./scoreEntry/validation";

const DEFAULT_BATTING_ROWS = 10;

const emptyLineScore: GameLineScore = {
  home: [], away: [], home_e: 0, away_e: 0, home_lob: 0, away_lob: 0,
};

export function ScoreEntryPage() {
  const params = useParams<{ gameId: string }>();
  const gameId = Number(params.gameId);
  const navigate = useNavigate();

  const initialDataQuery = useQuery({
    queryKey: ["score-entry-init", gameId],
    queryFn: async () => {
      const game = await fetchGame(gameId);
      const [seasons, homeTeam, awayTeam, homePlayers, awayPlayers, battingLines, pitchingLines] =
        await Promise.all([
          fetchSeasons(),
          fetchTeam(game.home_team_id),
          fetchTeam(game.away_team_id),
          fetchTeamPlayers(game.home_team_id),
          fetchTeamPlayers(game.away_team_id),
          fetchBattingLines(gameId),
          fetchPitchingLines(gameId),
        ]);
      return { game, seasons, homeTeam, awayTeam, homePlayers, awayPlayers, battingLines, pitchingLines };
    },
    enabled: Number.isFinite(gameId),
  });

  const [seeded, setSeeded] = useState(false);
  const [innings, setInnings] = useState(7);
  const [homeBatting, setHomeBatting] = useState<BattingRow[]>([]);
  const [awayBatting, setAwayBatting] = useState<BattingRow[]>([]);
  const [homePitching, setHomePitching] = useState<PitchingRowState[]>([]);
  const [awayPitching, setAwayPitching] = useState<PitchingRowState[]>([]);
  const [lineScore, setLineScore] = useState<GameLineScore>(emptyLineScore);

  const [validateResult, setValidateResult] = useState<ValidateResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (seeded || !initialDataQuery.data) return;
    const { game, seasons, homePlayers, awayPlayers, battingLines, pitchingLines } = initialDataQuery.data;

    const season = seasons.find((s) => s.id === game.season_id);
    const inn = season?.innings_per_game ?? 7;
    setInnings(inn);

    const homeIds = new Set(homePlayers.map((p) => p.id));
    const awayIds = new Set(awayPlayers.map((p) => p.id));

    const seedBattingTeam = (roster: typeof homePlayers, teamIds: Set<number>) => {
      const existing = battingLines
        .filter((l) => teamIds.has(l.player_id))
        .slice()
        .sort((a, b) => (a.bat_order ?? 999) - (b.bat_order ?? 999));
      const rows: BattingRow[] = existing.map((line) => ({
        line,
        numberText: roster.find((p) => p.id === line.player_id)?.number?.toString() ?? "",
      }));
      while (rows.length < DEFAULT_BATTING_ROWS) rows.push(blankBattingRow());
      return rows;
    };
    setHomeBatting(seedBattingTeam(homePlayers, homeIds));
    setAwayBatting(seedBattingTeam(awayPlayers, awayIds));

    const seedPitchingTeam = (roster: typeof homePlayers, teamIds: Set<number>) => {
      const existing = pitchingLines.filter((l) => teamIds.has(l.player_id));
      const rows: PitchingRowState[] = existing.map((line) => ({
        line,
        numberText: roster.find((p) => p.id === line.player_id)?.number?.toString() ?? "",
      }));
      return rows.length > 0 ? rows : [blankPitchingRow()];
    };
    setHomePitching(seedPitchingTeam(homePlayers, homeIds));
    setAwayPitching(seedPitchingTeam(awayPlayers, awayIds));

    const ls = (game.line_score ?? {}) as Partial<GameLineScore>;
    setLineScore({
      home: ls.home ?? Array(inn).fill(0),
      away: ls.away ?? Array(inn).fill(0),
      home_e: ls.home_e ?? 0,
      away_e: ls.away_e ?? 0,
      home_lob: ls.home_lob ?? 0,
      away_lob: ls.away_lob ?? 0,
    });

    setSeeded(true);
  }, [initialDataQuery.data, seeded]);

  function handleBattingChange(
    team: "home" | "away",
    index: number,
    field: keyof BattingLine,
    value: number | string | null,
  ) {
    const setter = team === "home" ? setHomeBatting : setAwayBatting;
    setter((prev) => prev.map((row, i) => (i === index ? { ...row, line: { ...row.line, [field]: value } } : row)));
  }

  function handleBattingNumberChange(team: "home" | "away", index: number, value: string) {
    const setter = team === "home" ? setHomeBatting : setAwayBatting;
    setter((prev) => prev.map((row, i) => (i === index ? { ...row, numberText: value } : row)));
  }

  function resolvePlayerByNumber(roster: { id: number; number: number }[], typed: string) {
    const typedNum = Number(typed);
    return roster.find((p) => p.number === typedNum) ?? null;
  }

  function handleBattingNumberBlur(team: "home" | "away", index: number) {
    const data = initialDataQuery.data;
    if (!data) return;
    const roster = team === "home" ? data.homePlayers : data.awayPlayers;
    const rows = team === "home" ? homeBatting : awayBatting;
    const setter = team === "home" ? setHomeBatting : setAwayBatting;
    const typed = rows[index].numberText.trim();

    if (typed === "") {
      setter((prev) => prev.map((r, i) => (i === index ? { ...r, line: { ...r.line, player_id: 0 } } : r)));
      return;
    }
    const match = resolvePlayerByNumber(roster, typed);
    if (match) {
      setter((prev) => prev.map((r, i) => (i === index ? { ...r, line: { ...r.line, player_id: match.id } } : r)));
      return;
    }
    const proceed = window.confirm(`找不到背號 ${typed} 的球員，確定要繼續嗎？`);
    setter((prev) =>
      prev.map((r, i) =>
        i === index
          ? proceed
            ? { ...r, line: { ...r.line, player_id: 0 } }
            : { ...r, numberText: "", line: { ...r.line, player_id: 0 } }
          : r,
      ),
    );
  }

  function handleAddBattingRow(team: "home" | "away") {
    const setter = team === "home" ? setHomeBatting : setAwayBatting;
    setter((prev) => [...prev, blankBattingRow()]);
  }

  function handlePitchingChange(
    team: "home" | "away",
    index: number,
    field: keyof PitchingLine,
    value: number | string | boolean,
  ) {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => prev.map((row, i) => (i === index ? { ...row, line: { ...row.line, [field]: value } } : row)));
  }

  function handlePitchingNumberChange(team: "home" | "away", index: number, value: string) {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => prev.map((row, i) => (i === index ? { ...row, numberText: value } : row)));
  }

  function handlePitchingNumberBlur(team: "home" | "away", index: number) {
    const data = initialDataQuery.data;
    if (!data) return;
    const roster = team === "home" ? data.homePlayers : data.awayPlayers;
    const rows = team === "home" ? homePitching : awayPitching;
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    const typed = rows[index].numberText.trim();

    if (typed === "") {
      setter((prev) => prev.map((r, i) => (i === index ? { ...r, line: { ...r.line, player_id: 0 } } : r)));
      return;
    }
    const match = resolvePlayerByNumber(roster, typed);
    if (match) {
      setter((prev) => prev.map((r, i) => (i === index ? { ...r, line: { ...r.line, player_id: match.id } } : r)));
      return;
    }
    const proceed = window.confirm(`找不到背號 ${typed} 的球員，確定要繼續嗎？`);
    setter((prev) =>
      prev.map((r, i) =>
        i === index
          ? proceed
            ? { ...r, line: { ...r.line, player_id: 0 } }
            : { ...r, numberText: "", line: { ...r.line, player_id: 0 } }
          : r,
      ),
    );
  }

  function handleAddPitcher(team: "home" | "away") {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => [...prev, { line: { ...blankPitchingLine(), seq: prev.length + 1 }, numberText: "" }]);
  }

  function handleRemovePitcher(team: "home" | "away", index: number) {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => prev.filter((_, i) => i !== index));
  }

  function handleLineScoreChange(
    side: "home" | "away",
    field: "runs" | "e" | "lob",
    value: number,
    inningIndex?: number,
  ) {
    setLineScore((prev) => {
      if (field === "runs" && inningIndex !== undefined) {
        const arr = [...(prev[side] ?? [])];
        arr[inningIndex] = value;
        return { ...prev, [side]: arr };
      }
      if (field === "e") return { ...prev, [`${side}_e`]: value };
      if (field === "lob") return { ...prev, [`${side}_lob`]: value };
      return prev;
    });
  }

  async function handleSave() {
    if (!initialDataQuery.data) return;
    const { game } = initialDataQuery.data;
    setSaving(true);
    setActionError(null);
    try {
      const homeLines = homeBatting.map((r) => r.line).filter((l) => l.player_id > 0 && l.pa > 0);
      const awayLines = awayBatting.map((r) => r.line).filter((l) => l.player_id > 0 && l.pa > 0);
      const homeP = homePitching.map((r) => r.line).filter((l) => l.player_id > 0);
      const awayP = awayPitching.map((r) => r.line).filter((l) => l.player_id > 0);

      await Promise.all([
        putBattingLines(game.id, game.home_team_id, homeLines),
        putBattingLines(game.id, game.away_team_id, awayLines),
        putPitchingLines(game.id, game.home_team_id, homeP),
        putPitchingLines(game.id, game.away_team_id, awayP),
        patchGameLineScore(game.id, lineScore),
      ]);
      setValidateResult(null);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    if (!initialDataQuery.data) return;
    setValidating(true);
    setActionError(null);
    try {
      setValidateResult(await validateGame(initialDataQuery.data.game.id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "驗證失敗");
    } finally {
      setValidating(false);
    }
  }

  async function handleFinalize() {
    if (!initialDataQuery.data) return;
    setFinalizing(true);
    setActionError(null);
    try {
      const { game } = initialDataQuery.data;
      await finalizeGame(game.id);
      navigate(`/games/${game.id}/boxscore`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "完賽失敗");
    } finally {
      setFinalizing(false);
    }
  }

  if (initialDataQuery.isLoading || !seeded) return <LoadingBlock />;
  if (initialDataQuery.isError || !initialDataQuery.data) {
    return <FormError message="無法載入比賽資料" />;
  }

  const { homeTeam, awayTeam, homePlayers, awayPlayers } = initialDataQuery.data;

  const homeBattingArr = homeBatting.map((r) => r.line);
  const awayBattingArr = awayBatting.map((r) => r.line);
  const awayPitchingOuts = awayPitching.reduce((s, r) => s + (r.line.outs || 0), 0);
  const homePitchingOuts = homePitching.reduce((s, r) => s + (r.line.outs || 0), 0);
  const homeCheck = computeRLobPo(homeBattingArr, lineScore.home_lob ?? 0, awayPitchingOuts);
  const awayCheck = computeRLobPo(awayBattingArr, lineScore.away_lob ?? 0, homePitchingOuts);

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight text-foreground">
        {awayTeam.name} @ {homeTeam.name} — 計分表
      </h1>

      <div className="mt-4">
        <LineScoreEntry
          innings={innings}
          awayName={awayTeam.name}
          homeName={homeTeam.name}
          awayRuns={lineScore.away}
          homeRuns={lineScore.home}
          awayE={lineScore.away_e ?? 0}
          homeE={lineScore.home_e ?? 0}
          awayLob={lineScore.away_lob ?? 0}
          homeLob={lineScore.home_lob ?? 0}
          onChange={handleLineScoreChange}
        />
      </div>

      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{awayTeam.name}（客隊）打擊</h2>
      <BattingGrid
        players={awayPlayers}
        rows={awayBatting}
        onChange={(i, field, value) => handleBattingChange("away", i, field, value)}
        onNumberChange={(i, v) => handleBattingNumberChange("away", i, v)}
        onNumberBlur={(i) => handleBattingNumberBlur("away", i)}
        onAddRow={() => handleAddBattingRow("away")}
      />
      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{awayTeam.name} 投手</h2>
      <PitchingGrid
        players={awayPlayers}
        rows={awayPitching}
        onChange={(i, field, value) => handlePitchingChange("away", i, field, value)}
        onNumberChange={(i, v) => handlePitchingNumberChange("away", i, v)}
        onNumberBlur={(i) => handlePitchingNumberBlur("away", i)}
        onAddPitcher={() => handleAddPitcher("away")}
        onRemovePitcher={(i) => handleRemovePitcher("away", i)}
      />

      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{homeTeam.name}（主隊）打擊</h2>
      <BattingGrid
        players={homePlayers}
        rows={homeBatting}
        onChange={(i, field, value) => handleBattingChange("home", i, field, value)}
        onNumberChange={(i, v) => handleBattingNumberChange("home", i, v)}
        onNumberBlur={(i) => handleBattingNumberBlur("home", i)}
        onAddRow={() => handleAddBattingRow("home")}
      />
      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{homeTeam.name} 投手</h2>
      <PitchingGrid
        players={homePlayers}
        rows={homePitching}
        onChange={(i, field, value) => handlePitchingChange("home", i, field, value)}
        onNumberChange={(i, v) => handlePitchingNumberChange("home", i, v)}
        onNumberBlur={(i) => handlePitchingNumberBlur("home", i)}
        onAddPitcher={() => handleAddPitcher("home")}
        onRemovePitcher={(i) => handleRemovePitcher("home", i)}
      />

      <Card className="mt-6">
        <CardContent className="grid gap-1 text-sm">
          <p className={awayCheck.ok ? "text-success" : "text-destructive"}>
            {awayCheck.ok ? "✓" : "✗"} {awayTeam.name} R+LOB+PO 檢查:R{awayCheck.r} + LOB{awayCheck.lob}{" "}
            + PO{awayCheck.po} {awayCheck.ok ? "=" : "≠"} PA{awayCheck.pa}
          </p>
          <p className={homeCheck.ok ? "text-success" : "text-destructive"}>
            {homeCheck.ok ? "✓" : "✗"} {homeTeam.name} R+LOB+PO 檢查:R{homeCheck.r} + LOB{homeCheck.lob}{" "}
            + PO{homeCheck.po} {homeCheck.ok ? "=" : "≠"} PA{homeCheck.pa}
          </p>
        </CardContent>
      </Card>

      <div className="mt-4 flex flex-wrap gap-3">
        <Button type="button" variant="outline" onClick={handleSave} disabled={saving}>
          {saving ? "儲存中…" : "儲存"}
        </Button>
        <Button type="button" variant="outline" onClick={handleValidate} disabled={validating}>
          {validating ? "驗證中…" : "伺服器驗證"}
        </Button>
        <Button type="button" onClick={handleFinalize} disabled={finalizing || !validateResult?.ok}>
          {finalizing ? "完賽中…" : "完賽"}
        </Button>
      </div>

      <FormError message={actionError} />

      {validateResult && (
        <ul className="mt-4 grid gap-1 text-sm">
          {validateResult.checks.map((c) => (
            <li key={c.name} className={cn(c.ok ? "text-success" : "text-destructive")}>
              {c.ok ? "✓" : "✗"} {c.name}:{c.detail}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
