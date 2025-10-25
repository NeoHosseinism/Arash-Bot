"""
Name Mapping Configuration
Maps technical service and model IDs to friendly, non-identifying names.
"""

from typing import Dict

# Model name mappings: technical_id -> friendly_name
MODEL_NAME_MAPPINGS: Dict[str, str] = {
    # Google Models
    "google/gemini-2.0-flash-001": "flash-alpha",
    "google/gemini-2.5-flash": "flash-beta",
    "google/gemma-3-1b-it": "compact-model",

    # OpenAI Models
    "openai/gpt-5-chat": "premium-chat",
    "openai/gpt-4o-search": "search-pro",
    "openai/gpt-4o-mini": "mini-chat",

    # Anthropic Models
    "anthropic/claude-opus-4.5": "reasoning-pro",
    "anthropic/claude-sonnet-4.5": "balanced-pro",

    # DeepSeek Models
    "deepseek/deepseek-chat-v3-0324": "deep-chat",
    "deepseek/deepseek-r1": "reasoning-alpha",

    # xAI Models
    "x-ai/grok-4-beta": "analysis-beta",

    # Meta Models
    "meta-llama/llama-4-maverick": "creative-model",

    # Mistral Models
    "mistralai/mistral-large": "enterprise-chat",
}

# Reverse mapping for converting friendly names back to technical IDs
FRIENDLY_TO_TECHNICAL: Dict[str, str] = {v: k for k, v in MODEL_NAME_MAPPINGS.items()}

# Service provider mappings
SERVICE_PROVIDER_MAPPINGS: Dict[str, str] = {
    "google": "provider-a",
    "openai": "provider-b",
    "anthropic": "provider-c",
    "deepseek": "provider-d",
    "x-ai": "provider-e",
    "meta-llama": "provider-f",
    "mistralai": "provider-g",
}

# Platform name mappings
PLATFORM_MAPPINGS: Dict[str, str] = {
    "telegram": "public-platform",
    "internal": "private-platform",
}

def get_friendly_model_name(technical_name: str) -> str:
    """
    Convert technical model name to friendly name.
    If no mapping exists, generates a generic name.

    Args:
        technical_name: Technical model identifier (e.g., "google/gemini-2.0-flash-001")

    Returns:
        Friendly name (e.g., "flash-alpha")
    """
    if technical_name in MODEL_NAME_MAPPINGS:
        return MODEL_NAME_MAPPINGS[technical_name]

    # Generate generic friendly name if not in mapping
    if "/" in technical_name:
        provider, model = technical_name.split("/", 1)
        provider_friendly = SERVICE_PROVIDER_MAPPINGS.get(provider, "provider-x")
        # Create a simple hash-based identifier to keep it consistent
        model_hash = hash(model) % 1000
        return f"{provider_friendly}-model-{model_hash:03d}"

    return f"model-{hash(technical_name) % 1000:03d}"

def get_technical_model_name(friendly_name: str) -> str:
    """
    Convert friendly model name back to technical name.

    Args:
        friendly_name: Friendly model identifier (e.g., "flash-alpha")

    Returns:
        Technical name (e.g., "google/gemini-2.0-flash-001")
        Returns input if no mapping exists.
    """
    return FRIENDLY_TO_TECHNICAL.get(friendly_name, friendly_name)

def get_friendly_platform_name(technical_name: str) -> str:
    """
    Convert platform name to friendly name.

    Args:
        technical_name: Technical platform name (e.g., "telegram")

    Returns:
        Friendly platform name (e.g., "public-platform")
    """
    return PLATFORM_MAPPINGS.get(technical_name, "unknown-platform")

def mask_session_id(session_id: str, show_chars: int = 8) -> str:
    """
    Mask session ID for logging, showing only first N characters.

    Args:
        session_id: Full session ID
        show_chars: Number of characters to show (default: 8)

    Returns:
        Masked session ID (e.g., "a1b2c3d4...")
    """
    if len(session_id) <= show_chars:
        return session_id
    return f"{session_id[:show_chars]}..."
