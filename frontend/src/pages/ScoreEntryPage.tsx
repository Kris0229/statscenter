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
import { BattingGrid } from "./scoreEntry/BattingGrid";
import { LineScoreEntry } from "./scoreEntry/LineScoreEntry";
import { PitchingGrid } from "./scoreEntry/PitchingGrid";
import "./scoreEntry/ScoreEntryPage.css";
import { computeRLobPo } from "./scoreEntry/validation";

function blankBattingLine(playerId: number, batOrder: number): BattingLine {
  return {
    player_id: playerId, bat_order: batOrder, sub_index: 0, pos: "",
    pa: 0, ab: 0, sh: 0, sf: 0, bb: 0, hp: 0, io: 0, tie: 0,
    r: 0, h: 0, b2: 0, b3: 0, hr: 0, rbi: 0, so: 0, sb: 0, cs: 0, gidp: 0, e: 0,
  };
}

function blankPitchingLine(): PitchingLine {
  return {
    player_id: 0, seq: 1, decision: "none", outs: 0, np: 0, bf: 0, ab: 0, h: 0, hr: 0,
    bb: 0, hp: 0, so: 0, r: 0, er: 0, wp: 0, gs: false, cg: false, sho: false, sv: false, svo: false,
  };
}

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
  const [homeBatting, setHomeBatting] = useState<Map<number, BattingLine>>(new Map());
  const [awayBatting, setAwayBatting] = useState<Map<number, BattingLine>>(new Map());
  const [homePitching, setHomePitching] = useState<PitchingLine[]>([]);
  const [awayPitching, setAwayPitching] = useState<PitchingLine[]>([]);
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

    const seedTeam = (players: typeof homePlayers) => {
      const m = new Map<number, BattingLine>();
      players.forEach((p, i) => {
        const existing = battingLines.find((l) => l.player_id === p.id);
        m.set(p.id, existing ?? blankBattingLine(p.id, i + 1));
      });
      return m;
    };
    setHomeBatting(seedTeam(homePlayers));
    setAwayBatting(seedTeam(awayPlayers));

    const homeIds = new Set(homePlayers.map((p) => p.id));
    const awayIds = new Set(awayPlayers.map((p) => p.id));
    const homeP = pitchingLines.filter((l) => homeIds.has(l.player_id));
    const awayP = pitchingLines.filter((l) => awayIds.has(l.player_id));
    setHomePitching(homeP.length > 0 ? homeP : [blankPitchingLine()]);
    setAwayPitching(awayP.length > 0 ? awayP : [blankPitchingLine()]);

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
    playerId: number,
    field: keyof BattingLine,
    value: number | string | null,
  ) {
    const setter = team === "home" ? setHomeBatting : setAwayBatting;
    setter((prev) => {
      const line = prev.get(playerId);
      if (!line) return prev;
      const next = new Map(prev);
      next.set(playerId, { ...line, [field]: value });
      return next;
    });
  }

  function handlePitchingChange(
    team: "home" | "away",
    index: number,
    field: keyof PitchingLine,
    value: number | string | boolean,
  ) {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => prev.map((line, i) => (i === index ? { ...line, [field]: value } : line)));
  }

  function handleAddPitcher(team: "home" | "away") {
    const setter = team === "home" ? setHomePitching : setAwayPitching;
    setter((prev) => [...prev, { ...blankPitchingLine(), seq: prev.length + 1 }]);
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
      const homeLines = [...homeBatting.values()].filter((l) => l.pa > 0);
      const awayLines = [...awayBatting.values()].filter((l) => l.pa > 0);
      const homeP = homePitching.filter((l) => l.player_id);
      const awayP = awayPitching.filter((l) => l.player_id);

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

  const homeBattingArr = [...homeBatting.values()];
  const awayBattingArr = [...awayBatting.values()];
  const awayPitchingOuts = awayPitching.reduce((s, l) => s + (l.outs || 0), 0);
  const homePitchingOuts = homePitching.reduce((s, l) => s + (l.outs || 0), 0);
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
        lines={awayBatting}
        onChange={(id, field, value) => handleBattingChange("away", id, field, value)}
      />
      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{awayTeam.name} 投手</h2>
      <PitchingGrid
        players={awayPlayers}
        lines={awayPitching}
        onChange={(i, field, value) => handlePitchingChange("away", i, field, value)}
        onAddPitcher={() => handleAddPitcher("away")}
        onRemovePitcher={(i) => handleRemovePitcher("away", i)}
      />

      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{homeTeam.name}（主隊）打擊</h2>
      <BattingGrid
        players={homePlayers}
        lines={homeBatting}
        onChange={(id, field, value) => handleBattingChange("home", id, field, value)}
      />
      <h2 className="mt-6 mb-2 text-lg font-semibold text-foreground">{homeTeam.name} 投手</h2>
      <PitchingGrid
        players={homePlayers}
        lines={homePitching}
        onChange={(i, field, value) => handlePitchingChange("home", i, field, value)}
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
