"""Excel roster import: parsing + row validation only (BUILD_SPEC §5).

Committing parsed rows to the database is the API layer's job
(app/api/roster_import.py), so this stays a pure, easily-testable function.
"""
import io
import re
from dataclasses import dataclass

import openpyxl

TEMPLATE_COLUMNS = ["number", "name", "positions", "bats_throws", "email", "phone", "birthdate"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_BATS_VALUES = {"R", "L", "S"}
_THROWS_VALUES = {"R", "L"}


@dataclass
class RosterRow:
    row: int
    number: int
    name: str
    positions: str | None
    bats: str | None
    throws: str | None


@dataclass
class RowError:
    row: int
    field: str
    msg: str


@dataclass
class ParseResult:
    valid_rows: list[RosterRow]
    errors: list[RowError]


def build_template_workbook() -> openpyxl.Workbook:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "roster"
    ws.append(TEMPLATE_COLUMNS)
    return wb


def _blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def parse_roster_workbook(content: bytes) -> ParseResult:
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb["roster"] if "roster" in wb.sheetnames else wb.active

    header_row = next(ws.iter_rows(min_row=1, max_row=1), ())
    header = [str(c.value).strip().lower() if c.value is not None else "" for c in header_row]
    col_index = {name: i for i, name in enumerate(header)}

    missing = [c for c in ("number", "name") if c not in col_index]
    if missing:
        return ParseResult(
            valid_rows=[],
            errors=[RowError(row=1, field=c, msg="missing required column") for c in missing],
        )

    def get(values: list, col: str) -> object:
        idx = col_index.get(col)
        if idx is None or idx >= len(values):
            return None
        return values[idx]

    valid_rows: list[RosterRow] = []
    errors: list[RowError] = []
    seen_numbers: dict[int, int] = {}

    for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        values = [cell.value for cell in row]
        if all(_blank(v) for v in values):
            continue

        row_ok = True

        raw_number = get(values, "number")
        number: int | None = None
        if _blank(raw_number):
            errors.append(RowError(row=row_idx, field="number", msg="required"))
            row_ok = False
        else:
            try:
                number = int(raw_number)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                errors.append(RowError(row=row_idx, field="number", msg="must be an integer"))
                row_ok = False
            else:
                if not (0 <= number <= 99):
                    errors.append(RowError(row=row_idx, field="number", msg="must be 0-99"))
                    row_ok = False

        raw_name = get(values, "name")
        name = str(raw_name).strip() if not _blank(raw_name) else ""
        if not name:
            errors.append(RowError(row=row_idx, field="name", msg="required"))
            row_ok = False

        raw_positions = get(values, "positions")
        positions = None if _blank(raw_positions) else str(raw_positions).strip()

        bats: str | None = None
        throws: str | None = None
        raw_bats_throws = get(values, "bats_throws")
        if not _blank(raw_bats_throws):
            parts = str(raw_bats_throws).strip().split("/")
            if len(parts) != 2:
                errors.append(
                    RowError(row=row_idx, field="bats_throws", msg="expected format 'B/T', e.g. 'R/R'"),
                )
                row_ok = False
            else:
                bats, throws = parts[0].strip().upper(), parts[1].strip().upper()
                if bats not in _BATS_VALUES:
                    errors.append(
                        RowError(row=row_idx, field="bats_throws", msg=f"bats must be one of {sorted(_BATS_VALUES)}"),
                    )
                    row_ok = False
                if throws not in _THROWS_VALUES:
                    errors.append(
                        RowError(row=row_idx, field="bats_throws", msg=f"throws must be one of {sorted(_THROWS_VALUES)}"),
                    )
                    row_ok = False

        raw_email = get(values, "email")
        if not _blank(raw_email) and not _EMAIL_RE.match(str(raw_email).strip()):
            errors.append(RowError(row=row_idx, field="email", msg="invalid email format"))
            row_ok = False

        # phone / birthdate: TODO(confirm) — the `players` table (BUILD_SPEC §3)
        # has no columns for these. Accepted here for validation per §5 but not
        # persisted; extend the schema if the league needs them stored.

        if number is not None:
            if number in seen_numbers:
                errors.append(
                    RowError(
                        row=row_idx, field="number",
                        msg=f"duplicate number in file (also row {seen_numbers[number]})",
                    ),
                )
                row_ok = False
            else:
                seen_numbers[number] = row_idx

        if row_ok:
            valid_rows.append(
                RosterRow(row=row_idx, number=number, name=name, positions=positions, bats=bats, throws=throws),  # type: ignore[arg-type]
            )

    return ParseResult(valid_rows=valid_rows, errors=errors)
