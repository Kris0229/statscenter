"""player roster fields — title/birthdate/national_id/email/phone

Revision ID: 20260723_0003
Revises: 20260722_0002
Create Date: 2026-07-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0003"
down_revision: Union[str, None] = "20260722_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_PLAYER_TITLE_VALUES = ("manager", "coach", "captain", "member")


def _player_title_enum(create_type: bool) -> postgresql.ENUM:
    return postgresql.ENUM(*_PLAYER_TITLE_VALUES, name="player_title", create_type=create_type)


def upgrade() -> None:
    conn = op.get_bind()
    _player_title_enum(create_type=True).create(conn, checkfirst=True)

    op.add_column(
        "players",
        sa.Column(
            "title", _player_title_enum(create_type=False),
            nullable=False, server_default="member",
        ),
    )
    op.add_column("players", sa.Column("birthdate", sa.Date(), nullable=True))
    op.add_column("players", sa.Column("national_id", sa.Text(), nullable=True))
    op.add_column("players", sa.Column("email", sa.Text(), nullable=True))
    op.add_column("players", sa.Column("phone", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    op.drop_column("players", "phone")
    op.drop_column("players", "email")
    op.drop_column("players", "national_id")
    op.drop_column("players", "birthdate")
    op.drop_column("players", "title")
    _player_title_enum(create_type=False).drop(conn, checkfirst=True)
