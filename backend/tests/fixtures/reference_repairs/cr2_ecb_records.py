"""Reference repair (tests only): versioned AES-GCM for new records, ECB kept for legacy reads."""

import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"CAv2:"


def encrypt(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt a customer record with AES."""
    nonce = os.urandom(12)
    return _MAGIC + nonce + AESGCM(key).encrypt(nonce, plaintext, _MAGIC)


def decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """Decrypt a customer record produced by encrypt()."""
    if ciphertext.startswith(_MAGIC):
        nonce = ciphertext[len(_MAGIC) : len(_MAGIC) + 12]
        return AESGCM(key).decrypt(nonce, ciphertext[len(_MAGIC) + 12 :], _MAGIC)
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()
