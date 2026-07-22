import { useCallback, useRef } from "react";
import type { KeyboardEvent } from "react";

/**
 * Spreadsheet-style keyboard navigation for a grid of inputs, addressed by
 * (row, col). Tab/Shift+Tab need no help here — they already follow DOM
 * order, which matches the grid's visual layout. Arrow keys don't move
 * focus by default in a text input, so this fills that in; Enter also
 * drops down a row (RTBA sheets are filled top-to-bottom per column).
 */
export function useGridNav() {
  const cells = useRef(new Map<string, HTMLElement>());

  const cellKey = (row: number, col: number) => `${row}:${col}`;

  const registerCell = useCallback(
    (row: number, col: number) => (el: HTMLElement | null) => {
      const k = cellKey(row, col);
      if (el) {
        cells.current.set(k, el);
      } else {
        cells.current.delete(k);
      }
    },
    [],
  );

  const focusCell = useCallback((row: number, col: number) => {
    const el = cells.current.get(cellKey(row, col));
    if (!el) return;
    el.focus();
    if (el instanceof HTMLInputElement && el.type !== "checkbox") {
      el.select();
    }
  }, []);

  const handleKeyDown = useCallback(
    (row: number, col: number) => (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowUp":
          e.preventDefault();
          focusCell(row - 1, col);
          break;
        case "ArrowDown":
        case "Enter":
          e.preventDefault();
          focusCell(row + 1, col);
          break;
        case "ArrowLeft":
          e.preventDefault();
          focusCell(row, col - 1);
          break;
        case "ArrowRight":
          e.preventDefault();
          focusCell(row, col + 1);
          break;
        default:
          break;
      }
    },
    [focusCell],
  );

  return { registerCell, handleKeyDown };
}
