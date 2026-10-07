"""V1 functional oracle. CANARY: cryptoaudit-hidden-oracle-cr4_weak_kdf"""

PASSWORDS = ["example-test-input-1", "pässwörd✓", ""]


def check_hash_returns_str(ctx):
    module = ctx.load_candidate()
    assert isinstance(module.hash_password("example-test-input-1"), str)


def check_roundtrip_verifies(ctx):
    module = ctx.load_candidate()
    for password in PASSWORDS:
        stored = module.hash_password(password)
        assert module.verify_password(password, stored) is True, f"roundtrip failed for {password!r}"


def check_wrong_password_rejected(ctx):
    module = ctx.load_candidate()
    stored = module.hash_password("example-test-input-1")
    assert module.verify_password("EXAMPLE-test-input-1", stored) is False
