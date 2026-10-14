"""Password hashing for the app's username/password login (standard library only).

Stored format: ``pbkdf2_sha256$<iterations>$<salt b64>$<hash b64>``. Plain passwords are never stored;
generate hashes with ``python -m p6toolkit hash-password``.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import secrets
from collections.abc import Mapping
from functools import lru_cache

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 600_000      # OWASP 2023 recommendation for PBKDF2-HMAC-SHA256


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check. Malformed hashes return False instead of raising."""
    try:
        algorithm, iterations, salt_b64, hash_b64 = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(hash_b64, validate=True)
        digest = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(digest, expected)


def normalize_users(users) -> dict[str, dict]:
    """Accept any mapping (e.g. st.secrets sections); usernames are case-insensitive."""
    if not isinstance(users, Mapping):
        return {}
    return {str(k).strip().lower(): dict(v) for k, v in users.items() if isinstance(v, Mapping)}


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password("not-a-real-password", salt=b"\0" * 16)


def authenticate(users, username: str, password: str) -> dict | None:
    """Return the user record if credentials match. Unknown users still pay the hashing cost."""
    table = normalize_users(users)
    name = (username or "").strip().lower()
    record = table.get(name)
    ok = verify_password(password, (record or {}).get("password") or _dummy_hash())
    if not (ok and record) or record.get("disabled"):
        return None
    return {"username": name, "name": record.get("name") or name}
