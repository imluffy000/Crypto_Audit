"""V3 legacy-compatibility oracle. CANARY: cryptoaudit-hidden-oracle-cr2_ecb_records"""


def check_legacy_records_decrypt(ctx):
    module = ctx.load_candidate()
    legacy = ctx.load_json("legacy_records.json")
    key = bytes.fromhex(legacy["key"])
    for record in legacy["records"]:
        recovered = module.decrypt(key, bytes.fromhex(record["ciphertext"]))
        assert recovered == bytes.fromhex(record["plaintext"]), "legacy record did not decrypt to its plaintext"
