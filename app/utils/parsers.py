"""
Webhook parsers for different platforms
"""
from typing import Dict, Any, Optional
import logging

from app.models.schemas import IncomingMessage, MessageAttachment
from app.core.constants import MessageType

logger = logging.getLogger(__name__)


def parse_webhook_data(platform: str, data: Dict[str, Any]) -> Optional[IncomingMessage]:
    """Parse platform-specific webhook data"""
    
    if platform == "telegram":
        return parse_telegram_webhook(data)
    elif platform == "internal":
        return parse_internal_webhook(data)
    else:
        logger.warning(f"Unknown platform in webhook: {platform}")
        return None


def parse_telegram_webhook(data: Dict[str, Any]) -> Optional[IncomingMessage]:
    """Parse Telegram webhook"""
    if "message" not in data:
        return None
    
    msg = data["message"]
    
    # Extract basic info
    chat_id = str(msg["chat"]["id"])
    user_id = str(msg["from"]["id"])
    message_id = str(msg["message_id"])
    
    # Determine message type and content
    text = msg.get("text")
    attachments = []
    msg_type = MessageType.TEXT
    
    # Handle photo messages
    if "photo" in msg and msg["photo"]:
        msg_type = MessageType.IMAGE
        photo = msg["photo"][-1]  # Get largest photo
        attachments.append(MessageAttachment(
            type=MessageType.IMAGE,
            file_id=photo["file_id"],
            file_size=photo.get("file_size")
        ))
        text = msg.get("caption", text)
    
    # Handle document messages
    elif "document" in msg:
        msg_type = MessageType.DOCUMENT
        doc = msg["document"]
        attachments.append(MessageAttachment(
            type=MessageType.DOCUMENT,
            file_id=doc["file_id"],
            mime_type=doc.get("mime_type"),
            file_size=doc.get("file_size")
        ))
        text = msg.get("caption", text)
    
    return IncomingMessage(
        platform="telegram",
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        type=msg_type,
        attachments=attachments,
        metadata={
            "username": msg["from"].get("username"),
            "first_name": msg["from"].get("first_name"),
            "last_name": msg["from"].get("last_name"),
            "language_code": msg["from"].get("language_code")
        }
    )


def parse_internal_webhook(data: Dict[str, Any]) -> Optional[IncomingMessage]:
    """Parse internal messenger webhook"""
    
    # Handle image attachments
    attachments = []
    if "attachments" in data:
        for att in data["attachments"]:
            attachments.append(MessageAttachment(
                type=MessageType(att.get("type", "document")),
                data=att.get("data"),
                mime_type=att.get("mime_type"),
                file_size=att.get("file_size")
            ))
    
    return IncomingMessage(
        platform="internal",
        user_id=data.get("user_id", ""),
        chat_id=data.get("chat_id", ""),
        message_id=data.get("message_id", ""),
        text=data.get("text"),
        type=MessageType(data.get("type", "text")),
        attachments=attachments,
        metadata={
            "organization": data.get("organization"),
            "department": data.get("department"),
            "employee_id": data.get("employee_id"),
            "full_name": data.get("full_name")
        }
    )