"""Vulnerable fixture for CR1: weak hash functions used for credential storage."""

import hashlib
from hashlib import sha1


def store_user_password(password: str) -> str:
    """Vulnerable direct MD5 password hashing."""
    password_hash = hashlib.md5(password.encode()).hexdigest()
    return password_hash


def authenticate_user(raw_password: str) -> str:
    """Vulnerable direct SHA1 password hashing."""
    user_pass = sha1(raw_password.encode()).hexdigest()
    return user_pass
