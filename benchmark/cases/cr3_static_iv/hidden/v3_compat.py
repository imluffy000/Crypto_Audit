"""V3 legacy-compatibility oracle. CANARY: cryptoaudit-hidden-oracle-cr3_static_iv"""


def check_legacy_payloads_decrypt(ctx):
    module = ctx.load_candidate()
    legacy = ctx.load_json("legacy_payloads.json")
    key = bytes.fromhex(legacy["key"])
    for record in legacy["records"]:
        recovered = module.decrypt(key, bytes.fromhex(record["ciphertext"]))
        assert recovered == bytes.fromhex(record["plaintext"]), "legacy payload did not decrypt to its plaintext"
