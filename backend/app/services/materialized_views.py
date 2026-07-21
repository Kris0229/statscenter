"""Refresh the leaderboard materialized views (§3.1).

Uses plain `REFRESH MATERIALIZED VIEW` (not CONCURRENTLY) so it can run as
part of the same transaction as /finalize — CONCURRENTLY refresh cannot run
inside a transaction block at all, and finalize's transactionality (§7 Phase
3 DoD: "partial failure rolls back") matters more here than avoiding a brief
exclusive lock on two small views for what BUILD_SPEC §0.4 calls "an internal
league tool, not high-scale SaaS." TODO(confirm): if this ever needs to move
off the request path (e.g. a busy league contending on the MVs), switch to a
background job using CONCURRENTLY — the unique indexes from the migration
already support it.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session


def refresh_leaderboard_views(db: Session) -> None:
    db.execute(text("REFRESH MATERIALIZED VIEW mv_batting_season"))
    db.execute(text("REFRESH MATERIALIZED VIEW mv_pitching_season"))
