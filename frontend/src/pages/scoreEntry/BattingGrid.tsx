import type { BattingLine, Player } from "../../api/types";
import { useGridNav } from "./gridNavigation";
import { hitsInconsistent, paBreakdownMismatch } from "./validation";

export interface BattingRow {
  line: BattingLine;
  numberText: string;
}

export function blankBattingLine(): BattingLine {
  return {
    player_id: 0, bat_order: null, sub_index: 0, pos: null,
    pa: 0, ab: 0, sh: 0, sf: 0, bb: 0, hp: 0, io: 0, tie: 0,
    r: 0, h: 0, b2: 0, b3: 0, hr: 0, rbi: 0, so: 0, sb: 0, cs: 0, gidp: 0, e: 0,
  };
}

export function blankBattingRow(): BattingRow {
  return { line: blankBattingLine(), numberText: "" };
}

interface ColDef {
  key: keyof BattingLine;
  label: string;
}

const RESULT_COLUMNS: ColDef[] = [
  { key: "r", label: "R" },
  { key: "h", label: "H" },
  { key: "b2", label: "2B" },
  { key: "b3", label: "3B" },
  { key: "hr", label: "HR" },
  { key: "rbi", label: "RBI" },
  { key: "so", label: "SO" },
  { key: "sb", label: "SB" },
  { key: "cs", label: "CS" },
  { key: "gidp", label: "GIDP" },
  { key: "e", label: "E" },
];

const PA_COLUMNS: ColDef[] = [
  { key: "pa", label: "PA" },
  { key: "ab", label: "AB" },
  { key: "sh", label: "SH" },
  { key: "sf", label: "SF" },
  { key: "bb", label: "BB" },
  { key: "hp", label: "HP" },
  { key: "io", label: "IO" },
  { key: "tie", label: "TIE" },
];

const STAT_COLUMNS: ColDef[] = [...RESULT_COLUMNS, ...PA_COLUMNS];

interface BattingGridProps {
  players: Player[];
  rows: BattingRow[];
  onChange: (index: number, field: keyof BattingLine, value: number | string | null) => void;
  onNumberChange: (index: number, value: string) => void;
  onNumberBlur: (index: number) => void;
  onAddRow: () => void;
}

export function BattingGrid({ players, rows, onChange, onNumberChange, onNumberBlur, onAddRow }: BattingGridProps) {
  const { registerCell, handleKeyDown } = useGridNav();

  return (
    <div>
      <table className="score-entry-table">
        <thead>
          <tr>
            <th rowSpan={2} className="name-cell">
              姓名
            </th>
            <th rowSpan={2}>打序</th>
            <th rowSpan={2}>背號</th>
            <th colSpan={RESULT_COLUMNS.length}>結果 (Results)</th>
            <th colSpan={PA_COLUMNS.length}>打席內容 (PA breakdown)</th>
          </tr>
          <tr>
            {STAT_COLUMNS.map((col) => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => {
            const { line } = row;
            const player = players.find((p) => p.id === line.player_id);
            const hasError = paBreakdownMismatch(line) || hitsInconsistent(line);
            return (
              <tr key={rowIndex} className={hasError ? "row-error" : undefined}>
                <td className="name-cell">{player?.name ?? ""}</td>
                <td>
                  <input
                    ref={registerCell(rowIndex, 0)}
                    type="number"
                    className="grid-cell"
                    value={line.bat_order ?? ""}
                    onChange={(e) =>
                      onChange(rowIndex, "bat_order", e.target.value === "" ? null : Number(e.target.value))
                    }
                    onKeyDown={handleKeyDown(rowIndex, 0)}
                  />
                </td>
                <td>
                  <input
                    ref={registerCell(rowIndex, 1)}
                    type="number"
                    className="grid-cell"
                    value={row.numberText}
                    onChange={(e) => onNumberChange(rowIndex, e.target.value)}
                    onBlur={() => onNumberBlur(rowIndex)}
                    onKeyDown={handleKeyDown(rowIndex, 1)}
                  />
                </td>
                {STAT_COLUMNS.map((col, i) => (
                  <td key={col.key}>
                    <input
                      ref={registerCell(rowIndex, i + 2)}
                      type="number"
                      className="grid-cell"
                      value={cellValue(line, col.key)}
                      onChange={(e) => onChange(rowIndex, col.key, e.target.value === "" ? 0 : Number(e.target.value))}
                      onKeyDown={handleKeyDown(rowIndex, i + 2)}
                    />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      <button type="button" onClick={onAddRow} className="text-sm text-primary hover:underline">
        + 新增打者
      </button>
    </div>
  );
}

function cellValue(line: BattingLine, key: keyof BattingLine): string | number {
  const v = line[key];
  return v === null || v === undefined ? "" : (v as string | number);
}
