import type { PitchingLine, Player } from "../../api/types";
import { useGridNav } from "./gridNavigation";

export interface PitchingRowState {
  line: PitchingLine;
  numberText: string;
}

export function blankPitchingLine(): PitchingLine {
  return {
    player_id: 0, seq: 1, decision: "none", outs: 0, np: 0, bf: 0, ab: 0, h: 0, hr: 0,
    bb: 0, hp: 0, so: 0, r: 0, er: 0, wp: 0, gs: false, cg: false, sho: false, sv: false, svo: false,
  };
}

export function blankPitchingRow(): PitchingRowState {
  return { line: blankPitchingLine(), numberText: "" };
}

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
  rows: PitchingRowState[];
  onChange: (index: number, field: keyof PitchingLine, value: number | string | boolean) => void;
  onNumberChange: (index: number, value: string) => void;
  onNumberBlur: (index: number) => void;
  onAddPitcher: () => void;
  onRemovePitcher: (index: number) => void;
}

export function PitchingGrid({
  players, rows, onChange, onNumberChange, onNumberBlur, onAddPitcher, onRemovePitcher,
}: PitchingGridProps) {
  const { registerCell, handleKeyDown } = useGridNav();
  // numeric columns start after the 背號 input (col 0); the decision <select>
  // sits between them in DOM order but, like before, isn't part of arrow-key nav.
  const numericColOffset = 1;
  const flagColOffset = numericColOffset + NUMERIC_COLUMNS.length;

  return (
    <div>
      <table className="score-entry-table">
        <thead>
          <tr>
            <th className="name-cell">投手</th>
            <th>背號</th>
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
          {rows.map((row, rowIndex) => {
            const { line } = row;
            const player = players.find((p) => p.id === line.player_id);
            return (
              <tr key={rowIndex}>
                <td className="name-cell">{player?.name ?? ""}</td>
                <td>
                  <input
                    ref={registerCell(rowIndex, 0)}
                    type="number"
                    className="grid-cell"
                    value={row.numberText}
                    onChange={(e) => onNumberChange(rowIndex, e.target.value)}
                    onBlur={() => onNumberBlur(rowIndex)}
                    onKeyDown={handleKeyDown(rowIndex, 0)}
                  />
                </td>
                <td>
                  <select
                    value={line.decision}
                    onChange={(e) => onChange(rowIndex, "decision", e.target.value)}
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
                      ref={registerCell(rowIndex, numericColOffset + i)}
                      type="number"
                      className="grid-cell"
                      value={line[col.key] as number}
                      onChange={(e) => onChange(rowIndex, col.key, Number(e.target.value) || 0)}
                      onKeyDown={handleKeyDown(rowIndex, numericColOffset + i)}
                    />
                  </td>
                ))}
                {FLAG_COLUMNS.map((col, i) => (
                  <td key={col.key}>
                    <input
                      ref={registerCell(rowIndex, flagColOffset + i)}
                      type="checkbox"
                      checked={line[col.key] as boolean}
                      onChange={(e) => onChange(rowIndex, col.key, e.target.checked)}
                      onKeyDown={handleKeyDown(rowIndex, flagColOffset + i)}
                    />
                  </td>
                ))}
                <td>
                  <button
                    type="button"
                    onClick={() => onRemovePitcher(rowIndex)}
                    className="text-xs text-destructive hover:underline"
                  >
                    移除
                  </button>
                </td>
              </tr>
            );
          })}
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
