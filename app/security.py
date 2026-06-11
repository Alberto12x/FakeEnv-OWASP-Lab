"""Password hashing utilities.

WARNING — INTENTIONALLY INSECURE.
This module implements MD5 hashing with a single, static, application-wide salt
on purpose, as part of an educational OWASP project (TFM). It demonstrates
OWASP A02:2021 - Cryptographic Failures. Never reuse this in production code;
use a memory-hard algorithm such as Argon2, scrypt or bcrypt instead.
"""

import hashlib

from flask import current_app


def hash_password(password: str) -> str:
    """Return the MD5 hex digest of (global_salt + password)."""
    salt = current_app.config["PASSWORD_SALT"]
    return hashlib.md5(f"{salt}{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a plaintext password against a stored MD5 hash."""
    return hash_password(password) == stored_hash
