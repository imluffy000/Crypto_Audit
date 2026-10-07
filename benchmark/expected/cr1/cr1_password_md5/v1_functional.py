"""V1 functional oracle. CANARY: cryptoaudit-hidden-oracle-cr1_password_md5"""

PASSWORDS = ["correct horse battery staple", "s3cret!", "pässwörd✓", ""]


def check_hash_returns_str(ctx):
    module = ctx.load_candidate()
    assert isinstance(module.hash_password("s3cret!"), str)


def check_roundtrip_verifies(ctx):
    module = ctx.load_candidate()
    for password in PASSWORDS:
        stored = module.hash_password(password)
        assert module.verify_password(password, stored) is True, f"roundtrip failed for {password!r}"


def check_wrong_password_rejected(ctx):
    module = ctx.load_candidate()
    stored = module.hash_password("correct horse battery staple")
    assert module.verify_password("Correct horse battery staple", stored) is False
    assert module.verify_password("", stored) is False
