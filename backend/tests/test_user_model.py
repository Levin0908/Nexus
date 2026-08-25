import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import password_hasher
from app.db.session import SessionLocal
from app.models.user import User


@pytest.fixture
async def fresh_user_email() -> str:
    return f"test-{uuid.uuid4()}@example.com"


async def test_create_and_retrieve_user(fresh_user_email: str) -> None:
    hashed = password_hasher.hash("hunter2")
    async with SessionLocal() as session:
        user = User(email=fresh_user_email, password_hash=hashed)
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.email == fresh_user_email
        assert user.password_hash.startswith("$argon2id$")
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

        retrieved = (
            await session.execute(select(User).where(User.email == fresh_user_email))
        ).scalar_one()
        assert retrieved.id == user.id


async def test_duplicate_email_raises_integrity_error(fresh_user_email: str) -> None:
    hashed = password_hasher.hash("pw")
    async with SessionLocal() as session:
        session.add(User(email=fresh_user_email, password_hash=hashed))
        await session.commit()

    async with SessionLocal() as session:
        session.add(User(email=fresh_user_email, password_hash=hashed))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_email_is_case_insensitive(fresh_user_email: str) -> None:
    upper = fresh_user_email.upper()
    lower = fresh_user_email.lower()
    assert upper != lower

    async with SessionLocal() as session:
        session.add(User(email=lower, password_hash=password_hasher.hash("pw")))
        await session.commit()

    async with SessionLocal() as session:
        found = (await session.execute(select(User).where(User.email == upper))).scalar_one()
        assert found.email == lower


async def test_password_hash_is_argon2id_and_verifies(fresh_user_email: str) -> None:
    async with SessionLocal() as session:
        user = User(
            email=fresh_user_email,
            password_hash=password_hasher.hash("correct-pw"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    assert password_hasher.verify(user.password_hash, "correct-pw") is True
    assert password_hasher.verify(user.password_hash, "wrong-pw") is False
