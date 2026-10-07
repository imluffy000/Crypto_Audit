"""Session token generation for authenticated users."""

import random
import string

ALPHABET = string.ascii_letters + string.digits


def generate_session_token(length: int = 32) -> str:
    """Return a new random session token."""
    return "".join(random.choice(ALPHABET) for _ in range(length))
