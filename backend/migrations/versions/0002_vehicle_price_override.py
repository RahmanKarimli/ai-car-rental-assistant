"""Add per-vehicle daily price overrides.

The linked rate plan remains the fallback for vehicles without an override.
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE vehicles ADD COLUMN daily_rate_qepik BIGINT")
    op.execute("ALTER TABLE vehicles ADD CONSTRAINT vehicles_daily_rate_qepik_nonnegative CHECK (daily_rate_qepik IS NULL OR daily_rate_qepik >= 0)")


def downgrade():
    raise RuntimeError("Destructive downgrade is intentionally unsupported")
