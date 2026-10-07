"""Multi-rule vulnerable fixture containing CR1, CR2, CR3, CR4, and CR5 misuses."""

import hashlib
import random
from hashlib import sha1

from Crypto.Cipher import AES


def cr1_weak_hash(password: str) -> str:
    """CR1 misuse: weak MD5 password hashing."""
    user_pass = hashlib.md5(password.encode()).hexdigest()
    return user_pass


def cr2_ecb_mode(key: bytes, plaintext: bytes) -> bytes:
    """CR2 misuse: AES ECB mode encryption."""
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(plaintext)


def cr3_static_iv(key: bytes, plaintext: bytes) -> bytes:
    """CR3 misuse: static hardcoded IV."""
    static_iv = b"1234567890123456"
    cipher = AES.new(key, AES.MODE_CBC, iv=static_iv)
    return cipher.encrypt(plaintext)


def cr4_weak_kdf(password: str) -> bytes:
    """CR4 misuse: static salt and low iteration count (500 iterations)."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"static_salt", 500)


def cr5_weak_random() -> str:
    """CR5 misuse: random module for session token generation."""
    session_token = str(random.randint(100000, 999999))
    return session_token
