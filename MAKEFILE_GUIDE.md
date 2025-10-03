# Makefile Usage Guide

Complete guide for using the Makefile to manage the Arash Messenger Bot project.

## 📋 Quick Reference

```bash
make help              # Show all available commands
make install           # Complete installation
make run-all          # Run both services
make test             # Run tests
make docker-up        # Start with Docker
```

---

## 🚀 Getting Started

### First Time Setup

```bash
# 1. Install everything
make install

# 2. Create environment file
make env

# 3. Edit .env with your tokens
nano .env

# 4. Run services
make run-all
```

---

## 🔧 Development Workflow

### Daily Development

```bash
# Start development
make run-all           # Starts both services in tmux

# In another terminal:
make logs             # Watch logs in real-time
make stats            # Check service statistics
```

### Code Quality

```bash
# Before committing:
make check            # Run all checks (format, lint, security)

# Or individually:
make format           # Format code with black
make lint             # Lint with flake8 and mypy
make security         # Security checks with bandit
```

### Testing

```bash
make test             # Run all tests
make test-cov         # Run tests with coverage report
make test-watch       # Run tests in watch mode (continuous)
```

---

## 🐳 Docker Workflow

### Using Docker

```bash
# Build images
make docker-build

# Start services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

### Docker Commands Explained

- `docker-build`: Builds both API and Bot Docker images
- `docker-up`: Starts services in detached mode
- `docker-down`: Stops and removes containers
- `docker-logs`: Shows real-time logs from all containers

---

## 🏃 Running Services

### Method 1: Makefile (Recommended)

```bash
# Run both services (requires tmux or screen)
make run-all

# Or run individually in separate terminals:
# Terminal 1:
make run-service

# Terminal 2:
make run-bot
```

### Method 2: Direct Python

```bash
# Activate venv first
source venv/bin/activate

# Run services
python run_service.py
python run_bot.py
```

### Method 3: Systemd (Production)

```bash
# Install services
make install-service

# Start services
make service-start

# Check status
make service-status

# Stop services
make service-stop
```

---

## 🧹 Maintenance

### Cleaning

```bash
make clean            # Clean cache and temp files
make clean-all        # Deep clean (includes venv)
```

### Backup

```bash
make backup           # Create timestamped backup
```

### Updates

```bash
make upgrade          # Show outdated packages
make requirements     # Update requirements.txt
```

---

## 📊 Monitoring

### View Logs

```bash
# Application logs
make logs

# Systemd logs (if using systemd)
sudo journalctl -u arash-bot-api -f
sudo journalctl -u arash-bot-telegram -f
```

### Statistics

```bash
make stats            # Show service statistics (calls /stats endpoint)
```

### Service Status

```bash
make info             # Show project information
make service-status   # Show systemd service status
```

---

## 🚢 Deployment

### Pre-Deployment

```bash
# Run all checks before deploying
make deploy-check

# This checks:
# - Environment file exists
# - Required variables set
# - Tests pass
# - Security scan
```

### Deploy to Production

```bash
# Full deployment (customize for your needs)
make deploy

# Or manual steps:
make install
make env              # Then edit .env
make deploy-check
make docker-up        # or make install-service
```

---

## 💡 Tips & Tricks

### Using tmux (for run-all)

```bash
# Install tmux
sudo apt install tmux

# Run services
make run-all

# Detach from tmux: Ctrl+B, then D
# Reattach: tmux attach -t arash-bot
# Kill session: tmux kill-session -t arash-bot
```

### Using screen (alternative)

```bash
# Install screen
sudo apt install screen

# Run services
make run-all

# List screens
screen -ls

# Attach to screen
screen -r arash-service
screen -r arash-bot

# Detach from screen: Ctrl+A, then D
```

### Development Iteration

```bash
# Typical development cycle:
1. make run-all              # Start services
2. Edit code
3. make stop                 # Stop services
4. make test                 # Run tests
5. make format               # Format code
6. make run-all              # Restart services
```

### Quick Restart

```bash
# Stop and restart services
make stop && make run-all
```

### Debugging

```bash
# Run service in foreground (not background)
python run_service.py

# Check if services are running
ps aux | grep run_service
ps aux | grep run_bot

