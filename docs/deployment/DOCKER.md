# Docker Deployment Guide

Complete guide for deploying Arash External API Service using Docker and Docker Compose.

## Quick Start

### 1. Prerequisites

```bash
# Install Docker
docker --version  # Should be 20.10+

# Install Docker Compose
docker-compose --version  # Should be 2.0+
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
nano .env

# Set PostgreSQL password (required)
export POSTGRES_PASSWORD="your_strong_password_here"
```

**Required Environment Variables:**
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `INTERNAL_API_KEY`: Secure random key (min 32 characters)
- `AI_SERVICE_URL`: Your AI service endpoint

### 3. Start Services

```bash
# Start API service with PostgreSQL
docker-compose up -d

# Or start with Telegram bot
docker-compose --profile telegram up -d

# View logs
docker-compose logs -f api

# Check status
docker-compose ps
```

### 4. Initialize Database

Database initialization runs automatically via the `db-init` service.

**Manual initialization (if needed):**
```bash
docker-compose run --rm api python scripts/manage_api_keys.py init
```

### 5. Create First Team and API Key

```bash
# Create team
docker-compose exec api python scripts/manage_api_keys.py team create "Engineering" \
    --description "Main engineering team" \
    --monthly-quota 50000

# Create admin API key
docker-compose exec api python scripts/manage_api_keys.py key create 1 "Admin Key" \
    --level admin \
    --description "Administrator access"

# Save the generated key!
```

## Service URLs

Once running:
- **API Service**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **PostgreSQL**: localhost:5432

## Docker Compose Services

### Core Services

**1. postgres**
- PostgreSQL 15 Alpine
- Data persisted in `postgres_data` volume
- Health checks enabled
- Port: 5432

**2. db-init**
- One-time database initialization
- Creates tables if they don't exist
- Skips if tables already exist
- Runs before API starts

**3. api**
- Main FastAPI service
- Depends on healthy PostgreSQL
- Logs mapped to `./logs`
- Port: 8001

### Optional Services

**4. telegram-bot**
- Telegram bot handler
- Requires `--profile telegram` to start
- Depends on healthy API service

## Common Commands

### Start/Stop

```bash
# Start all services
docker-compose up -d

# Start with Telegram bot
docker-compose --profile telegram up -d

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database!)
docker-compose down -v
```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f api
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 api
```

### Database Management

```bash
# Create team
docker-compose exec api python scripts/manage_api_keys.py team create "TeamName"

# List teams
docker-compose exec api python scripts/manage_api_keys.py team list

# Create API key
docker-compose exec api python scripts/manage_api_keys.py key create 1 "KeyName" --level admin

# View usage
docker-compose exec api python scripts/manage_api_keys.py usage --team-id 1

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d arash_api

# Backup database
docker-compose exec postgres pg_dump -U postgres arash_api > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres arash_api < backup.sql
```

### Health Checks

```bash
# Check service health
docker-compose ps

# Test API health
curl http://localhost:8001/health

# Test database connection
docker-compose exec api python -c "from app.models.database import get_database; db = get_database(); print('OK' if db.test_connection() else 'FAILED')"
```

### Rebuilding

```bash
# Rebuild after code changes
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Rebuild and restart
docker-compose up -d --build
```

## Production Deployment

### Security Checklist

- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Generate secure `INTERNAL_API_KEY` (32+ chars)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `ENABLE_API_DOCS=false`
- [ ] Configure `CORS_ORIGINS` (don't use `*`)
- [ ] Use secrets management (Docker Swarm secrets or Kubernetes secrets)
- [ ] Enable SSL/TLS with reverse proxy
- [ ] Regular database backups
- [ ] Monitor logs and metrics

### Reverse Proxy (nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Resource Limits

Add to docker-compose.yml under each service:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

### Persistent Logs

Logs are stored in `./logs` directory:

```bash
# View logs
tail -f logs/arash_api_service.log

# Search for errors
grep ERROR logs/arash_api_service.log

# Rotate logs (add to crontab)
find logs/ -name "*.log" -mtime +30 -delete
```

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8001
lsof -i :8001
netstat -tulpn | grep 8001

# Change port in docker-compose.yml or use environment variable
export API_PORT=8002
docker-compose up -d
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U postgres -d arash_api -c "SELECT 1;"
```

### Container Keeps Restarting

```bash
# Check logs
docker-compose logs api

# Check health
docker-compose ps

# Run in foreground for debugging
docker-compose up api
```

### Out of Disk Space

```bash
# Clean up unused images
docker system prune -a

# Remove old volumes
docker volume prune

# Check disk usage
docker system df
```

## Updates and Migrations

### Updating the Application

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build

# Stop services
docker-compose down

# Start with new version
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### Database Migrations

Database schema changes are handled automatically. The initialization script:
- Detects existing tables
- Creates missing tables
- Skips tables that already exist

**Expected output:**
```
[INFO] Found existing tables in database: api_keys, teams, usage_logs
[OK] Skipped existing tables: api_keys, teams, usage_logs
[OK] All required tables already exist in database
[OK] Database schema is ready
```

## Monitoring

### Health Endpoints

```bash
# API health
curl http://localhost:8001/health

# Platform info
curl http://localhost:8001/

# Statistics
curl http://localhost:8001/stats
```

### Database Monitoring

```bash
# Connection count
docker-compose exec postgres psql -U postgres -d arash_api -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
docker-compose exec postgres psql -U postgres -d arash_api -c "SELECT pg_size_pretty(pg_database_size('arash_api'));"

# Table sizes
docker-compose exec postgres psql -U postgres -d arash_api -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables WHERE schemaname='public';"
```

## Advanced Configuration

### Custom Network

```yaml
networks:
  arash-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### External PostgreSQL

If using external PostgreSQL, remove `postgres` service and set database parameters:

```yaml
services:
  api:
    environment:
      DB_HOST: external-host
      DB_PORT: 5432
      DB_USER: user
      DB_PASSWORD: pass
      DB_NAME: dbname
```

### Multiple Environments

```bash
# Development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify environment: `docker-compose config`
3. Test connectivity: Health check endpoints
4. Review [README.md](README.md) for configuration details
