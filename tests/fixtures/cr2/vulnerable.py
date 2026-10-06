"""Vulnerable fixture for CR2: Electronic Codebook (ECB) mode encryption."""

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


def encrypt_data_pycryptodome(key: bytes, plaintext: bytes) -> bytes:
    """Vulnerable PyCryptodome AES ECB encryption."""
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(plaintext)


def encrypt_data_cryptography(key: bytes, plaintext: bytes) -> bytes:
    """Vulnerable cryptography AES ECB encryption."""
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    return encryptor.update(plaintext) + encryptor.finalize()
