"""
Run FastAPI Service
"""
# Load environment variables first (before importing settings)
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )