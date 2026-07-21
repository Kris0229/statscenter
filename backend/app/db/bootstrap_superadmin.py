"""One-off bootstrap for the initial super_admin account.

Run via `python -m app.db.bootstrap_superadmin`. Credentials come from
SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD (env or .env) — never via API,
per BUILD_SPEC §6.0. Idempotent: no-op if a super_admin with that email
already exists.
"""
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import User


def bootstrap_superadmin() -> User:
    settings = get_settings()
    if not settings.SUPERADMIN_EMAIL or not settings.SUPERADMIN_PASSWORD:
        raise SystemExit(
            "SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must be set (env or .env)",
        )

    db = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter(User.email == settings.SUPERADMIN_EMAIL)
            .one_or_none()
        )
        if existing is not None:
            print(f"super_admin already exists: {existing.email}")
            return existing

        user = User(
            league_id=None,
            email=settings.SUPERADMIN_EMAIL,
            password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
            display_name="System Admin",
            role="super_admin",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"created super_admin: {user.email}")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap_superadmin()
