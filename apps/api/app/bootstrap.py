from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.config import Settings
from apps.api.app.models import User
from apps.api.app.security import hash_password


def seed_development_user(db: Session, settings: Settings) -> None:
    if not settings.is_development:
        return
    if not settings.dev_seed_password:
        raise RuntimeError(
            "DEV_SEED_PASSWORD is required when APP_ENV=development so the seed user is not hardcoded."
        )

    email = settings.dev_seed_email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return

    db.add(
        User(
            email=email,
            password_hash=hash_password(settings.dev_seed_password),
            role="admin",
        )
    )
    db.commit()

