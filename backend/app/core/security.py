from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.core.config import settings


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
