# Logging Guide

Complete logging configuration and reference for Arash External API Service v1.0

## Quick Reference

### Configuration Variables

```bash
# In your .env file:
LOG_LEVEL=DEBUG                # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_TIMESTAMP=both             # utc | ir | both
LOG_COLOR=auto                 # auto | true | false
NO_COLOR=0                     # 0 (allow) | 1 (force disable)
LOG_TIMESTAMP_PRECISION=6      # 3 (ms) | 6 (μs)
LOG_FILE=logs/arash_api_service.log
```

### Timestamp Modes

**UTC Only (`LOG_TIMESTAMP=utc`):**
```
[2025-11-08 11:04:40.401000 UTC][info] server_started port=8080
```

**Iranian Only (`LOG_TIMESTAMP=ir`):**
```
[1404-08-17 14:34:40.403000 IR][info] server_started port=8080
```

**Both (`LOG_TIMESTAMP=both`):**
```
[2025-11-08 11:04:40.404000 UTC][1404-08-17 14:34:40.404000 IR][info] server_started port=8080
```

### Quick Commands

```bash
# Run interactive timestamp mode demo
python3 demo_timestamp_modes.py

# Run comprehensive logging tests
python3 tests/test_logging.py

# Use make command
make demo-logging

# Change mode in .env
sed -i 's/LOG_TIMESTAMP=.*/LOG_TIMESTAMP=utc/' .env  # UTC only
sed -i 's/LOG_TIMESTAMP=.*/LOG_TIMESTAMP=ir/' .env   # IR only
sed -i 's/LOG_TIMESTAMP=.*/LOG_TIMESTAMP=both/' .env # Both
```

---

## Configuration Details

### 1. LOG_TIMESTAMP (Timestamp Display Mode)

Controls which timestamps are shown in log output.

**Options:**
- `utc` - Show only UTC timestamp
- `ir` - Show only Iranian (Jalali/Solar Hijri) timestamp
- `both` - Show both UTC and Iranian timestamps (default)

---

### 2. LOG_LEVEL (Log Verbosity)

Controls which log messages are shown based on severity.

**Options:**
- `DEBUG` - Show all messages (most verbose)
- `INFO` - Show info, warning, and error messages
- `WARNING` - Show warning and error messages only
- `ERROR` - Show error messages only
- `CRITICAL` - Show only critical errors

**Example:**
```bash
LOG_LEVEL=DEBUG  # Development
LOG_LEVEL=INFO   # Staging
LOG_LEVEL=WARNING # Production
```

---

### 3. LOG_COLOR (Color Output Control)

Controls whether log output is colorized.

**Options:**
- `auto` - Automatically detect TTY and enable colors (default)
- `true` - Always enable colors (even for redirected output)
- `false` - Always disable colors

**Auto-disable conditions:**
- Output is not a TTY (e.g., redirected to file)
- Running in Docker/Kubernetes
- `NO_COLOR=1` is set
- Output is piped to another command

---

### 4. NO_COLOR (Force Disable Colors)

Override to force disable all color output.

**Options:**
- `0` - Allow colors (respects LOG_COLOR setting)
- `1` - Force disable colors (overrides LOG_COLOR)

---

### 5. LOG_TIMESTAMP_PRECISION

Controls the precision of microsecond display in timestamps.

**Options:**
- `3` - Milliseconds (3 digits after seconds)
- `6` - Microseconds (6 digits after seconds) - default

---

## Environment Presets

### Development
```bash
LOG_LEVEL=DEBUG
LOG_TIMESTAMP=both
LOG_COLOR=auto
NO_COLOR=0
LOG_TIMESTAMP_PRECISION=6
```

### Staging
```bash
LOG_LEVEL=INFO
LOG_TIMESTAMP=both
LOG_COLOR=auto
NO_COLOR=0
LOG_TIMESTAMP_PRECISION=6
```

### Production
```bash
LOG_LEVEL=WARNING
LOG_TIMESTAMP=utc
LOG_COLOR=false
NO_COLOR=1
LOG_TIMESTAMP_PRECISION=3
```

### CI/CD
```bash
LOG_LEVEL=INFO
LOG_TIMESTAMP=utc
LOG_COLOR=false
NO_COLOR=1
LOG_TIMESTAMP_PRECISION=3
```

---

## Log Format Specification

### Structure
```
[timestamp(s)][level] message [context] key=value...
```

### Components

1. **Timestamps** (Cyan for UTC, Blue for IR)
   - Format: `[YYYY-MM-DD HH:MM:SS.μs UTC]` and/or `[YYYY-MM-DD HH:MM:SS.μs IR]`
   - **IMPORTANT**: NO 'J' prefix in Iranian dates: `1404-08-17` NOT `J1404-08-17`

