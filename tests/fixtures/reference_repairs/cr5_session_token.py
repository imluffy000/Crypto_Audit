"""Reference repair (tests only): CSPRNG-backed session tokens."""

import secrets
import string

ALPHABET = string.ascii_letters + string.digits


def generate_session_token(length: int = 32) -> str:
    """Return a new random session token."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
