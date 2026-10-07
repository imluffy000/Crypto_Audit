"""V2 security-property oracle. CANARY: cryptoaudit-hidden-oracle-cr2_ecb_records"""

from unittest import mock

from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.primitives.ciphers import base as ciphers_base

KEY = bytes(range(32))


def check_encrypt_does_not_use_ecb(ctx):
    # Observe Cipher construction; mode classes are never replaced because the native backend
    # resolves them by exact type.
    modes_used = []
    real_cipher = ciphers.Cipher

    class RecordingCipher(real_cipher):
        def __init__(self, algorithm, mode, *args, **kwargs):
            modes_used.append(type(mode).__name__)
            super().__init__(algorithm, mode, *args, **kwargs)

    with mock.patch.object(ciphers, "Cipher", RecordingCipher), mock.patch.object(ciphers_base, "Cipher", RecordingCipher):
        module = ctx.load_candidate()
        module.encrypt(KEY, b"record")
    assert "ECB" not in modes_used, "ECB mode used for new encryption"


def check_no_repeated_block_pattern(ctx):
    module = ctx.load_candidate()
    ciphertext = module.encrypt(KEY, b"A" * 64)
    blocks = [ciphertext[i : i + 16] for i in range(0, len(ciphertext) - len(ciphertext) % 16, 16)]
    assert len(blocks) == len(set(blocks)), "identical plaintext blocks produce identical ciphertext blocks"


def check_encryption_is_randomized(ctx):
    module = ctx.load_candidate()
    assert module.encrypt(KEY, b"same record") != module.encrypt(KEY, b"same record")


def check_tampering_is_detected(ctx):
    module = ctx.load_candidate()
    plaintext = b"amount=100;account=alice;" * 3
    ciphertext = module.encrypt(KEY, plaintext)
    for position in (len(ciphertext) // 2, len(ciphertext) - 1):
        tampered = bytearray(ciphertext)
        tampered[position] ^= 0x01
        try:
            recovered = module.decrypt(KEY, bytes(tampered))
        except Exception:
            continue
        raise AssertionError(f"tampered ciphertext (byte {position}) accepted, decrypted to {recovered[:16]!r}...")
