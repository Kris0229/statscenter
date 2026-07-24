import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, createGame, fetchSeasons, fetchTeams } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { FormField } from "@/components/FormField";
import { FormError } from "@/components/FormStatus";
import { LoadingBlock } from "@/components/Loading";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

  if (seasonsQuery.isLoading || teamsQuery.isLoading) return <LoadingBlock />;

  return (
    <div className="max-w-lg">
      <PageHeader
        title="新增比賽"
        description={currentSeason ? `球季：${currentSeason.name}（${currentSeason.year}）` : undefined}
      />
      <Card>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4">
            <FormField label="日期" htmlFor="game-date" required>
              <Input
                id="game-date"
                type="date"
                value={gameDate}
                onChange={(e) => setGameDate(e.target.value)}
                required
              />
            </FormField>
            <FormField label="客隊" htmlFor="away-team" required>
              <Select
                value={awayTeamId ? String(awayTeamId) : ""}
                onValueChange={(v) => setAwayTeamId(v ? Number(v) : "")}
              >
                <SelectTrigger id="away-team" className="w-full">
                  <SelectValue placeholder="請選擇" />
                </SelectTrigger>
                <SelectContent>
                  {teamsQuery.data?.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="主隊" htmlFor="home-team" required>
              <Select
                value={homeTeamId ? String(homeTeamId) : ""}
                onValueChange={(v) => setHomeTeamId(v ? Number(v) : "")}
              >
                <SelectTrigger id="home-team" className="w-full">
                  <SelectValue placeholder="請選擇" />
                </SelectTrigger>
                <SelectContent>
                  {teamsQuery.data?.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="場地" htmlFor="venue">
              <Input id="venue" value={venue} onChange={(e) => setVenue(e.target.value)} />
            </FormField>
            <FormField label="賽事代碼" htmlFor="code">
              <Input id="code" value={code} onChange={(e) => setCode(e.target.value)} />
            </FormField>
            <FormError message={error} />
            <Button type="submit" disabled={submitting || !currentSeason}>
              {submitting ? "建立中…" : "建立比賽並開始計分"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
