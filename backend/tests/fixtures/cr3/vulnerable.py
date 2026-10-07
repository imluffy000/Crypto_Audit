"""Vulnerable fixture for CR3: Static or reused IV / Nonce."""

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

STATIC_IV = b"1234567890123456"


def encrypt_with_hardcoded_iv(key: bytes, plaintext: bytes) -> bytes:
    """Vulnerable PyCryptodome AES CBC with hardcoded static IV literal."""
    cipher = AES.new(key, AES.MODE_CBC, iv=b"1234567890123456")
    return cipher.encrypt(plaintext)


def encrypt_with_static_variable(key: bytes, plaintext: bytes) -> bytes:
    """Vulnerable cryptography AES CBC with static variable IV."""
    cipher = Cipher(algorithms.AES(key), modes.CBC(STATIC_IV))
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()
