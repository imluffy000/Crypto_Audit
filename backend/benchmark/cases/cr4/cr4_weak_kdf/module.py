"""Password hashing for the internal admin console."""

import hashlib
import hmac

SALT = b"admin-console-salt"
ITERATIONS = 1000


def hash_password(password: str) -> str:
    """Return the stored representation of a password."""
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), SALT, ITERATIONS)
    return digest.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a login attempt against a stored password hash."""
    return hmac.compare_digest(hash_password(password), stored_hash)
