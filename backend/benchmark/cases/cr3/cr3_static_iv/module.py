"""Encrypts session payloads before they are written to the cache."""

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

IV = b"0123456789abcdef"


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt a session payload with AES-CBC."""
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(IV)).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt a session payload produced by encrypt()."""
    decryptor = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()
