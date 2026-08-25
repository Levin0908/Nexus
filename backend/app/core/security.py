from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class JWTSecretMissingError(RuntimeError):
    """Raised when JWT_SECRET_KEY is unset and we're not in debug mode."""


class PasswordHasher:
    def __init__(
        self,
        time_cost: int,
        memory_cost: int,
        parallelism: int,
        hash_len: int,
        salt_len: int,
        max_length: int,
    ) -> None:
        self._max_length = max_length
        self._hasher = _Argon2PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    def hash(self, plain: str) -> str:
        if not isinstance(plain, str):
            raise TypeError("password must be a str")
        if len(plain) == 0:
            raise ValueError("password must not be empty")
        if len(plain) > self._max_length:
            raise ValueError(f"password exceeds max length of {self._max_length} characters")
        return self._hasher.hash(plain)

    def verify(self, hashed: str, plain: str) -> bool:
        try:
            self._hasher.verify(hashed, plain)
            return True
        except VerifyMismatchError:
            return False
        except InvalidHashError:
            return False
        except VerificationError:
            return False


password_hasher = PasswordHasher(
    time_cost=settings.password_time_cost,
    memory_cost=settings.password_memory_cost,
    parallelism=settings.password_parallelism,
    hash_len=settings.password_hash_len,
    salt_len=settings.password_salt_len,
    max_length=settings.password_max_length,
)


_TOKEN_TYPE_ACCESS = "access"
_TOKEN_TYPE_REFRESH = "refresh"

_jwt_secret_cache: str | None = None


def _resolve_jwt_secret() -> str:
    """Return the JWT secret, resolved once per process.

    - If JWT_SECRET_KEY is set, use it.
    - Otherwise, in dev (debug=True), auto-generate a random secret and warn.
    - Otherwise (production), raise JWTSecretMissingError.
    """
    global _jwt_secret_cache
    if _jwt_secret_cache is not None:
        return _jwt_secret_cache
    if settings.jwt_secret_key:
        _jwt_secret_cache = settings.jwt_secret_key
        return _jwt_secret_cache
    if settings.debug:
        _jwt_secret_cache = secrets.token_urlsafe(64)
        logger.warning(
            "JWT_SECRET_KEY not set — generated an ephemeral dev secret. "
            "Tokens will not survive restart. Set JWT_SECRET_KEY for production."
        )
        return _jwt_secret_cache
    raise JWTSecretMissingError(
        "JWT_SECRET_KEY must be set in production. "
        'Generate one with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.'
    )


def _encode_token(
    *,
    subject: str,
    ttl: timedelta,
    token_type: str,
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": subject,
        "iat": now,
        "exp": now + ttl,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(
        claims,
        _resolve_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(*, subject: str, extra_claims: dict | None = None) -> str:
    return _encode_token(
        subject=subject,
        ttl=timedelta(minutes=settings.jwt_access_ttl_minutes),
        token_type=_TOKEN_TYPE_ACCESS,
        extra_claims=extra_claims,
    )


def create_refresh_token(*, subject: str) -> str:
    return _encode_token(
        subject=subject,
        ttl=timedelta(days=settings.jwt_refresh_ttl_days),
        token_type=_TOKEN_TYPE_REFRESH,
    )


class InvalidTokenError(jwt.PyJWTError):
    """Raised when a JWT is malformed, expired, signed with the wrong key, or
    has an unexpected `type` claim.

    Inherits from `jwt.PyJWTError` so callers can catch either.
    """


def decode_token(token: str, *, expected_type: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            _resolve_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if claims.get("type") != expected_type:
        raise InvalidTokenError(
            f"unexpected token type: expected {expected_type!r}, got {claims.get('type')!r}"
        )
    return claims
