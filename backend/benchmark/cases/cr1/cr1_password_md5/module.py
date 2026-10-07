"""Account credential storage for a small web application."""

import hashlib


def hash_password(password: str) -> str:
    """Return the stored representation of a password."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a login attempt against a stored password hash."""
    return hash_password(password) == stored_hash
