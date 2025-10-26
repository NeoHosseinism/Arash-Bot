# Model Mapping Fix - Comprehensive Review

## Problem Summary

Technical model IDs (e.g., `google/gemini-2.0-flash-001`) are being exposed to end users in:
1. ✗ API responses (`/`, `/health`, `/platforms`, `/sessions`, `/stats`)
2. ✗ Telegram bot responses
3. ✗ Command outputs (`/start`, `/help`, `/status`, `/model`, `/models`)
4. ✗ Session listings

**Goal**: Users should ONLY see friendly names like "Gemini 2.0 Flash", never technical IDs.

---

## Files That Need Changes

### 1. **app/services/platform_manager.py**
**Current Problem**: Returns technical IDs directly
```python
def get_available_models(self, platform: str) -> List[str]:
    return config.available_models  # Returns technical IDs!
```

**Fix**: Add new methods
```python
def get_available_models_friendly(self, platform: str) -> List[str]:
    """Get available models as friendly names"""
    technical_models = self.get_available_models(platform)
    return [get_friendly_model_name(m) for m in technical_models]

def get_default_model_friendly(self, platform: str) -> str:
    """Get default model as friendly name"""
    technical = self.get_default_model(platform)
    return get_friendly_model_name(technical)

def resolve_model_name(self, model_input: str, platform: str) -> Optional[str]:
    """
    Convert any model name (friendly, alias, or technical) to technical ID.
    Returns None if model not available on platform.
    """
    # Check if already technical and available
    if self.is_model_available(platform, model_input):
        return model_input

    # Try as friendly name
    technical = get_technical_model_name(model_input)
    if self.is_model_available(platform, technical):
        return technical

    # Try as alias
    from app.core.constants import MODEL_ALIASES, TELEGRAM_MODEL_ALIASES
    aliases = TELEGRAM_MODEL_ALIASES if platform == "telegram" else MODEL_ALIASES
    if model_input.lower() in aliases:
        friendly = aliases[model_input.lower()]
        technical = get_technical_model_name(friendly)
        if self.is_model_available(platform, technical):
            return technical

    return None
```

---

### 2. **app/api/routes.py**
**Current Problem**: Exposes technical IDs in ALL responses

**Lines to Fix**:
- Line 51: `"model": telegram_config.model,` → Use friendly name
- Line 57: `"models": internal_config.available_models,` → Use friendly names
- Line 141: `"model": telegram_config.model,` → Use friendly name
- Line 150: `"available_models": internal_config.available_models,` → Use friendly names
- Line 188: `"current_model": session.current_model,` → Use friendly name
- Line 265: `"model": platform_manager.get_config("telegram").model,` → Use friendly name

**Fix Example**:
```python
from app.core.name_mapping import get_friendly_model_name

# In root() function
return HealthCheckResponse(
    service="Arash External API Service",
    version="1.0.0",
    status="healthy",
    platforms={
        "telegram": {
            "type": "public",
            "model": get_friendly_model_name(telegram_config.model),  # ✓ Friendly
            "rate_limit": telegram_config.rate_limit,
            "model_switching": False,
        },
        "internal": {
            "type": "private",
            "models": [get_friendly_model_name(m) for m in internal_config.available_models],  # ✓ Friendly
            "rate_limit": internal_config.rate_limit,
            "model_switching": True,
        },
    },
    active_sessions=len(session_manager.sessions),
    timestamp=datetime.now(),
)
```

---

### 3. **app/services/command_processor.py**
**Current Problem**: Shows technical IDs to users everywhere

**Lines to Fix**:
- Line 90, 96: `/start` shows technical model name
- Line 114, 122, 139: `/help` and `/status` show technical model name
- Line 173, 177-180: `/model` lists technical IDs
- Line 208: Model switching - needs to accept friendly names as input
- Line 221-225: `/models` lists technical IDs

