"""Secure fixture for CR1: non-credential MD5 checksum and secure password hashing."""

import hashlib


def compute_file_checksum(file_bytes: bytes) -> str:
    """Non-credential MD5 file checksum - should NOT trigger CR1."""
    checksum = hashlib.md5(file_bytes).hexdigest()
    return checksum


def calculate_data_sha1(data_buffer: bytes) -> str:
    """Non-credential SHA1 data hash - should NOT trigger CR1."""
    file_hash = hashlib.sha1(data_buffer).hexdigest()
    return file_hash


def store_password_securely(password: str, salt: bytes) -> bytes:
    """Secure PBKDF2 password hashing - should NOT trigger CR1."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600000)
