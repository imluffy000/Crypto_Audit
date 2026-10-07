"""V3 legacy-compatibility oracle. CANARY: cryptoaudit-hidden-oracle-cr1_password_md5"""


def check_legacy_hashes_still_verify(ctx):
    module = ctx.load_candidate()
    for user in ctx.load_json("legacy_credentials.json")["users"]:
        assert module.verify_password(user["password"], user["stored"]) is True, f"legacy hash for {user['name']} rejected"


def check_legacy_hashes_reject_wrong_password(ctx):
    module = ctx.load_candidate()
    for user in ctx.load_json("legacy_credentials.json")["users"]:
        assert module.verify_password(user["password"] + "x", user["stored"]) is False
