"""V1 functional oracle. CANARY: cryptoaudit-hidden-oracle-cr5_session_token"""

import string

ALLOWED = set(string.ascii_letters + string.digits)


def check_default_length(ctx):
    module = ctx.load_candidate()
    token = module.generate_session_token()
    assert isinstance(token, str) and len(token) == 32


def check_custom_lengths(ctx):
    module = ctx.load_candidate()
    for length in (1, 16, 64):
        assert len(module.generate_session_token(length)) == length


def check_alphabet_preserved(ctx):
    module = ctx.load_candidate()
    token = "".join(module.generate_session_token() for _ in range(20))
    assert set(token) <= ALLOWED, f"unexpected characters: {set(token) - ALLOWED}"
