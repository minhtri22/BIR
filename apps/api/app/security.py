from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compare_hash(raw_value: str, expected_hash: str) -> bool:
    return secrets.compare_digest(sha256_text(raw_value), expected_hash)


def account_identifier_hash(identifier: str) -> str:
    return sha256_text(identifier.strip().lower())

