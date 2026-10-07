"""V2 security-property oracle. CANARY: cryptoaudit-hidden-oracle-cr1_password_md5"""

import hashlib
from contextlib import contextmanager
from unittest import mock

PBKDF2_MIN_ITERATIONS = {"sha256": 600_000, "sha384": 600_000, "sha512": 210_000}
SCRYPT_MIN_N = 2**14
MIN_SALT_BYTES = 16


@contextmanager
def forbid_weak_hashes():
    real_new = hashlib.new

    def blocked(*args, **kwargs):
        raise AssertionError("MD5/SHA-1 used while creating a new password hash")

    def guarded_new(name, *args, **kwargs):
        if str(name).lower().replace("-", "") in {"md5", "sha1"}:
            blocked()
        return real_new(name, *args, **kwargs)

    with mock.patch.object(hashlib, "md5", blocked), mock.patch.object(hashlib, "sha1", blocked), mock.patch.object(
        hashlib, "new", guarded_new
    ):
        yield


@contextmanager
def record_kdf_calls():
    calls = []
    real_pbkdf2, real_scrypt = hashlib.pbkdf2_hmac, hashlib.scrypt

    def pbkdf2_hmac(hash_name, password, salt, iterations, dklen=None):
        calls.append(("pbkdf2", str(hash_name).lower(), bytes(salt), int(iterations)))
        return real_pbkdf2(hash_name, password, salt, iterations, dklen)

    def scrypt(password, *, salt, n, r, p, maxmem=0, dklen=64):
        calls.append(("scrypt", "scrypt", bytes(salt), int(n)))
        return real_scrypt(password, salt=salt, n=n, r=r, p=p, maxmem=maxmem, dklen=dklen)

    with mock.patch.object(hashlib, "pbkdf2_hmac", pbkdf2_hmac), mock.patch.object(hashlib, "scrypt", scrypt):
        yield calls


def _strong(call):
    kind, name, salt, cost = call
    if len(salt) < MIN_SALT_BYTES:
        return False
    if kind == "pbkdf2":
        return cost >= PBKDF2_MIN_ITERATIONS.get(name, float("inf"))
    return cost >= SCRYPT_MIN_N


def check_new_hashes_do_not_use_md5_or_sha1(ctx):
    with forbid_weak_hashes():
        module = ctx.load_candidate()
        module.hash_password("correct horse battery staple")


def check_hashes_are_salted(ctx):
    module = ctx.load_candidate()
    first = module.hash_password("correct horse battery staple")
    second = module.hash_password("correct horse battery staple")
    assert first != second, "identical passwords produce identical hashes (no per-password salt)"


def check_uses_slow_kdf_with_random_salt(ctx):
    with record_kdf_calls() as calls:
        module = ctx.load_candidate()
        module.hash_password("correct horse battery staple")
        module.hash_password("correct horse battery staple")
    strong = [c for c in calls if _strong(c)]
    assert len(strong) >= 2, f"no password KDF with adequate cost and >=16-byte salt observed: {calls}"
    assert len({c[2] for c in strong}) == len(strong), "salt reused across password hashes"


def check_hash_does_not_expose_password(ctx):
    module = ctx.load_candidate()
    stored = module.hash_password("correct horse battery staple")
    assert "correct horse" not in stored
    assert "correct horse".encode().hex() not in stored
