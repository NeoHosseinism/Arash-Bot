"""
OpenRouter API client with retry logic
"""
import asyncio
from typing import List, Dict, Any, Optional
import httpx
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for communicating with OpenRouter service"""
    
    def __init__(self):
        self.base_url = settings.OPENROUTER_SERVICE_URL
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        self.max_retries = 3
    
    async def send_chat_request(
        self,
        session_id: str,
        query: str,
        history: List[Dict[str, str]],
        pipeline: str,
        files: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Send chat request to OpenRouter service with retry logic"""
        
        # Format history for OpenRouter
        formatted_history = []
        for msg in history:
            formatted_history.append({
                "Role": msg.get("role", "user"),
                "Message": msg.get("content", ""),
                "Files": None
            })
        
        payload = {
            "UserId": session_id,
            "UserName": "MessengerBot",
            "SessionId": session_id,
            "History": formatted_history,
            "Pipeline": pipeline,
            "Query": query,
            "AudioFile": None,
            "Files": files or []
        }
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries} for session {session_id}")
                
                response = await self.client.post(
                    f"{self.base_url}/v2/chat",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully processed request for session {session_id}")
                return result
                
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries} "
                    f"for session {session_id}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error {e.response.status_code} for session {session_id}: {e}"
                )
                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                last_error = e
                logger.error(
                    f"Error on attempt {attempt + 1}/{self.max_retries} "
                    f"for session {session_id}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        error_msg = f"Failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def health_check(self) -> bool:
        """Check if OpenRouter service is healthy"""
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("OpenRouter client closed")


# Global instance
openrouter_client = OpenRouterClient()