# Check ports
lsof -i :8001  # API service port
```

---

## 📝 Common Scenarios

### Scenario 1: Fresh Installation

```bash
git clone <repo-url>
cd arash-messenger-bot
make install
make env
# Edit .env with your tokens
nano .env
make run-all
```

### Scenario 2: After Pulling Changes

```bash
git pull
make install          # Reinstall dependencies
make test            # Ensure tests pass
make stop            # Stop old services
make run-all         # Start updated services
```

### Scenario 3: Running Tests Before Commit

```bash
make check           # Format, lint, security
make test-cov        # Tests with coverage
git add .
git commit -m "Your message"
```

### Scenario 4: Production Deployment

```bash
# On production server:
git clone <repo-url>
cd arash-messenger-bot
make install
make env
# Edit .env for production
nano .env
make deploy-check
make install-service
make service-start
make service-status
```

### Scenario 5: Troubleshooting Issues

```bash
# Check service status
make info
make stats

# View logs
make logs

# Stop everything and clean
make stop
make clean

# Restart fresh
make run-all
```

---

## 🔐 Security Best Practices

### Before Deployment

```bash
# Always run security checks
make security

# Verify environment
grep -i "production" .env

# Ensure API docs are disabled in production
grep "ENABLE_API_DOCS=false" .env
```

### Regular Maintenance

```bash
# Weekly: Check for updates
make upgrade

# Monthly: Run full security audit
make security
make test
```

---

## 🐛 Troubleshooting

### "Command not found: make"

```bash
# Install make on Ubuntu/Debian
sudo apt install make

# Install on macOS
xcode-select --install

# Install on Windows (WSL recommended)
sudo apt install make
```

### "tmux not found"

```bash
# Install tmux
sudo apt install tmux

# Or use screen instead
sudo apt install screen
```

### "Permission denied"

```bash
# Fix script permissions
chmod +x setup.sh

# Fix Makefile permissions
chmod +x Makefile
```

### Services Won't Start

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check if venv is activated
which python  # Should show venv path

# Check if port is in use
lsof -i :8001

# Check logs
make logs
```

### Tests Failing

```bash
# Install test dependencies
make dev

# Run tests with verbose output
source venv/bin/activate
pytest tests/ -v -s

# Clear cache and retry
make clean
make test
```

---

## 📦 Makefile Variables

You can customize these in the Makefile:

```makefile
PYTHON := python3          # Python executable
VENV := venv              # Virtual environment directory
API_PORT := 8001          # API service port
```

---

## 🎯 Advanced Usage

### Running Specific Tests

```bash
# Run specific test file
source venv/bin/activate
pytest tests/test_api.py -v

# Run specific test function
pytest tests/test_api.py::test_health_check -v
```

### Custom Docker Build

```bash
# Build specific service
docker-compose build api
docker-compose build bot

# Build with no cache
docker-compose build --no-cache
```

### Manual Service Management

```bash
# Start only API service
docker-compose up -d api

# Start only Bot service
docker-compose up -d bot

# Scale services (if needed)
docker-compose up -d --scale bot=2
```

### Environment-Specific Commands

```bash
# Development
ENVIRONMENT=development make run-all

# Staging
ENVIRONMENT=staging make run-all

# Production
ENVIRONMENT=production make deploy
```

---

## 📚 Additional Resources

### Makefile Help

```bash
# Show all commands with descriptions
make help

# Show specific command usage
make help | grep docker
```

### Service Endpoints

- API Docs: `http://localhost:8001/docs`
- Health Check: `http://localhost:8001/health`
- Statistics: `http://localhost:8001/stats`
- Platforms Info: `http://localhost:8001/platforms`

### Log Files

- Application: `logs/bot_service.log`
- Systemd API: `/var/log/arash-bot/api.log`
- Systemd Bot: `/var/log/arash-bot/telegram.log`
- Docker: `docker-compose logs`

---

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test

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
        run: make install
      - name: Run checks
        run: make check
      - name: Run tests
        run: make test-cov
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
test:
  image: python:3.11
  script:
    - make install
    - make check
    - make test-cov
```

---

## ⚡ Performance Tips

### Faster Development

```bash
# Use test watch mode for continuous testing
make test-watch

# Run only failed tests
pytest --lf

# Run tests in parallel
pytest -n auto
```

### Docker Optimization

```bash
# Use Docker BuildKit for faster builds
DOCKER_BUILDKIT=1 docker-compose build

# Prune unused images
docker system prune -a
```

---

## 📞 Getting Help

If you encounter issues:

1. Check this guide
2. Run `make help`
3. Check logs with `make logs`
4. Review `README.md`
5. Check service status with `make info`

---

**Happy Coding! 🚀**