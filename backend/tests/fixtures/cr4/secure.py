"""Secure fixture for CR4: Dynamic salt and strong PBKDF2 iterations (600,000)."""

import hashlib
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key_secure_hashlib(password: str) -> bytes:
    """Secure hashlib pbkdf2_hmac with dynamic os.urandom salt and 600,000 iterations."""
    salt = os.urandom(16)
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)


def derive_key_secure_cryptography(password: bytes) -> bytes:
    """Secure cryptography PBKDF2HMAC with dynamic salt and 600,000 iterations."""
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return kdf.derive(password)
