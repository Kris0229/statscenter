"""PostgreSQL ENUM type declarations shared across models.

`create_type=False` here — the migration creates and drops each type explicitly
so we can order it before/after the table DDL.
"""
from sqlalchemy.dialects.postgresql import ENUM

entity_status_enum = ENUM(
    "active", "inactive", name="entity_status", create_type=False,
)
user_role_enum = ENUM(
    "super_admin", "admin", "power", "user", name="user_role", create_type=False,
)
player_status_enum = ENUM(
    "active", "left", name="player_status", create_type=False,
)
player_title_enum = ENUM(
    "manager", "coach", "captain", "member", name="player_title", create_type=False,
)
roster_req_type_enum = ENUM(
    "rename", "renumber", "add", "remove", name="roster_req_type", create_type=False,
)
roster_req_status_enum = ENUM(
    "pending", "approved", "rejected", name="roster_req_status", create_type=False,
)
game_status_enum = ENUM(
    "scheduled", "in_progress", "final", "postponed", "cancelled",
    name="game_status", create_type=False,
)
pitch_decision_enum = ENUM(
    "W", "L", "SV", "BS", "HLD", "SVO", "none",
    name="pitch_decision", create_type=False,
)
media_type_enum = ENUM(
    "photo", "video", "link", name="media_type", create_type=False,
)

ALL_ENUMS = (
    entity_status_enum,
    user_role_enum,
    player_status_enum,
    roster_req_type_enum,
    roster_req_status_enum,
    game_status_enum,
    pitch_decision_enum,
    media_type_enum,
)
