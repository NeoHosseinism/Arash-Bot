"""update_access_levels_remove_team_lead_rename_user_to_team

Revision ID: 6f4dbeea5805
Revises: 71521c6321dc
Create Date: 2025-11-08 12:31:09.969280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f4dbeea5805'
down_revision: Union[str, None] = '71521c6321dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Update access levels to new two-tier system:
    - Rename 'user' to 'team' (external teams)
    - Rename 'team_lead' to 'team' (consolidate into single level)
    - Keep 'admin' as-is (super admins)

    TWO-TIER SYSTEM:
    - ADMIN: Super admins (internal team) - full access to admin endpoints
    - TEAM: External teams (clients) - can only use chat service
    """
    # Update existing 'user' access level to 'team'
    op.execute(
        """
        UPDATE api_keys
        SET access_level = 'team'
        WHERE access_level = 'user'
        """
    )

    # Update existing 'team_lead' access level to 'team'
    op.execute(
        """
        UPDATE api_keys
        SET access_level = 'team'
        WHERE access_level = 'team_lead'
        """
    )


def downgrade() -> None:
    """
    Rollback to old access levels:
    - Rename 'team' back to 'user' (cannot distinguish from old team_lead)

    NOTE: This is a lossy downgrade - we cannot distinguish between
    old 'user' and 'team_lead' levels, so everything becomes 'user'.
    """
    # Rename 'team' back to 'user' (lossy - cannot recover team_lead distinction)
    op.execute(
        """
        UPDATE api_keys
        SET access_level = 'user'
        WHERE access_level = 'team'
        """
    )
