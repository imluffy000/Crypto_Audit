"""Reference repair (tests only): random IV stored with the ciphertext, static-IV payloads still readable."""

import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LEGACY_IV = b"0123456789abcdef"
_MAGIC = b"CAv2:"


def _cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt a session payload with AES-CBC."""
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return _MAGIC + iv + encryptor.update(padded) + encryptor.finalize()


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt a session payload produced by encrypt()."""
    if ciphertext.startswith(_MAGIC):
        iv = ciphertext[len(_MAGIC) : len(_MAGIC) + 16]
        return _cbc_decrypt(key, iv, ciphertext[len(_MAGIC) + 16 :])
    return _cbc_decrypt(key, _LEGACY_IV, ciphertext)
