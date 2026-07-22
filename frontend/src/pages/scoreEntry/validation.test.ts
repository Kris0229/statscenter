import { describe, expect, it } from "vitest";

import type { BattingLine } from "../../api/types";
import { computeRLobPo, hitsInconsistent, paBreakdownMismatch, rowHasError } from "./validation";

function makeLine(overrides: Partial<BattingLine> = {}): BattingLine {
  return {
    player_id: 1, bat_order: 1, sub_index: 0, pos: "OF",
    pa: 4, ab: 4, sh: 0, sf: 0, bb: 0, hp: 0, io: 0, tie: 0,
    r: 0, h: 0, b2: 0, b3: 0, hr: 0, rbi: 0, so: 0, sb: 0, cs: 0, gidp: 0, e: 0,
    ...overrides,
  };
}

describe("paBreakdownMismatch", () => {
  it("is false when pa equals the sum of its components", () => {
    expect(paBreakdownMismatch(makeLine({ pa: 5, ab: 3, bb: 1, hp: 1 }))).toBe(false);
  });

  it("is true when pa doesn't match", () => {
    expect(paBreakdownMismatch(makeLine({ pa: 4, ab: 4, bb: 1 }))).toBe(true);
  });
});

describe("hitsInconsistent", () => {
  it("is false when h >= 2b+3b+hr", () => {
    expect(hitsInconsistent(makeLine({ h: 2, b2: 1, hr: 1 }))).toBe(false);
  });

  it("is true when h < 2b+3b+hr", () => {
    expect(hitsInconsistent(makeLine({ h: 1, b2: 1, hr: 1 }))).toBe(true);
  });
});

describe("rowHasError", () => {
  it("flags a row with either kind of error", () => {
    expect(rowHasError(makeLine())).toBe(false);
    expect(rowHasError(makeLine({ pa: 5, ab: 4 }))).toBe(true);
    expect(rowHasError(makeLine({ h: 0, hr: 1 }))).toBe(true);
  });
});

describe("computeRLobPo", () => {
  it("matches when r+lob+po equals total pa", () => {
    const lines = [makeLine({ pa: 4, r: 1 }), makeLine({ pa: 4, r: 0 })];
    // pa total = 8; r total = 1; lob=3, po=4 -> 1+3+4=8
    const result = computeRLobPo(lines, 3, 4);
    expect(result.ok).toBe(true);
    expect(result.pa).toBe(8);
    expect(result.r).toBe(1);
  });

  it("flags a mismatch", () => {
    const lines = [makeLine({ pa: 4, r: 1 })];
    const result = computeRLobPo(lines, 0, 0);
    expect(result.ok).toBe(false);
  });
});
