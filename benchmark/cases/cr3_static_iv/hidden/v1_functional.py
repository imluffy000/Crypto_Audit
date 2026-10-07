"""V1 functional oracle. CANARY: cryptoaudit-hidden-oracle-cr3_static_iv"""

KEYS = [bytes(range(16)), bytes(range(32))]
LENGTHS = [0, 1, 15, 16, 17, 100, 1000]


def check_roundtrip(ctx):
    module = ctx.load_candidate()
    for key in KEYS:
        for length in LENGTHS:
            plaintext = bytes((i * 11) % 256 for i in range(length))
            ciphertext = module.encrypt(key, plaintext)
            assert isinstance(ciphertext, bytes)
            assert module.decrypt(key, ciphertext) == plaintext, f"roundtrip failed (key={len(key)}B, len={length})"


def check_ciphertext_hides_plaintext(ctx):
    module = ctx.load_candidate()
    plaintext = b"session=abc123;user=alice"
    assert plaintext not in module.encrypt(KEYS[1], plaintext)
