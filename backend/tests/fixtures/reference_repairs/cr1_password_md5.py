"""Reference repair (tests only): salted PBKDF2 for new hashes, MD5 kept for legacy reads."""

import hashlib
import hmac
import os

_SCHEME = "pbkdf2_sha256"
_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """Return the stored representation of a password."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_SCHEME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Check a login attempt against a stored password hash."""
    if stored_hash.startswith(_SCHEME + "$"):
        _, iterations, salt_hex, digest_hex = stored_hash.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), digest_hex)
    legacy = hashlib.md5(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)
