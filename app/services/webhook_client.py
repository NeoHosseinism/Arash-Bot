"""
Webhook client for sending callbacks to team webhook URLs
"""
import hashlib
import hmac
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from app.models.database import Team

logger = logging.getLogger(__name__)


class WebhookClient:
    """Client for sending webhook callbacks to teams"""

    def __init__(self, timeout: int = 10):
        """
        Initialize webhook client

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    def _generate_signature(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload

        Args:
            payload: JSON payload as string
            secret: Team's webhook secret

        Returns:
            Hexadecimal signature string
        """
        return hmac.new(
            key=secret.encode('utf-8'),
            msg=payload.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

    async def send_message_callback(
        self,
        team: Team,
        message_data: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> bool:
        """
        Send message callback to team's webhook URL

        Args:
            team: Team object with webhook configuration
            message_data: Original message data (user input, chat_id, etc.)
            response_data: AI response data (text, model, session_id, etc.)

        Returns:
            True if webhook was sent successfully, False otherwise
        """
        # Check if webhook is enabled and configured
        if not team.webhook_enabled or not team.webhook_url:
            logger.debug(f"Webhook not enabled for team {team.id} ({team.name})")
            return False

        # Prepare webhook payload
        payload = {
            "event": "message.response",
            "timestamp": datetime.utcnow().isoformat(),
            "team_id": team.id,
            "team_name": team.name,
            "message": message_data,
            "response": response_data
        }

        try:
            # Convert payload to JSON string for signing
            import json
            payload_str = json.dumps(payload, sort_keys=True)

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Arash-Bot-Webhook/1.0",
                "X-Webhook-Event": "message.response",
                "X-Webhook-Timestamp": payload["timestamp"],
            }

            # Add signature if secret is configured
            if team.webhook_secret:
                signature = self._generate_signature(payload_str, team.webhook_secret)
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            # Send webhook request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    team.webhook_url,
                    json=payload,
                    headers=headers
                )

                # Check response status
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook sent successfully to team {team.id} ({team.name}): {response.status_code}")
                    return True
                else:
                    logger.warning(
                        f"Webhook to team {team.id} ({team.name}) returned status {response.status_code}: {response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(f"Webhook timeout for team {team.id} ({team.name})")
            return False
        except httpx.RequestError as e:
            logger.error(f"Webhook request failed for team {team.id} ({team.name}): {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook to team {team.id} ({team.name}): {e}", exc_info=True)
            return False

    async def test_webhook(self, team: Team) -> Dict[str, Any]:
        """
        Send a test webhook to verify configuration

        Args:
            team: Team object with webhook configuration

        Returns:
            Dict with test results
        """
        if not team.webhook_url:
            return {
                "success": False,
                "error": "No webhook URL configured"
            }

        # Prepare test payload
        test_payload = {
            "event": "webhook.test",
            "timestamp": datetime.utcnow().isoformat(),
            "team_id": team.id,
            "team_name": team.name,
            "message": "This is a test webhook from Arash Bot"
        }

        try:
            import json
            payload_str = json.dumps(test_payload, sort_keys=True)

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Arash-Bot-Webhook/1.0",
                "X-Webhook-Event": "webhook.test",
                "X-Webhook-Timestamp": test_payload["timestamp"],
            }

            if team.webhook_secret:
                signature = self._generate_signature(payload_str, team.webhook_secret)
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    team.webhook_url,
                    json=test_payload,
                    headers=headers
                )

                return {
                    "success": response.status_code >= 200 and response.status_code < 300,
                    "status_code": response.status_code,
                    "response_text": response.text[:200] if response.text else None
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }


# Global webhook client instance
webhook_client = WebhookClient()
