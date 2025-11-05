"""
FastAPI application entry point with integrated Telegram bot
"""
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import router
from app.api.admin_routes import router as admin_router
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.ai_client import ai_client
from app.models.database import get_database
from app.core.database_init import initialize_database, create_logs_directory
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Telegram bot integration
telegram_bot = None
telegram_task = None
if settings.RUN_TELEGRAM_BOT:
    from telegram_bot.bot import TelegramBot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global telegram_bot, telegram_task

    # Startup
    logger.info("=" * 60)
    logger.info("Starting Arash External API Service v1.1")
    logger.info("=" * 60)

    app.state.start_time = datetime.now()

    # Create logs directory (safe for all environments including Docker)
    create_logs_directory()

    # Log environment configuration
    logger.info(f"Environment: {settings.ENVIRONMENT.upper()}")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info(f"API Docs: {'Enabled' if settings.ENABLE_API_DOCS else 'Disabled'}")

    # Log database configuration
    logger.info(f"Database: {settings.DB_NAME}")
    logger.info(f"   Host: {settings.DB_HOST}:{settings.DB_PORT}")
    logger.info(f"   User: {settings.DB_USER}")

    # Initialize database with Alembic migrations
    try:
        if not initialize_database():
            logger.error("[ERROR] Database initialization failed - API key management may not work")
        else:
            logger.info("[OK] Database initialized successfully with Alembic migrations")
    except Exception as e:
        logger.error(f"[ERROR] Database initialization failed: {e}")

    # Log platform configurations
    logger.info("Platform Configurations:")

    # Telegram
    telegram_config = platform_manager.get_config("telegram")
    logger.info("  Telegram (Public):")
    logger.info(f"    - Model: {telegram_config.model}")
    logger.info(f"    - Rate Limit: {telegram_config.rate_limit}/min")
    logger.info(f"    - Commands: {', '.join(telegram_config.commands)}")
    logger.info(f"    - Max History: {telegram_config.max_history}")

    # Internal
    internal_config = platform_manager.get_config("internal")
    logger.info("  Internal (Private):")
    logger.info(f"    - Default Model: {internal_config.model}")
    logger.info(f"    - Available Models: {len(internal_config.available_models)}")
    logger.info(f"    - Rate Limit: {internal_config.rate_limit}/min")
    logger.info(f"    - Commands: {len(internal_config.commands)}")
    logger.info(f"    - Max History: {internal_config.max_history}")
    logger.info(f"    - Authentication: {'Required' if internal_config.requires_auth else 'Not required'}")

    logger.info(f"\nAI Service: {settings.AI_SERVICE_URL}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Start Telegram bot if enabled
    if settings.RUN_TELEGRAM_BOT:
        logger.info("Starting integrated Telegram bot...")
        try:
            telegram_bot = TelegramBot(service_url=f"http://localhost:{settings.API_PORT}")
            telegram_bot.setup()
            # Run bot in background task
            telegram_task = asyncio.create_task(run_telegram_bot())
            logger.info("[OK] Telegram bot started successfully")
        except Exception as e:
            logger.error(f"[ERROR] Failed to start Telegram bot: {e}")
    else:
        logger.info("Telegram bot disabled (RUN_TELEGRAM_BOT=false)")

    logger.info("[OK] Service ready to handle requests!")
    logger.info("=" * 60)

    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Shutdown
    logger.info("Shutting down Arash External API Service...")

    # Stop Telegram bot
    if telegram_bot and telegram_task:
        logger.info("Stopping Telegram bot...")
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass
        if telegram_bot.application:
            await telegram_bot.application.stop()
            await telegram_bot.application.shutdown()
        logger.info("Telegram bot stopped")
    
    # Cancel cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Close HTTP client
    await ai_client.close()
    
    # Log statistics
    total_sessions = len(session_manager.sessions)
    telegram_count = session_manager.get_session_count("telegram")
    internal_count = session_manager.get_session_count("internal")
    
    logger.info(f"Sessions processed: {total_sessions}")
    logger.info(f"  - Telegram: {telegram_count}")
    logger.info(f"  - Internal: {internal_count}")
    logger.info("Shutdown complete.")


async def run_telegram_bot():
    """Run Telegram bot in background"""
    try:
        if telegram_bot:
            # Use run_polling for async operation
            await telegram_bot.application.initialize()
            await telegram_bot.application.start()
            await telegram_bot.application.updater.start_polling(drop_pending_updates=True)
            # Keep running until cancelled
            while True:
                await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Telegram bot task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in Telegram bot: {e}", exc_info=True)


async def periodic_cleanup():
    """Periodic cleanup of old sessions"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            cleared = session_manager.clear_old_sessions()
            session_manager.clear_rate_limits()
            if cleared > 0:
                logger.info(f"Periodic cleanup: removed {cleared} expired sessions")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Create FastAPI app
app = FastAPI(
    title="Arash External API Service",
    version="1.1.0",
    description="External API service supporting Telegram (public) and Internal (private) platforms with enterprise features",
    docs_url="/api/v1/docs" if settings.ENABLE_API_DOCS else None,
    redoc_url="/api/v1/redoc" if settings.ENABLE_API_DOCS else None,
    openapi_url="/api/v1/openapi.json" if settings.ENABLE_API_DOCS else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_server_error",
            "detail": "An internal error occurred" if settings.is_production else str(exc)
        }
    )


# Include routes with versioning
# API v1 endpoints
app.include_router(router, prefix="/api/v1", tags=["v1"])
app.include_router(admin_router, prefix="/api/v1")


# Unversioned health check endpoint (for monitoring systems)
@app.get("/health")
async def health_check():
    """
    Health check endpoint (unversioned for monitoring compatibility)

    SECURITY: Does NOT expose any internal details
    """
    ai_service_healthy = await ai_client.health_check()

    return {
        "status": "healthy" if ai_service_healthy else "degraded",
        "service": "Arash External API Service",
        "version": "1.1.0",
        "timestamp": datetime.now().isoformat(),
    }


# Development server helper
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=not settings.is_production,
        log_level=settings.LOG_LEVEL.lower()
    )