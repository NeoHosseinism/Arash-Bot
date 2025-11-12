"""
API Key Management Service
Handles creation, validation, and management of API keys for team-based access control.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.database import APIKey, Team, UsageLog

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manages API keys for team-based access control"""

    @staticmethod
    def generate_api_key() -> Tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            Tuple of (api_key, key_hash, key_prefix)
            - api_key: Full API key to give to user (show only once)
            - key_hash: SHA256 hash to store in database
            - key_prefix: First 8 characters for identification
        """
        # Generate a secure random key (32 bytes = 64 hex characters)
        api_key = f"ak_{secrets.token_urlsafe(32)}"

        # Create SHA256 hash for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Extract prefix for identification
        key_prefix = api_key[:12]  # "ak_" + first 8 chars

        return api_key, key_hash, key_prefix

    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash an API key for comparison.

        Args:
            api_key: The API key to hash

        Returns:
            SHA256 hash of the key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()

    @staticmethod
    def create_team(
        db: Session,
        name: str,
        description: Optional[str] = None,
        monthly_quota: Optional[int] = None,
        daily_quota: Optional[int] = None,
    ) -> Team:
        """
        Create a new team.

        Args:
            db: Database session
            name: Team name
            description: Team description
            monthly_quota: Monthly request quota (None = unlimited)
            daily_quota: Daily request quota (None = unlimited)

        Returns:
            Created team
        """
        team = Team(
            name=name,
            description=description,
            monthly_quota=monthly_quota,
            daily_quota=daily_quota,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        logger.info(f"Created team: {name} (ID: {team.id})")
        return team

    @staticmethod
    def create_api_key(
        db: Session,
        team_id: int,
        name: str,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        monthly_quota: Optional[int] = None,
        daily_quota: Optional[int] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[str, APIKey]:
        """
        Create a new API key for an external team (client).

        NOTE: This creates API keys for external teams only (chat service access).
        Super admin authentication is handled separately via SUPER_ADMIN_API_KEYS environment variable.

        Args:
            db: Database session
            team_id: Team ID
            name: Friendly name for the key
            created_by: User who created the key
            description: Description of the key
            monthly_quota: Monthly quota override (None = use team quota)
            daily_quota: Daily quota override (None = use team quota)
            expires_in_days: Days until expiration (None = never expires)

        Returns:
            Tuple of (api_key_string, api_key_object)
            - api_key_string: Full API key (show only once to user)
            - api_key_object: Database object
        """
        # Generate the key
        api_key_string, key_hash, key_prefix = APIKeyManager.generate_api_key()

        # Calculate expiration date
        expires_at = None
        if expires_in_days is not None:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create database record
        api_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            team_id=team_id,
            monthly_quota=monthly_quota,
            daily_quota=daily_quota,
            created_by=created_by,
            description=description,
            expires_at=expires_at,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)

        logger.info(f"Created API key: {name} (prefix: {key_prefix}) for team ID {team_id}")

        return api_key_string, api_key

    @staticmethod
    def validate_api_key(db: Session, api_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the key object if valid.

        Args:
            db: Database session
            api_key: API key to validate

        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = APIKeyManager.hash_key(api_key)

        # Find the key
        db_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()

        if not db_key:
            logger.warning(f"Invalid API key attempted (hash: {key_hash[:16]}...)")
            return None

        # Check if key is active
        if not db_key.is_active:
            logger.warning(f"Inactive API key attempted (prefix: {db_key.key_prefix})")
            return None

        # Check if key has expired
        if db_key.is_expired:
            logger.warning(f"Expired API key attempted (prefix: {db_key.key_prefix})")
            return None

        # Check if team is active
        if not db_key.team.is_active:
            logger.warning(
                f"API key from inactive team attempted (prefix: {db_key.key_prefix}, team: {db_key.team.name})"
            )
            return None

        # Update last used timestamp
        db_key.last_used_at = datetime.utcnow()
        db.commit()

        logger.debug(f"API key validated (prefix: {db_key.key_prefix}, team: {db_key.team.name})")
        return db_key

    @staticmethod
    def revoke_api_key(db: Session, key_id: int) -> bool:
        """
        Revoke (deactivate) an API key.

        Args:
            db: Database session
            key_id: API key ID

        Returns:
            True if revoked, False if not found
        """
        db_key = db.query(APIKey).filter(APIKey.id == key_id).first()

        if not db_key:
            return False

        db_key.is_active = False
        db.commit()

        logger.info(f"Revoked API key (prefix: {db_key.key_prefix})")
        return True

    @staticmethod
    def delete_api_key(db: Session, key_id: int) -> bool:
        """
        Permanently delete an API key.

        Args:
            db: Database session
            key_id: API key ID

        Returns:
            True if deleted, False if not found
        """
        db_key = db.query(APIKey).filter(APIKey.id == key_id).first()

        if not db_key:
            return False

        key_prefix = db_key.key_prefix
        db.delete(db_key)
        db.commit()

        logger.info(f"Deleted API key (prefix: {key_prefix})")
        return True

    @staticmethod
    def list_team_api_keys(db: Session, team_id: int) -> List[APIKey]:
        """
        List all API keys for a team.

        Args:
            db: Database session
            team_id: Team ID

        Returns:
            List of API keys
        """
        return db.query(APIKey).filter(APIKey.team_id == team_id).all()

    @staticmethod
    def get_team_by_name(db: Session, name: str) -> Optional[Team]:
        """
        Get team by name (legacy - use get_team_by_platform_name instead).

        Args:
            db: Database session
            name: Team name

        Returns:
            Team object if found, None otherwise
        """
        return db.query(Team).filter(Team.name == name).first()

    @staticmethod
    def get_team_by_platform_name(db: Session, platform_name: str) -> Optional[Team]:
        """
        Get team by platform name.

        Args:
            db: Database session
            platform_name: Platform name (e.g., "Internal-BI", "External-Telegram")

        Returns:
            Team object if found, None otherwise
        """
        return db.query(Team).filter(Team.platform_name == platform_name).first()

    @staticmethod
    def create_team_with_key(
        db: Session,
        platform_name: str,
        monthly_quota: Optional[int] = None,
        daily_quota: Optional[int] = None,
    ) -> Tuple[Team, str]:
        """
        Create a new team with auto-generated API key (one key per team).

        This is the new simplified method that creates a team and immediately
        generates its single API key.

        Args:
            db: Database session
            platform_name: Platform name (e.g., "Internal-BI", "External-Telegram")
            monthly_quota: Monthly request quota (None = unlimited)
            daily_quota: Daily request quota (None = unlimited)

        Returns:
            Tuple of (team, api_key_string)
            - team: Created team object
            - api_key_string: Full API key (show only once to user)
        """
        # Create team (use platform_name as both name and platform_name)
        team = Team(
            name=platform_name,  # Internal name same as platform_name
            platform_name=platform_name,
            monthly_quota=monthly_quota,
            daily_quota=daily_quota,
        )
        db.add(team)
        db.flush()  # Flush to get team.id before creating key

        # Auto-generate API key for this team
        api_key_string, key_hash, key_prefix = APIKeyManager.generate_api_key()

        api_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=f"API Key for {platform_name}",  # Auto-generated name
            team_id=team.id,
            monthly_quota=None,  # Use team quotas
            daily_quota=None,  # Use team quotas
            created_by="system",  # Auto-created by system
            description=f"Auto-generated key for {platform_name}",
        )
        db.add(api_key)
        db.commit()
        db.refresh(team)

        logger.info(
            f"Created team '{platform_name}' (ID: {team.id}) with auto-generated API key (prefix: {key_prefix})"
        )

        return team, api_key_string

    @staticmethod
    def get_team_by_id(db: Session, team_id: int) -> Optional[Team]:
        """
        Get team by ID.

        Args:
            db: Database session
            team_id: Team ID

        Returns:
            Team object if found, None otherwise
        """
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def list_all_teams(db: Session, active_only: bool = True) -> List[Team]:
        """
        List all teams.

        Args:
            db: Database session
            active_only: Only return active teams

        Returns:
            List of teams
        """
        query = db.query(Team)
        if active_only:
            query = query.filter(Team.is_active)
        return query.all()

    @staticmethod
    def update_team(
        db: Session,
        team_id: int,
        platform_name: Optional[str] = None,
        monthly_quota: Optional[int] = None,
        daily_quota: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Team]:
        """
        Update team settings.

        Changes:
        - Uses platform_name instead of name/description
        - Removed webhook fields

        Args:
            db: Database session
            team_id: Team ID
            platform_name: New platform name
            monthly_quota: New monthly quota
            daily_quota: New daily quota
            is_active: Active status

        Returns:
            Updated team if found, None otherwise
        """
        team = db.query(Team).filter(Team.id == team_id).first()

        if not team:
            return None

        if platform_name is not None:
            team.platform_name = platform_name
            team.name = platform_name  # Keep name in sync
        if monthly_quota is not None:
            team.monthly_quota = monthly_quota
        if daily_quota is not None:
            team.daily_quota = daily_quota
        if is_active is not None:
            team.is_active = is_active

        team.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(team)

        logger.info(f"Updated team: {team.platform_name} (ID: {team.id})")
        return team

    @staticmethod
    def delete_team(db: Session, team_id: int, force: bool = False) -> bool:
        """
        Delete a team. By default, only deletes if no active API keys exist.

        Args:
            db: Database session
            team_id: Team ID to delete
            force: If True, delete team and all associated API keys and usage logs

        Returns:
            True if deleted, False if not found or has active keys
        """
        team = db.query(Team).filter(Team.id == team_id).first()

        if not team:
            logger.warning(f"Team not found for deletion: ID {team_id}")
            return False

        # Check for active API keys
        active_keys = (
            db.query(APIKey).filter(APIKey.team_id == team_id, APIKey.is_active).count()
        )

        if active_keys > 0 and not force:
            logger.warning(
                f"Cannot delete team {team.name}: has {active_keys} active API keys. Use force=True to delete anyway."
            )
            raise ValueError(
                f"Team has {active_keys} active API keys. Revoke them first or use --force flag."
            )

        team_name = team.name

        # If force, delete all associated API keys and usage logs
        if force:
            # Delete usage logs first (foreign key dependency)
            deleted_logs = db.query(UsageLog).filter(UsageLog.team_id == team_id).delete()

            # Delete API keys
            deleted_keys = db.query(APIKey).filter(APIKey.team_id == team_id).delete()

            logger.info(
                f"Force deleting team {team_name}: removed {deleted_keys} keys and {deleted_logs} usage logs"
            )

        # Delete the team
        db.delete(team)
        db.commit()

        logger.info(f"Deleted team: {team_name} (ID: {team_id})")
        return True
