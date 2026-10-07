"""Vulnerable fixture for CR4: Weak KDF parameters, static salt, or fast hash direct key derivation."""

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

STATIC_SALT = b"hardcoded_static_salt"


def derive_key_low_iterations(password: bytes) -> bytes:
    """Vulnerable PBKDF2 with static salt and low iteration count (1000 iterations)."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=STATIC_SALT,
        iterations=1000,
    )
    return kdf.derive(password)


def derive_key_hashlib_static_salt(password: str) -> bytes:
    """Vulnerable hashlib pbkdf2_hmac with static salt and low iteration count (5000 iterations)."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"fixed_salt", 5000)


def derive_key_fast_hash(password: str) -> bytes:
    """Vulnerable direct fast hash key derivation from password without KDF."""
    derived_key = hashlib.sha256(password.encode()).digest()
    return derived_key
