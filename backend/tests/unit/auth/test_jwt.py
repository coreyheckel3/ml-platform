import pytest

from forgeml.platform.security.jwt import JwtSigner, TokenError


def test_jwt_signer_round_trips_claims() -> None:
    signer = JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test")

    token = signer.encode({"sub": "user-1", "typ": "access"}, ttl_seconds=60)
    claims = signer.decode(token)

    assert claims["sub"] == "user-1"
    assert claims["typ"] == "access"
    assert claims["iss"] == "forgeml-test"


def test_jwt_signer_rejects_tampered_token() -> None:
    signer = JwtSigner(secret="a-secret-long-enough-for-tests", issuer="forgeml-test")

    token = signer.encode({"sub": "user-1", "typ": "access"}, ttl_seconds=60)
    header, payload, signature = token.split(".", 2)
    replacement = "A" if signature[0] != "A" else "B"
    tampered = f"{header}.{payload}.{replacement}{signature[1:]}"

    with pytest.raises(TokenError):
        signer.decode(tampered)
