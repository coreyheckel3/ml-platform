import base64
import hashlib
import hmac
import secrets

HASH_NAME = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 390_000
SALT_BYTES = 16


class PasswordHasher:
    def hash(self, password: str) -> str:
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters.")
        salt = secrets.token_bytes(SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, DEFAULT_ITERATIONS)
        return "$".join(
            [
                HASH_NAME,
                str(DEFAULT_ITERATIONS),
                base64.urlsafe_b64encode(salt).decode(),
                base64.urlsafe_b64encode(digest).decode(),
            ]
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_raw, salt_raw, expected_raw = password_hash.split("$", 3)
            if algorithm != HASH_NAME:
                return False
            iterations = int(iterations_raw)
            salt = base64.urlsafe_b64decode(salt_raw.encode())
            expected = base64.urlsafe_b64decode(expected_raw.encode())
        except (ValueError, TypeError):
            return False

        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)

