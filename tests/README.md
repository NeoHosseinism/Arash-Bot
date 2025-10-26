# Tests

Test suite for Arash Messenger Bot.

## 📁 Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_ai_service.py       # AI service integration tests
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
# Run only AI service tests
pytest tests/test_ai_service.py

# Run only fast tests (skip slow ones)
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run specific test class
pytest tests/test_ai_service.py::TestAIServiceConnectivity

# Run specific test method
pytest tests/test_ai_service.py::TestAIServiceConnectivity::test_base_url_reachable
```

### Manual Test (No pytest required)

```bash
# Run AI service connectivity test directly
python tests/test_ai_service.py
```

This will run a detailed diagnostic test showing:
- Connection status
- Health check results
- Chat endpoint functionality
- Detailed error messages

## 🏷️ Test Markers

Tests are categorized using pytest markers:

- `@pytest.mark.slow` - Slow tests (network calls, etc.)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.ai_service` - Tests requiring AI service

### Examples

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run everything except AI service tests
pytest -m "not ai_service"
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

## 🔧 AI Service Tests

The `test_ai_service.py` file includes:

### Test Classes

1. **TestAIServiceConnectivity**
   - Tests basic connectivity
   - Health endpoint check
   - Chat endpoint format validation

2. **TestAIServiceClient**
   - Tests client initialization
   - Health check method
   - Chat request sending

3. **TestAIServiceConfiguration**
   - Validates configuration
   - URL format checks
   - Model configuration

### Manual Diagnostic Test

```bash
python tests/test_ai_service.py
```

Output includes:
```
======================================================================
                AI Service Connectivity Test
======================================================================

Service URL: https://your-ai-service-url.com
Telegram Model: Gemini 2.0 Flash
Internal Models: 11

----------------------------------------------------------------------

1. Testing Base URL Connectivity...
   [OK] Status: 200
   Response: ...

2. Testing Health Endpoint...
   [OK] Status: 200
   Response: ...

3. Testing Chat Endpoint...
   [OK] Status: 200
   Response: ...

4. Testing Client Health Check Method...
   [OK] Service is healthy

======================================================================
                              Test Complete
======================================================================
```

## 🐛 Troubleshooting

### Tests Fail with Connection Error

```bash
# Check if AI service URL is correct
grep AI_SERVICE_URL .env

# Test connectivity manually
curl -v https://your-ai-service-url.com/health

# Run diagnostic
python tests/test_ai_service.py
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