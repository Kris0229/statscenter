import type { BattingLine, Player } from "../../api/types";
import { useGridNav } from "./gridNavigation";
import { hitsInconsistent, paBreakdownMismatch } from "./validation";

interface ColDef {
  key: keyof BattingLine;
  label: string;
  type: "number" | "text";
  group?: "pa" | "results";
}

const COLUMNS: ColDef[] = [
  { key: "bat_order", label: "打序", type: "number" },
  { key: "pos", label: "守位", type: "text" },
  { key: "pa", label: "PA", type: "number", group: "pa" },
  { key: "ab", label: "AB", type: "number", group: "pa" },
  { key: "sh", label: "SH", type: "number", group: "pa" },
  { key: "sf", label: "SF", type: "number", group: "pa" },
  { key: "bb", label: "BB", type: "number", group: "pa" },
  { key: "hp", label: "HP", type: "number", group: "pa" },
  { key: "io", label: "IO", type: "number", group: "pa" },
  { key: "tie", label: "TIE", type: "number", group: "pa" },
  { key: "r", label: "R", type: "number", group: "results" },
  { key: "h", label: "H", type: "number", group: "results" },
  { key: "b2", label: "2B", type: "number", group: "results" },
  { key: "b3", label: "3B", type: "number", group: "results" },
  { key: "hr", label: "HR", type: "number", group: "results" },
  { key: "rbi", label: "RBI", type: "number", group: "results" },
  { key: "so", label: "SO", type: "number", group: "results" },
  { key: "sb", label: "SB", type: "number", group: "results" },
  { key: "cs", label: "CS", type: "number", group: "results" },
  { key: "gidp", label: "GIDP", type: "number", group: "results" },
  { key: "e", label: "E", type: "number", group: "results" },
];

interface BattingGridProps {
  players: Player[];
  lines: Map<number, BattingLine>;
  onChange: (playerId: number, field: keyof BattingLine, value: number | string | null) => void;
}

export function BattingGrid({ players, lines, onChange }: BattingGridProps) {
  const { registerCell, handleKeyDown } = useGridNav();

  return (
    <table className="score-entry-table">
      <thead>
        <tr>
          <th rowSpan={2}>打序</th>
          <th rowSpan={2} className="name-cell">
            姓名
          </th>
          <th rowSpan={2}>守位</th>
          <th colSpan={8}>打席內容 (PA breakdown)</th>
          <th colSpan={11}>結果 (Results)</th>
        </tr>
        <tr>
          {COLUMNS.slice(2).map((col) => (
            <th key={col.key}>{col.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {players.map((player, row) => {
          const line = lines.get(player.id);
          if (!line) return null;
          const hasError = paBreakdownMismatch(line) || hitsInconsistent(line);
          return (
            <tr key={player.id} className={hasError ? "row-error" : undefined}>
              <td className="name-cell">
                {player.number} {player.name}
              </td>
              {COLUMNS.map((col, colIndex) => (
                <td key={col.key}>
                  <input
                    ref={registerCell(row, colIndex)}
                    type={col.type === "number" ? "number" : "text"}
                    className="grid-cell"
                    value={cellValue(line, col.key)}
                    onChange={(e) =>
                      onChange(
                        player.id,
                        col.key,
                        col.type === "number"
                          ? e.target.value === ""
                            ? (col.key === "bat_order" ? null : 0)
                            : Number(e.target.value)
                          : e.target.value,
                      )
                    }
                    onKeyDown={handleKeyDown(row, colIndex)}
                  />
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function cellValue(line: BattingLine, key: keyof BattingLine): string | number {
  const v = line[key];
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "1" : "0";
  return v;
}
