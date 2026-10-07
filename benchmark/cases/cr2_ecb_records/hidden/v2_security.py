"""V2 security-property oracle. CANARY: cryptoaudit-hidden-oracle-cr2_ecb_records"""

from unittest import mock

from cryptography.hazmat.primitives.ciphers import modes

KEY = bytes(range(32))


def check_encrypt_does_not_use_ecb(ctx):
    def blocked(*args, **kwargs):
        raise AssertionError("ECB mode used for new encryption")

    with mock.patch.object(modes, "ECB", blocked):
        module = ctx.load_candidate()
        module.encrypt(KEY, b"record")


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
