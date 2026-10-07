"""Secure fixture for CR2: Authenticated and safe encryption modes."""

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt_data_gcm_pycryptodome(key: bytes, plaintext: bytes, nonce: bytes) -> bytes:
    """Secure PyCryptodome AES-GCM authenticated encryption."""
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return ciphertext + tag


def encrypt_data_gcm_cryptography(key: bytes, plaintext: bytes, nonce: bytes) -> bytes:
    """Secure cryptography AESGCM authenticated encryption."""
    aesgcm = AESGCM(key)
    return aesgcm.encrypt(nonce, plaintext, None)
