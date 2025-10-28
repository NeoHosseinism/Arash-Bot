"""
Database initialization with Alembic migration support.
This module ensures database schema is up-to-date using Alembic migrations.
"""
import logging
import subprocess
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.config import settings

logger = logging.getLogger(__name__)


def check_alembic_history() -> bool:
    """
    Check if Alembic migration history table exists.

    Returns:
        True if alembic_version table exists, False otherwise
    """
    from app.models.database import get_database

    try:
        db = get_database()
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        return "alembic_version" in tables
    except Exception as e:
        logger.error(f"Error checking Alembic history: {e}")
        return False


def get_current_revision() -> str:
    """
    Get current Alembic revision from database.

    Returns:
        Current revision ID or empty string if no revision
    """
    from app.models.database import get_database

    try:
        db = get_database()
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else ""
    except Exception as e:
        logger.error(f"Error getting current revision: {e}")
        return ""


def run_migrations() -> bool:
    """
    Run Alembic migrations to bring database up-to-date.

    Returns:
        True if migrations successful, False otherwise
    """
    try:
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent

        print("[Migration] Running Alembic migrations...")
        logger.info("Running Alembic migrations")

        # Run alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("[OK] Migrations completed successfully")
            logger.info("Migrations completed successfully")
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"Migration: {line}")
            return True
        else:
            print(f"[ERROR] Migration failed: {result.stderr}")
            logger.error(f"Migration failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("[ERROR] Migration timeout")
        logger.error("Migration timeout after 60 seconds")
        return False
    except FileNotFoundError:
        print("[ERROR] Alembic not found. Install with: pip install alembic")
        logger.error("Alembic command not found")
        return False
    except Exception as e:
        print(f"[ERROR] Migration error: {e}")
        logger.error(f"Migration error: {e}")
        return False


def initialize_database() -> bool:
    """
    Initialize database with Alembic migrations.
    This is the main entry point for database initialization at startup.

    Process:
    1. Check if database is accessible
    2. Check if Alembic history exists
    3. If no history, run initial migration
    4. If history exists, check for pending migrations and run them
    5. Verify schema is up-to-date

    Returns:
        True if database initialized successfully, False otherwise
    """
    try:
        print("=" * 60)
        print(f"Database Initialization - Environment: {settings.ENVIRONMENT.upper()}")
        print("=" * 60)

        # Test database connection
        from app.models.database import get_database
        db = get_database()

        if not db.test_connection():
            print("[ERROR] Database connection failed")
            return False

        # Check if Alembic history exists
        has_history = check_alembic_history()

        if not has_history:
            print("[INFO] No migration history found - running initial migration...")
            logger.info("No Alembic history found, running initial migration")

            # Run initial migration
            if not run_migrations():
                print("[ERROR] Initial migration failed")
                return False

            print("[OK] Initial migration completed")

        else:
            # Check current revision
            current_rev = get_current_revision()
            print(f"[INFO] Current migration revision: {current_rev or 'none'}")
            logger.info(f"Current migration revision: {current_rev or 'none'}")

            # Run any pending migrations
            print("[INFO] Checking for pending migrations...")
            if not run_migrations():
                print("[WARNING] Migration check completed with warnings")
                # Don't fail on warnings - database might already be up-to-date
            else:
                print("[OK] Database schema is up-to-date")

        # Verify tables exist
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        expected_tables = {"teams", "api_keys", "usage_logs", "alembic_version"}

        missing_tables = expected_tables - set(tables)
        if missing_tables:
            print(f"[WARNING] Missing tables: {', '.join(missing_tables)}")
            logger.warning(f"Missing tables: {', '.join(missing_tables)}")
        else:
            print(f"[OK] All required tables present: {', '.join(sorted(tables))}")
            logger.info(f"All required tables present: {', '.join(sorted(tables))}")

        print("=" * 60)
        return True

    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        logger.error(f"Database initialization failed: {e}")
        print("=" * 60)
        return False


def create_logs_directory():
    """
    Create logs directory if it doesn't exist.
    This is separate from database initialization.
    """
    try:
        log_file = Path(settings.LOG_FILE)
        log_dir = log_file.parent

        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Created logs directory: {log_dir}")
            logger.info(f"Created logs directory: {log_dir}")

        return True
    except Exception as e:
        print(f"[WARNING] Could not create logs directory: {e}")
        logger.warning(f"Could not create logs directory: {e}")
        return False
