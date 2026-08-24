import pytest

from app.core.security import PasswordHasher, password_hasher


def test_singleton_hasher_is_configured() -> None:
    assert isinstance(password_hasher, PasswordHasher)


def test_hash_differs_per_call() -> None:
    h1 = password_hasher.hash("correct horse battery staple")
    h2 = password_hasher.hash("correct horse battery staple")
    assert h1 != h2
    assert h1.startswith("$argon2id$")


def test_hash_then_verify_returns_true() -> None:
    plain = "sup3r-secret-passw0rd!"
    hashed = password_hasher.hash(plain)
    assert password_hasher.verify(hashed, plain) is True


def test_verify_rejects_wrong_password() -> None:
    hashed = password_hasher.hash("the-right-one")
    assert password_hasher.verify(hashed, "the-wrong-one") is False


def test_verify_rejects_tampered_hash() -> None:
    hashed = password_hasher.hash("anything")
    tampered = hashed[:-1] + ("A" if hashed[-1] != "A" else "B")
    assert password_hasher.verify(tampered, "anything") is False


def test_verify_rejects_garbage_hash() -> None:
    assert password_hasher.verify("not-a-real-hash", "anything") is False
    assert password_hasher.verify("", "anything") is False


def test_hash_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="empty"):
        password_hasher.hash("")


def test_hash_rejects_oversize_password() -> None:
    too_long = "x" * (password_hasher._max_length + 1)  # noqa: SLF001
    with pytest.raises(ValueError, match="max length"):
        password_hasher.hash(too_long)


def test_hash_accepts_max_length_password() -> None:
    boundary = "y" * password_hasher._max_length  # noqa: SLF001
    hashed = password_hasher.hash(boundary)
    assert password_hasher.verify(hashed, boundary) is True


def test_hash_rejects_non_string_password() -> None:
    with pytest.raises(TypeError):
        password_hasher.hash(123456)  # type: ignore[arg-type]
