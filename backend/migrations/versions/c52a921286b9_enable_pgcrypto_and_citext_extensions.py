"""enable pgcrypto and citext extensions

Revision ID: c52a921286b9
Revises: e73269f6d3bd
Create Date: 2026-08-24 11:21:12.484863

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c52a921286b9'
down_revision: Union[str, Sequence[str], None] = 'e73269f6d3bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS citext;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
