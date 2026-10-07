"""Domain enums for CryptoAudit analysis findings."""

from enum import Enum


class Severity(str, Enum):
    """Severity levels for cryptographic misuse findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Category(str, Enum):
    """Category classification for cryptographic misuses (CR1-CR5)."""

    WEAK_HASH_CREDENTIALS = "WEAK_HASH_CREDENTIALS"
    WEAK_OR_UNAUTHENTICATED_ENCRYPTION = "WEAK_OR_UNAUTHENTICATED_ENCRYPTION"
    STATIC_OR_REUSED_IV_NONCE = "STATIC_OR_REUSED_IV_NONCE"
    WEAK_KDF_PARAMETERS_OR_STATIC_SALT = "WEAK_KDF_PARAMETERS_OR_STATIC_SALT"
    WEAK_RANDOMNESS_SECURITY_TOKENS = "WEAK_RANDOMNESS_SECURITY_TOKENS"
    MISC = "MISC"


class Confidence(str, Enum):
    """Confidence level of rule detection context."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
