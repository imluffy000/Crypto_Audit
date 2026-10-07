"""Vulnerable fixture for CR5: Weak randomness used for security-sensitive tokens."""

import random


def generate_session_token() -> str:
    """Vulnerable random.randint for generating session token."""
    session_token = str(random.randint(100000, 999999))
    return session_token


def generate_password_reset_code() -> str:
    """Vulnerable random.choice for generating password reset token."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    reset_code = "".join(random.choice(chars) for _ in range(16))
    return reset_code
