"""
Bot service client for Telegram
"""
import asyncio
from typing import Optional
import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class BotServiceClient:
    """Client for communicating with bot service"""
    
    def __init__(self, service_url: str = "http://localhost:8001"):
        self.service_url = service_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.max_retries = 3
    
    async def send_message(
        self,
        user_id: str,
        chat_id: str,
        message_id: str,
        text: str = None,
        image_data: str = None,
        mime_type: str = None
    ) -> dict:
        """Send message to bot service with retry logic"""

        # Simplified payload for /api/v1/chat endpoint (public mode - no auth)
        # Images not supported in simplified version
        if image_data:
            logger.warning("Image attachments not supported in simplified API")

        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "text": text or "📷 [Image]"  # Fallback for image messages
        }

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.service_url}/api/v1/chat",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries} "
                    f"for chat {chat_id}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
                # Don't retry on client errors
                if 400 <= e.response.status_code < 500:
                    raise
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                last_error = e
                logger.error(
                    f"Error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise Exception(f"Failed after {self.max_retries} attempts: {last_error}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()