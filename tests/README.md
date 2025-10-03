# Tests

Test suite for Arash Messenger Bot.

## 📁 Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_openrouter.py       # OpenRouter integration tests
├── test_api.py             # API endpoint tests (TODO)
├── test_commands.py        # Command processor tests (TODO)
└── README.md               # This file
```

## 🚀 Running Tests

### Run All Tests

```bash
# Using pytest
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=app --cov-report=html
```

### Run Specific Tests

```bash
# Run only OpenRouter tests
pytest tests/test_openrouter.py

# Run only fast tests (skip slow ones)
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run specific test class
pytest tests/test_openrouter.py::TestOpenRouterConnectivity

# Run specific test method
pytest tests/test_openrouter.py::TestOpenRouterConnectivity::test_base_url_reachable
```

### Manual Test (No pytest required)

```bash
# Run OpenRouter connectivity test directly
python tests/test_openrouter.py
```

This will run a detailed diagnostic test showing:
- ✓ Connection status
- ✓ Health check results
- ✓ Chat endpoint functionality
- ✓ Detailed error messages

## 🏷️ Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.slow` - Slow tests (network calls, etc.)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.openrouter` - Tests requiring OpenRouter service

### Examples

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run everything except OpenRouter tests
pytest -m "not openrouter"
```

## 📊 Test Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## 🔧 OpenRouter Tests

The `test_openrouter.py` file includes:

### Test Classes

1. **TestOpenRouterConnectivity**
   - Tests basic connectivity
   - Health endpoint check
   - Chat endpoint format validation

2. **TestOpenRouterClient**
   - Tests client initialization
   - Health check method
   - Chat request sending

3. **TestOpenRouterConfiguration**
   - Validates configuration
   - URL format checks
   - Model configuration

### Manual Diagnostic Test

```bash
python tests/test_openrouter.py
```

Output includes:
```
======================================================================
                OpenRouter Service Connectivity Test
======================================================================

Service URL: https://or.lucidfirm.ir
Telegram Model: google/gemini-2.0-flash-001
Internal Models: 11

----------------------------------------------------------------------

1. Testing Base URL Connectivity...
   ✓ Status: 200
   Response: ...

2. Testing Health Endpoint...
   ✓ Status: 200
   Response: ...

3. Testing Chat Endpoint...
   ✓ Status: 200
   Response: ...

4. Testing Client Health Check Method...
   ✓ Service is healthy

======================================================================
                              Test Complete
======================================================================
```

## 🐛 Troubleshooting

### Tests Fail with Connection Error

```bash
# Check if OpenRouter URL is correct
grep OPENROUTER_SERVICE_URL .env

# Test connectivity manually
curl -v https://or.lucidfirm.ir/health

# Run diagnostic
python tests/test_openrouter.py
```

### Import Errors

```bash
# Make sure you're in project root
cd /path/to/arash-bot

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest
```

### Async Tests Not Working

```bash
# Install pytest-asyncio
pip install pytest-asyncio

# Check pytest.ini has:
# asyncio_mode = auto
```

## 📝 Writing New Tests

### Example Unit Test

```python
import pytest

def test_something():
    """Test description"""
    assert True
```

### Example Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await some_async_function()
    assert result is not None
```

### Example Integration Test

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_api_integration():
    """Test API integration"""
    # Test code here
    pass
```

## 🎯 CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=app
```

## 📚 Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)