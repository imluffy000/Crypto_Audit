"""Context fixture: methods with duplicate names, nested functions, module-level findings."""

import hashlib
import random

SALT = b"static_salt_1234"
ITERATIONS = 1000
module_token = random.randint(0, 999999)


class Alpha:
    def derive(self, password):
        return hashlib.pbkdf2_hmac("sha256", password, SALT, ITERATIONS)


class Beta:
    def derive(self, password, salt):
        return hashlib.pbkdf2_hmac("sha256", password, salt, 600000)


def outer(password):
    def inner_hash_password(pw):
        return hashlib.md5(pw.encode()).hexdigest()

    return inner_hash_password(password)


def _private_helper():
    return outer("x")
