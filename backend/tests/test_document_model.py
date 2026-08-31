import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.security import password_hasher
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.user import User


@pytest.fixture
async def fresh_user() -> User:
    """Create and return a test user; cleaned up by the autouse fixture."""
    email = f"test-{uuid.uuid4()}@example.com"
    async with SessionLocal() as session:
        user = User(email=email, password_hash=password_hasher.hash("pw"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@pytest.fixture
async def _cleanup_documents() -> None:
    """Wipe any documents created during a test (after teardown)."""
    yield
    async with SessionLocal() as session:
        await session.execute(delete(Document))
        await session.commit()


async def test_create_and_retrieve_document(fresh_user: User, _cleanup_documents: None) -> None:
    owner_id = fresh_user.id
    doc = Document(
        owner_id=owner_id,
        filename="notes.pdf",
        mime_type="application/pdf",
        size_bytes=12345,
        storage_path=f"{owner_id}/abc.pdf",
        sha256="a" * 64,
    )

    async with SessionLocal() as session:
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        assert doc.id is not None
        assert doc.owner_id == owner_id
        assert doc.filename == "notes.pdf"
        assert doc.mime_type == "application/pdf"
        assert doc.size_bytes == 12345
        assert doc.storage_path == f"{owner_id}/abc.pdf"
        assert doc.sha256 == "a" * 64
        assert doc.status is DocumentStatus.UPLOADING
        assert doc.created_at is not None
        assert doc.updated_at is not None

        fetched = (
            await session.execute(select(Document).where(Document.id == doc.id))
        ).scalar_one()
        assert fetched.id == doc.id
        assert fetched.filename == "notes.pdf"


async def test_status_can_be_set_explicitly(fresh_user: User, _cleanup_documents: None) -> None:
    async with SessionLocal() as session:
        doc = Document(
            owner_id=fresh_user.id,
            filename="ready.txt",
            mime_type="text/plain",
            size_bytes=10,
            storage_path="x/ready.txt",
            sha256="b" * 64,
            status=DocumentStatus.READY,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

    assert doc.status is DocumentStatus.READY


async def test_owner_id_fk_is_required(fresh_user: User, _cleanup_documents: None) -> None:
    async with SessionLocal() as session:
        session.add(
            Document(
                owner_id=None,  # type: ignore[arg-type]
                filename="x",
                mime_type="text/plain",
                size_bytes=1,
                storage_path="x/x",
                sha256="c" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_invalid_owner_id_raises_integrity_error(
    fresh_user: User, _cleanup_documents: None
) -> None:
    bogus = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(
            Document(
                owner_id=bogus,
                filename="orphan.pdf",
                mime_type="application/pdf",
                size_bytes=1,
                storage_path="x/orphan.pdf",
                sha256="d" * 64,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_cascade_delete_with_owner(fresh_user: User, _cleanup_documents: None) -> None:
    async with SessionLocal() as session:
        doc = Document(
            owner_id=fresh_user.id,
            filename="cascade.pdf",
            mime_type="application/pdf",
            size_bytes=1,
            storage_path="x/cascade.pdf",
            sha256="e" * 64,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        doc_id = doc.id

    async with SessionLocal() as session:
        user = await session.get(User, fresh_user.id)
        assert user is not None
        await session.delete(user)
        await session.commit()

    async with SessionLocal() as session:
        survivor = await session.get(Document, doc_id)
        assert survivor is None, "document should be cascade-deleted with its owner"


async def test_public_schema_validates_from_orm(fresh_user: User, _cleanup_documents: None) -> None:
    from app.schemas.document import DocumentPublic

    async with SessionLocal() as session:
        doc = Document(
            owner_id=fresh_user.id,
            filename="schema.pdf",
            mime_type="application/pdf",
            size_bytes=42,
            storage_path="x/schema.pdf",
            sha256="f" * 64,
            status=DocumentStatus.READY,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        dumped = DocumentPublic.model_validate(doc)
        assert dumped.filename == "schema.pdf"
        assert dumped.size_bytes == 42
        assert dumped.status is DocumentStatus.READY
        assert dumped.owner_id == fresh_user.id
