from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test-tmp/app.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    cors_allowed_origins_raw: str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "bf_session")
    pre_csrf_cookie_name: str = os.getenv("PRE_CSRF_COOKIE_NAME", "bf_pre_csrf")
    cookie_secure: bool = _bool_env("COOKIE_SECURE", os.getenv("APP_ENV") == "production")
    auto_create_db: bool = _bool_env("AUTO_CREATE_DB", True)
    session_idle_seconds: int = _int_env("SESSION_IDLE_SECONDS", 1800)
    session_absolute_seconds: int = _int_env("SESSION_ABSOLUTE_SECONDS", 28800)
    csrf_nonce_seconds: int = _int_env("CSRF_NONCE_SECONDS", 600)
    login_rate_limit_attempts: int = _int_env("LOGIN_RATE_LIMIT_ATTEMPTS", 5)
    login_rate_limit_window_seconds: int = _int_env(
        "LOGIN_RATE_LIMIT_WINDOW_SECONDS",
        300,
    )
    artifact_storage_root: str = os.getenv("ARTIFACT_STORAGE_ROOT", "runtime-artifacts")
    max_upload_bytes: int = _int_env("MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
    max_zip_entries: int = _int_env("MAX_ZIP_ENTRIES", 1000)
    max_zip_path_length: int = _int_env("MAX_ZIP_PATH_LENGTH", 240)
    max_zip_uncompressed_bytes: int = _int_env("MAX_ZIP_UNCOMPRESSED_BYTES", 100 * 1024 * 1024)
    max_zip_compression_ratio: int = _int_env("MAX_ZIP_COMPRESSION_RATIO", 100)
    dev_seed_email: str = os.getenv("DEV_SEED_EMAIL", "admin@example.com")
    dev_seed_password: str | None = os.getenv("DEV_SEED_PASSWORD")

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins_raw.split(",")
            if origin.strip()
        ]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
