import type { PitchingLine, Player } from "../../api/types";
import { useGridNav } from "./gridNavigation";

interface NumCol {
  key: keyof PitchingLine;
  label: string;
}

const NUMERIC_COLUMNS: NumCol[] = [
  { key: "outs", label: "局數(outs)" },
  { key: "np", label: "NP" },
  { key: "bf", label: "BF" },
  { key: "ab", label: "AB" },
  { key: "h", label: "H" },
  { key: "hr", label: "HR" },
  { key: "bb", label: "BB" },
  { key: "hp", label: "HP" },
  { key: "so", label: "SO" },
  { key: "r", label: "R" },
  { key: "er", label: "ER" },
  { key: "wp", label: "WP" },
];

const FLAG_COLUMNS: NumCol[] = [
  { key: "gs", label: "GS" },
  { key: "cg", label: "CG" },
  { key: "sho", label: "SHO" },
  { key: "sv", label: "SV" },
  { key: "svo", label: "SVO" },
];

const DECISIONS = ["none", "W", "L", "SV", "BS", "HLD", "SVO"];

interface PitchingGridProps {
  players: Player[];
  lines: PitchingLine[];
  onChange: (index: number, field: keyof PitchingLine, value: number | string | boolean) => void;
  onAddPitcher: () => void;
  onRemovePitcher: (index: number) => void;
}

export function PitchingGrid({
  players, lines, onChange, onAddPitcher, onRemovePitcher,
}: PitchingGridProps) {
  const { registerCell, handleKeyDown } = useGridNav();
  // numeric columns start after the 2 select columns (player, decision)
  const numericColOffset = 2;
  const flagColOffset = numericColOffset + NUMERIC_COLUMNS.length;

  return (
    <div>
      <table className="score-entry-table">
        <thead>
          <tr>
            <th className="name-cell">投手</th>
            <th>勝敗</th>
            {NUMERIC_COLUMNS.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
            {FLAG_COLUMNS.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, row) => (
            <tr key={row}>
              <td className="name-cell">
                <select
                  value={line.player_id || ""}
                  onChange={(e) => onChange(row, "player_id", Number(e.target.value))}
                >
                  <option value="">選擇投手</option>
                  {players.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.number} {p.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={line.decision}
                  onChange={(e) => onChange(row, "decision", e.target.value)}
                >
                  {DECISIONS.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </td>
              {NUMERIC_COLUMNS.map((col, i) => (
                <td key={col.key}>
                  <input
                    ref={registerCell(row, numericColOffset + i)}
                    type="number"
                    className="grid-cell"
                    value={line[col.key] as number}
                    onChange={(e) => onChange(row, col.key, Number(e.target.value) || 0)}
                    onKeyDown={handleKeyDown(row, numericColOffset + i)}
                  />
                </td>
              ))}
              {FLAG_COLUMNS.map((col, i) => (
                <td key={col.key}>
                  <input
                    ref={registerCell(row, flagColOffset + i)}
                    type="checkbox"
                    checked={line[col.key] as boolean}
                    onChange={(e) => onChange(row, col.key, e.target.checked)}
                    onKeyDown={handleKeyDown(row, flagColOffset + i)}
                  />
                </td>
              ))}
              <td>
                <button
                  type="button"
                  onClick={() => onRemovePitcher(row)}
                  className="text-xs text-destructive hover:underline"
                >
                  移除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        type="button"
        onClick={onAddPitcher}
        className="text-sm text-primary hover:underline"
      >
        + 新增投手
      </button>
    </div>
  );
}
