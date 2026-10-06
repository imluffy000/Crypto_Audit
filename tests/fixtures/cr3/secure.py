"""Secure fixture for CR3: Dynamic cryptographically secure IV / Nonce generation."""

import os
import secrets
from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt_with_dynamic_iv(key: bytes, plaintext: bytes) -> bytes:
    """Secure PyCryptodome AES CBC with os.urandom IV."""
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    return cipher.encrypt(plaintext)


def encrypt_with_secrets_nonce(key: bytes, plaintext: bytes) -> bytes:
    """Secure cryptography AES GCM with secrets.token_bytes nonce."""
    nonce = secrets.token_bytes(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()
