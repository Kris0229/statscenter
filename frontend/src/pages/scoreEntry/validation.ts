import type { BattingLine } from "../../api/types";

/** Mirrors the server's §4.1 pa-breakdown check, for live row highlighting. */
export function paBreakdownMismatch(line: BattingLine): boolean {
  return line.pa !== line.ab + line.sh + line.sf + line.bb + line.hp + line.io + line.tie;
}

/** Mirrors the server's §4.1 h >= 2b+3b+hr check. */
export function hitsInconsistent(line: BattingLine): boolean {
  return line.h < line.b2 + line.b3 + line.hr;
}

export function rowHasError(line: BattingLine): boolean {
  return paBreakdownMismatch(line) || hitsInconsistent(line);
}

export interface RLobPoResult {
  ok: boolean;
  r: number;
  lob: number;
  po: number;
  pa: number;
}

/** Σr + LOB + PO == Σpa (§4.1 RTBA cross-check). PO is the outs the
 * *opposing* team's pitchers recorded against these batters. */
export function computeRLobPo(
  battingLines: BattingLine[],
  lob: number,
  opposingPitchingOuts: number,
): RLobPoResult {
  const r = battingLines.reduce((sum, l) => sum + l.r, 0);
  const pa = battingLines.reduce((sum, l) => sum + l.pa, 0);
  return { ok: r + lob + opposingPitchingOuts === pa, r, lob, po: opposingPitchingOuts, pa };
}