2. **Level** (Color-coded)
   - `[debug]` - Gray (90)
   - `[info]` - Green (92)
   - `[warn]` - Yellow (93)
   - `[error]` - Red (91) - colors both bracket and message

3. **Message** (snake_case, max 80 chars)
   - Example: `server_started`, `auth_success`, `payment_failed`

4. **Context** (Magenta, optional)
   - Format: `[module.component]`
   - Example: `[api.auth]`, `[db.postgres]`, `[session.manager]`

5. **Key-Value Pairs** (Keys in Cyan)
   - Format: `key=value key=value...`
   - Keys: snake_case (colored cyan)
   - Values: Unquoted for simple values, quoted for complex values
   - Example: `user_id=1234 method=jwt error="card declined"`

### Reserved Keys
- `user_id`, `request_id`, `trace_id`
- `duration_ms`, `status_code`
- `error`, `stack_trace`
- `model`, `tokens`, `cost_usd`
- `chat_id`, `message_type`

### Color Codes (ANSI)

| Component | Color | Code |
|-----------|-------|------|
| UTC timestamp | Cyan | 96 |
| IR timestamp | Blue | 94 |
| debug level | Gray | 90 |
| info level | Green | 92 |
| warn level | Yellow | 93 |
| error level | Red | 91 |
| context | Magenta | 95 |
| keys | Cyan | 36 |

---

## Usage Examples

### Standard Logging
```python
import logging

logger = logging.getLogger("app.api.routes")
logger.info("user_login user_id=1234 ip=192.168.1.100")
logger.error("auth_failed user_id=1234 error=\"invalid password\"")
```

### Structured Logging
```python
from app.utils.logger import get_structured_logger

slog = get_structured_logger("app.services.payment")
slog.info("payment_processed",
          context="payment.stripe",
          user_id=1234,
          amount=99.99,
          currency="USD")
```

---

## Troubleshooting

### Colors not showing
1. Check if output is a TTY: `python3 -c "import sys; print(sys.stdout.isatty())"`
2. Check `LOG_COLOR` setting in `.env`
3. Check if `NO_COLOR=1` is set
4. Verify you're not piping output

### Wrong timestamp mode
1. Check `LOG_TIMESTAMP` in `.env`
2. Restart the application after changing
3. Verify settings loaded: Check startup logs

### Logs not appearing
1. Check `LOG_LEVEL` setting
2. Verify log file path exists
3. Check file permissions

---

## Best Practices

1. **Development:** Use `both` timestamps, `DEBUG` level, and colors
2. **Staging:** Use `both` timestamps, `INFO` level, and colors
3. **Production:** Use `utc` only, `WARNING` level, no colors
4. **CI/CD:** Use `utc` only, `INFO` level, no colors
5. **Monitoring:** Parse UTC timestamps for consistency
6. **Debugging:** Use `both` to correlate local and server times

---

## Key Rules

1. ⚠️ **NO 'J' prefix**: `1404-08-17` NOT `J1404-08-17`
2. **Messages**: snake_case, max 80 chars
3. **Keys**: snake_case, colored cyan
4. **Values**: quote if contains spaces/special chars
5. **Context**: comes after message and key-values

---

## Performance Considerations

- Color codes add minimal overhead (~1-2%)
- Dual timestamps add ~5-10% overhead
- UTC-only mode is fastest
- File logging is asynchronous and buffered

---

## Testing

### Interactive Demo
```bash
# Run the demo script to see all modes in action
python3 demo_timestamp_modes.py

# Or use make command
make demo-logging
```

### Comprehensive Tests
```bash
# Run all logging tests
python3 tests/test_logging.py
```

### Manual Testing
```bash
# Test UTC only
echo "LOG_TIMESTAMP=utc" >> .env
python3 -c "from app.utils.logger import setup_logging; import logging; setup_logging(); logging.info('test')"

# Test IR only
echo "LOG_TIMESTAMP=ir" >> .env
python3 -c "from app.utils.logger import setup_logging; import logging; setup_logging(); logging.info('test')"

# Test both
echo "LOG_TIMESTAMP=both" >> .env
python3 -c "from app.utils.logger import setup_logging; import logging; setup_logging(); logging.info('test')"
```

---

## See Also

- `tests/test_logging.py` - Comprehensive logging examples and tests
- `demo_timestamp_modes.py` - Interactive timestamp mode demo
- `.env.example` - Configuration template
