import base64
import hashlib
import hmac
import json
import time
from typing import Any


class TokenError(Exception):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode())


class JwtSigner:
    def __init__(self, *, secret: str, issuer: str) -> None:
        if len(secret) < 16:
            raise ValueError("JWT secret must be at least 16 characters.")
        self._secret = secret.encode()
        self._issuer = issuer

    def encode(self, claims: dict[str, Any], *, ttl_seconds: int) -> str:
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            **claims,
            "iss": self._issuer,
            "iat": now,
            "nbf": now,
            "exp": now + ttl_seconds,
        }
        signing_input = ".".join(
            [
                _b64encode(json.dumps(header, separators=(",", ":")).encode()),
                _b64encode(json.dumps(payload, separators=(",", ":")).encode()),
            ]
        )
        signature = hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest()
        return f"{signing_input}.{_b64encode(signature)}"

    def decode(self, token: str) -> dict[str, Any]:
        try:
            header_raw, payload_raw, signature_raw = token.split(".", 2)
            signing_input = f"{header_raw}.{payload_raw}"
            expected = hmac.new(self._secret, signing_input.encode(), hashlib.sha256).digest()
            actual = _b64decode(signature_raw)
            if not hmac.compare_digest(actual, expected):
                raise TokenError("Invalid token signature.")

            header = json.loads(_b64decode(header_raw))
            payload = json.loads(_b64decode(payload_raw))
        except (ValueError, json.JSONDecodeError) as exc:
            raise TokenError("Malformed token.") from exc

        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            raise TokenError("Unsupported token header.")
        if payload.get("iss") != self._issuer:
            raise TokenError("Invalid token issuer.")
        now = int(time.time())
        if int(payload.get("nbf", 0)) > now:
            raise TokenError("Token is not active yet.")
        if int(payload.get("exp", 0)) <= now:
            raise TokenError("Token has expired.")
        return payload

