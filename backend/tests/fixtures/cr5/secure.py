"""Secure fixture for CR5: secrets module for tokens and non-security random usage."""

import random
import secrets


def roll_dice() -> int:
    """Non-security use of random module - should NOT trigger CR5."""
    dice_roll = random.randint(1, 6)
    return dice_roll


def select_random_color() -> str:
    """Non-security use of random module - should NOT trigger CR5."""
    colors = ["red", "blue", "green"]
    selected_color = random.choice(colors)
    return selected_color


def generate_secure_api_key() -> str:
    """Secure secrets module for token generation - should NOT trigger CR5."""
    api_key = secrets.token_urlsafe(32)
    return api_key
