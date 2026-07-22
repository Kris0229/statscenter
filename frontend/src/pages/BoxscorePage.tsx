import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchBoxscore } from "../api/client";
import type { Boxscore, BoxscoreBattingNotes, BoxscoreTeamSide } from "../api/types";
import "./BoxscorePage.css";

export function BoxscorePage() {
  const params = useParams<{ gameId: string }>();
  const gameId = Number(params.gameId);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["boxscore", gameId],
    queryFn: () => fetchBoxscore(gameId),
    enabled: Number.isFinite(gameId),
  });

  if (isLoading) return <p>載入中…</p>;
  if (isError || !data) return <p style={{ color: "crimson" }}>無法載入比賽紀錄表</p>;

  return <BoxscoreView boxscore={data} />;
}

function BoxscoreView({ boxscore }: { boxscore: Boxscore }) {
  return (
    <div>
      <div className="no-print" style={{ marginBottom: "1rem" }}>
        <button type="button" onClick={() => window.print()}>
          列印
        </button>
      </div>

      <h1>
        {boxscore.away.team.name} @ {boxscore.home.team.name}
      </h1>
      <p>
        {boxscore.game.date}
        {boxscore.game.venue && <> · {boxscore.game.venue}</>}
        {boxscore.game.code && <> · {boxscore.game.code}</>} · {statusLabel(boxscore.game.status)}
      </p>

      <LineScoreTable boxscore={boxscore} />

      <h2 className="boxscore-team-heading">{boxscore.away.team.name}(客隊)</h2>
      <BattingTable side={boxscore.away} />
      <BattingNotesView notes={boxscore.away.batting_notes} />
      <PitchingTable side={boxscore.away} />

      <h2 className="boxscore-team-heading">{boxscore.home.team.name}(主隊)</h2>
      <BattingTable side={boxscore.home} />
      <BattingNotesView notes={boxscore.home.batting_notes} />
      <PitchingTable side={boxscore.home} />
    </div>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    scheduled: "未開賽",
    in_progress: "進行中",
    final: "已完賽",
    postponed: "延賽",
    cancelled: "取消",
  };
  return labels[status] ?? status;
}

function LineScoreTable({ boxscore }: { boxscore: Boxscore }) {
  const innings = Math.max(boxscore.line_score.home.length, boxscore.line_score.away.length);
  const inningNumbers = Array.from({ length: innings }, (_, i) => i + 1);

  return (
    <table className="boxscore-table">
      <thead>
        <tr>
          <th className="name-cell">隊伍</th>
          {inningNumbers.map((n) => (
            <th key={n}>{n}</th>
          ))}
          <th>R</th>
          <th>H</th>
          <th>E</th>
        </tr>
      </thead>
      <tbody>
        <LineScoreRow
          name={boxscore.away.team.name}
          innings={boxscore.line_score.away}
          totals={boxscore.line_score.away_totals}
          totalInnings={innings}
        />
        <LineScoreRow
          name={boxscore.home.team.name}
          innings={boxscore.line_score.home}
          totals={boxscore.line_score.home_totals}
          totalInnings={innings}
        />
      </tbody>
    </table>
  );
}

function LineScoreRow({
  name,
  innings,
  totals,
  totalInnings,
}: {
  name: string;
  innings: number[];
  totals: { r: number; h: number; e: number };
  totalInnings: number;
}) {
  return (
    <tr>
      <td className="name-cell">{name}</td>
      {Array.from({ length: totalInnings }, (_, i) => (
        <td key={i}>{innings[i] ?? ""}</td>
      ))}
      <td>
        <strong>{totals.r}</strong>
      </td>
      <td>{totals.h}</td>
      <td>{totals.e}</td>
    </tr>
  );
}

function BattingTable({ side }: { side: BoxscoreTeamSide }) {
  return (
    <table className="boxscore-table">
      <thead>
        <tr>
          <th>打序</th>
          <th className="name-cell">姓名</th>
          <th>守位</th>
          <th>AB</th>
          <th>R</th>
          <th>H</th>
          <th>RBI</th>
          <th>BB</th>
          <th>SO</th>
          <th>AVG</th>
        </tr>
      </thead>
      <tbody>
        {side.batting.map((row) => (
          <tr key={`${row.player_id}-${row.sub}`}>
            <td>{row.sub > 0 ? `${row.order ?? ""}-${row.sub}` : row.order ?? ""}</td>
            <td className="name-cell">{row.name}</td>
            <td>{row.pos ?? ""}</td>
            <td>{row.ab}</td>
            <td>{row.r}</td>
            <td>{row.h}</td>
            <td>{row.rbi}</td>
            <td>{row.bb}</td>
            <td>{row.so}</td>
            <td>{row.avg}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function BattingNotesView({ notes }: { notes: BoxscoreBattingNotes }) {
  const lines: string[] = [];
  if (notes["2B"].length > 0) lines.push(`2B:${notes["2B"].join(", ")}`);
  if (notes["3B"].length > 0) lines.push(`3B:${notes["3B"].join(", ")}`);
  if (notes.HR.length > 0) lines.push(`HR:${notes.HR.join(", ")}`);
  if (notes.SB.length > 0) lines.push(`SB:${notes.SB.join(", ")}`);
  if (notes.LOB !== null) lines.push(`LOB:${notes.LOB}`);

  if (lines.length === 0) return null;
  return (
    <div className="boxscore-notes">
      {lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
}

function PitchingTable({ side }: { side: BoxscoreTeamSide }) {
  if (side.pitching.length === 0) return null;
  return (
    <table className="boxscore-table">
      <thead>
        <tr>
          <th className="name-cell">投手</th>
          <th>IP</th>
          <th>H</th>
          <th>R</th>
          <th>ER</th>
          <th>BB</th>
          <th>SO</th>
          <th>HR</th>
          <th>ERA</th>
          <th>勝敗</th>
        </tr>
      </thead>
      <tbody>
        {side.pitching.map((row) => (
          <tr key={row.player_id}>
            <td className="name-cell">{row.name}</td>
            <td>{row.ip}</td>
            <td>{row.h}</td>
            <td>{row.r}</td>
            <td>{row.er}</td>
            <td>{row.bb}</td>
            <td>{row.so}</td>
            <td>{row.hr}</td>
            <td>{row.era}</td>
            <td>{row.decision ?? ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
