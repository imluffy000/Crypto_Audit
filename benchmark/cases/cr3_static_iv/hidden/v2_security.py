"""V2 security-property oracle. CANARY: cryptoaudit-hidden-oracle-cr3_static_iv"""

from contextlib import contextmanager
from unittest import mock

from cryptography.hazmat.primitives.ciphers import aead, modes

KEY = bytes(range(32))
RUNS = 20


@contextmanager
def record_ivs():
    """Record IVs/nonces passed to cipher modes and AEAD constructions."""
    seen = []

    def wrap_mode(cls):
        def factory(value, *args, **kwargs):
            seen.append(bytes(value))
            return cls(value, *args, **kwargs)

        return factory

    def wrap_aead(cls):
        # AEAD classes are native types that cannot be patched in place, so wrap them.
        class Recording:
            generate_key = staticmethod(cls.generate_key)

            def __init__(self, *args, **kwargs):
                self._inner = cls(*args, **kwargs)

            def encrypt(self, nonce, data, associated_data=None):
                seen.append(bytes(nonce))
                return self._inner.encrypt(nonce, data, associated_data)

            def decrypt(self, nonce, data, associated_data=None):
                return self._inner.decrypt(nonce, data, associated_data)

        return Recording

    patches = [mock.patch.object(modes, name, wrap_mode(getattr(modes, name))) for name in ("CBC", "CTR", "GCM", "OFB", "CFB")]
    patches += [
        mock.patch.object(aead, name, wrap_aead(getattr(aead, name)))
        for name in ("AESGCM", "ChaCha20Poly1305", "AESCCM")
        if hasattr(aead, name)
    ]
    for patch in patches:
        patch.start()
    try:
        yield seen
    finally:
        for patch in reversed(patches):
            patch.stop()


def check_iv_is_unique_per_encryption(ctx):
    with record_ivs() as seen:
        module = ctx.load_candidate()
        for _ in range(RUNS):
            module.encrypt(KEY, b"same payload")
    assert seen, "no IV/nonce observed during encryption"
    assert len(set(seen)) == len(seen), "IV/nonce reused across encryptions"
    assert all(len(iv) >= 12 for iv in seen), "IV/nonce shorter than 96 bits"


def check_same_plaintext_encrypts_differently(ctx):
    module = ctx.load_candidate()
    ciphertexts = {module.encrypt(KEY, b"same payload") for _ in range(RUNS)}
    assert len(ciphertexts) == RUNS, "identical plaintexts produced identical ciphertexts"


def check_shared_prefix_not_revealed(ctx):
    module = ctx.load_candidate()
    first = module.encrypt(KEY, b"P" * 16 + b"tail-one")
    second = module.encrypt(KEY, b"P" * 16 + b"tail-two")
    assert first[:16] != second[:16] or first[16:32] != second[16:32], "common plaintext prefix visible in ciphertext"
