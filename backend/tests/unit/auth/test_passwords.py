from forgeml.platform.security.passwords import PasswordHasher


def test_password_hash_verifies_original_password() -> None:
    hasher = PasswordHasher()

    password_hash = hasher.hash("correct horse battery staple")

    assert password_hash.startswith("pbkdf2_sha256$")
    assert hasher.verify("correct horse battery staple", password_hash)
    assert not hasher.verify("wrong horse battery staple", password_hash)


def test_password_hash_rejects_short_password() -> None:
    hasher = PasswordHasher()

    try:
        hasher.hash("short")
    except ValueError as exc:
        assert "at least 12 characters" in str(exc)
    else:
        raise AssertionError("Expected short password to be rejected.")

