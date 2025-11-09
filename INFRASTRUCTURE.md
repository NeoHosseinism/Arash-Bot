# Infrastructure Components - Status

This document clarifies which infrastructure components are **actually running** vs **dead code** in documentation.

---

## ✅ RUNNING (Active Components)

### 1. **Python Application Container**
- **Status**: ✅ Running
- **Image**: `repo3.lucidfirm.ir/primebot/arash-external-api`
- **Port**: 3000
- **Health Check**:
  - Endpoint: `GET /health`
  - Liveness Probe: Every 30s
  - Readiness Probe: Every 10s
- **Components**:
  - FastAPI application
  - Integrated Telegram bot (runs in same container)
  - Session management (in-memory)

### 2. **Nginx Ingress Controller**
- **Status**: ✅ Running (Kubernetes Infrastructure)
- **Purpose**: Routes external traffic to application
- **Configuration**: `manifests/*/ingress.yaml`
- **Hosts**:
  - Dev: `arash-api-dev.irisaprime.ir`
  - Stage: `arash-api-stage.irisaprime.ir`
  - Prod: `arash-api.irisaprime.ir`

### 3. **PostgreSQL Database**
- **Status**: ✅ Running (External Service)
- **Purpose**: Stores teams, API keys, usage logs
- **NOT Stored**: Chat history (handled by AI service)
- **Access**: Via environment variables (DB_HOST, DB_PORT, etc.)

### 4. **AI Service**
- **Status**: ✅ Running (External Service)
- **URL**: Configured via `AI_SERVICE_URL` environment variable
- **Purpose**: Processes chat messages with various AI models

---

## ❌ NOT RUNNING (Dead Code / Planned but Not Implemented)

### 1. **Prometheus**
- **Status**: ❌ NOT running
- **Why**: Mentioned in old docs, never implemented
- **Alternative**: Use Kubernetes metrics-server or add later

### 2. **Grafana**
- **Status**: ❌ NOT running
- **Why**: Mentioned in old docs, never implemented
- **Alternative**: Use Kubernetes dashboard or add later

### 3. **Flower**
- **Status**: ❌ NOT running (Not Applicable)
- **Why**: Flower is for Celery monitoring
- **Reality**: This project doesn't use Celery or any async task queue
- **Async Handling**: Uses FastAPI's native async/await (no separate worker needed)

### 4. **Redis**
- **Status**: ❌ NOT running (Optional)
- **Config**: `REDIS_URL` environment variable (currently empty)
- **Current**: Sessions are in-memory
- **Future**: Can add Redis for distributed session storage

### 5. **Docker Compose**
- **Status**: ❌ No docker-compose.yml
- **Deployment**: Kubernetes-only (no local multi-container setup)
- **Local Dev**: Run Python app directly via `make run`

---

## Health Check Details

### Kubernetes Health Probes

**Liveness Probe** (Is container alive?):
```yaml
httpGet:
  path: /health
  port: 3000
initialDelaySeconds: 40
periodSeconds: 30
timeoutSeconds: 10
failureThreshold: 3
```

**Readiness Probe** (Can container receive traffic?):
```yaml
httpGet:
  path: /health
  port: 3000
initialDelaySeconds: 10
periodSeconds: 10
timeoutSeconds: 5
failureThreshold: 3
```

### Docker Healthcheck
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/health').read()" || exit 1
```

---

## Architecture Summary

```
┌─────────────────────────────────────────────────┐
│            Internet / Users                      │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│      Nginx Ingress Controller (K8s)             │
│      (Routes traffic based on host/path)        │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│   Arash Bot Container (Single Container)        │
│   ┌───────────────────────────────────────┐    │
│   │  FastAPI App + Telegram Bot           │    │
│   │  Port: 3000                            │    │
│   │  Health: /health                       │    │
│   └───────────────────────────────────────┘    │
└─────────────┬──────────────┬────────────────────┘
              │              │
              ▼              ▼
    ┌─────────────┐   ┌─────────────┐
    │ PostgreSQL  │   │ AI Service  │
    │ (External)  │   │ (External)  │
    └─────────────┘   └─────────────┘
```

---

## Future Additions (If Needed)

### Monitoring Stack (Optional)
If you want to add Prometheus + Grafana later:

1. **Prometheus** - Metrics collection
   - Scrape `/metrics` endpoint (need to add)
   - Store time-series data

2. **Grafana** - Visualization
   - Dashboard for API metrics
   - Team usage visualization

### Task Queue (Not Needed Currently)
If you add long-running background tasks later:

1. **Celery** - Distributed task queue
2. **Flower** - Celery monitoring UI
3. **Redis/RabbitMQ** - Message broker

**Current Status**: Not needed, FastAPI async is sufficient

---

## How to Verify What's Running

### Kubernetes
```bash
# Check pods
kubectl get pods -n arash

# Check services
kubectl get svc -n arash

# Check ingress
kubectl get ingress -n arash

# Check health
curl https://arash-api-dev.irisaprime.ir/health
```

### Docker
```bash
# Build and check health
docker build -t arash-bot .
docker run -p 3000:3000 arash-bot

# Check health
curl http://localhost:3000/health
```

---

## Environment Variables Reference

**Running Services:**
- `AI_SERVICE_URL` - AI service endpoint (required)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - PostgreSQL (required)
- `TELEGRAM_BOT_TOKEN` - Telegram bot (required if RUN_TELEGRAM_BOT=true)
- `SUPER_ADMIN_API_KEYS` - Super admin access (required for admin endpoints)

**Not Used (Optional/Future):**
- `REDIS_URL` - Redis (optional, not currently used)
- Prometheus/Grafana configs - Not implemented
- Flower configs - Not applicable

---

**Last Updated**: 2025-01-09
**Deployment**: Kubernetes (dev, stage, prod)
**Single Container**: FastAPI + Telegram Bot
