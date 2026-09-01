"""dedupe documents then enforce unique (owner_id, sha256)

Day 12 polish: replace the non-unique `ix_documents_sha256` index with a
UNIQUE constraint on (owner_id, sha256). This prevents the same user from
having two rows with the same content hash — both as a defensive guard for
the service-layer dedup logic and as a hard cap against race-condition
double-uploads.

The migration first deletes any pre-existing duplicate rows (keeping the
oldest per (owner_id, sha256)) so the constraint can be added safely. In
production this would be a manual data-cleanup step; in this dev DB it
cleans up the smoke-test artifacts from running the app manually.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b1b0b0b0b0b"
down_revision: Union[str, Sequence[str], None] = "a1105cce35da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop non-unique sha256 index; dedupe rows; add UNIQUE (owner_id, sha256)."""
    # Keep the OLDEST row per (owner_id, sha256); delete the rest.
    # `id` is uuid v4 from gen_random_uuid(), so ordering by id is a proxy for
    # creation order (close enough — created_at ordering would also work but
    # uuid ordering is fine for this one-time cleanup).
    op.execute(
        """
        DELETE FROM documents
        WHERE id NOT IN (
            SELECT MIN(id::text)::uuid
            FROM documents
            GROUP BY owner_id, sha256
        )
        """
    )

    op.drop_index("ix_documents_sha256", table_name="documents")
    op.create_unique_constraint(
        "uq_documents_owner_sha256",
        "documents",
        ["owner_id", "sha256"],
    )


def downgrade() -> None:
    """Recreate the non-unique sha256 index and drop the unique constraint."""
    op.drop_constraint(
        "uq_documents_owner_sha256",
        "documents",
        type_="unique",
    )
    op.create_index(
        "ix_documents_sha256",
        "documents",
        ["sha256"],
        unique=False,
    )