**Fix Example**:
```python
from app.core.name_mapping import get_friendly_model_name

async def handle_start(self, session: ChatSession, args: List[str]) -> str:
    """Handle /start command"""
    config = platform_manager.get_config(session.platform)
    friendly_model = get_friendly_model_name(session.current_model)  # ✓ Convert to friendly

    if session.platform == "internal":
        welcome = MESSAGES_FA["welcome_internal"].format(model=friendly_model)
        if session.is_admin:
            welcome += MESSAGES_FA["welcome_internal_admin"]
        return welcome
    else:
        return MESSAGES_FA["welcome_telegram"].format(
            model=friendly_model,  # ✓ Friendly
            rate_limit=config.rate_limit
        )

async def handle_model(self, session: ChatSession, args: List[str]) -> str:
    """Handle /model command"""
    if not args:
        # Show available models as FRIENDLY names
        friendly_models = platform_manager.get_available_models_friendly(session.platform)
        current_friendly = get_friendly_model_name(session.current_model)

        models_text = f"**مدل فعلی:** {current_friendly}\n\n"
        models_text += f"**مدل‌های موجود:**\n"

        for model in friendly_models:
            if model == current_friendly:
                models_text += f"• **{model}** ← فعلی\n"
            else:
                models_text += f"• {model}\n"

        return models_text

    # User provided model name - resolve it
    model_input = " ".join(args)  # Support multi-word names like "Gemini 2.0 Flash"

    # Resolve to technical ID (handles friendly names, aliases, technical IDs)
    technical_model = platform_manager.resolve_model_name(model_input, session.platform)

    if not technical_model:
        friendly_models = platform_manager.get_available_models_friendly(session.platform)
        return (
            MESSAGES_FA["model_invalid"].format(model=model_input) + "\n\n"
            f"**مدل‌های موجود:**\n" +
            "\n".join([f"• {m}" for m in friendly_models])
        )

    # Store technical ID internally
    session.current_model = technical_model

    # Show friendly name to user
    friendly_name = get_friendly_model_name(technical_model)
    return MESSAGES_FA["model_switched"].format(model=friendly_name)
```

---

### 4. **app/core/constants.py**
**Current Problem**: MODEL_ALIASES map to technical IDs instead of friendly names

**Fix**: Update aliases to map to friendly names
```python
# OLD (maps to technical IDs)
MODEL_ALIASES = {
    "gpt5": "openai/gpt-5-chat",  # ✗ Technical ID
    "gemini": "google/gemini-2.5-flash",  # ✗ Technical ID
}

# NEW (maps to friendly names)
MODEL_ALIASES = {
    "gpt5": "GPT-5 Chat",  # ✓ Friendly name
    "gpt": "GPT-5 Chat",
    "gemini": "Gemini 2.5 Flash",  # ✓ Friendly name
    "flash": "Gemini 2.0 Flash",
    "claude": "Claude Sonnet 4",
    "sonnet": "Claude Sonnet 4",
    "grok": "Grok 4",
    "deepseek": "DeepSeek Chat V3",
    "deep": "DeepSeek Chat V3",
    "mini": "GPT-4o Mini",
}

TELEGRAM_MODEL_ALIASES = {
    "gemini": "Gemini 2.5 Flash",
    "flash": "Gemini 2.0 Flash",
    "deepseek": "DeepSeek Chat V3",
    "deep": "DeepSeek Chat V3",
    "mini": "GPT-4o Mini",
    "gemma": "Gemma 3 1B",
}
```

---

### 5. **app/models/session.py**
**Problem**: session.current_model stores technical ID (this is OK internally)

**Fix**: Add property for friendly name
```python
@property
def current_model_friendly(self) -> str:
    """Get current model as friendly name for display"""
    from app.core.name_mapping import get_friendly_model_name
    return get_friendly_model_name(self.current_model)
```

---

## Implementation Order

1. ✓ **name_mapping.py** - Already has forward/reverse mapping
2. **platform_manager.py** - Add friendly name methods + resolve_model_name()
3. **constants.py** - Update MODEL_ALIASES to use friendly names
4. **session.py** - Add current_model_friendly property
5. **command_processor.py** - Use friendly names everywhere, resolve user input
6. **routes.py** - Convert all model IDs to friendly names in responses
7. **Test** - Verify no technical IDs exposed to users

---

## Testing Checklist

After fixes, verify:
- [ ] `GET /` shows friendly model names, not technical IDs
- [ ] `GET /platforms` shows friendly model names in available_models list
- [ ] `GET /sessions` shows friendly current_model
- [ ] `GET /stats` shows friendly model names in usage stats
- [ ] Telegram `/start` shows friendly model name
- [ ] Telegram `/help` shows friendly model name
- [ ] Telegram `/status` shows friendly current_model
- [ ] Telegram `/models` lists friendly names only
- [ ] Telegram `/model Gemini 2.0 Flash` works (friendly name input)
- [ ] Telegram `/model gemini` works (alias input)
- [ ] API calls to AI service still use technical IDs
- [ ] Swagger UI shows friendly names in responses

---

## Key Principle

**Data Flow:**
```
User Input (any format)
    ↓
resolve_model_name() → Technical ID
    ↓
Store internally (session.current_model = technical)
    ↓
Pass to AI Service (technical ID)
    ↓
Get response
    ↓
get_friendly_model_name() → Friendly Name
    ↓
Show to User (friendly name)
```

**Never expose technical IDs except:**
- Internal storage (database, sessions)
- AI service API calls
- Internal logs (optional)
