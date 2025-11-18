# Hotfix: Migration Conflict Resolution

**Date:** January 17, 2025
**Severity:** 🔴 Critical - Blocks Production Deployment
**Status:** ✅ Fixed - Ready for Deployment

---

## Problem

**Container startup was failing** in production with the following error:

```
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head';
please specify a specific target revision, '<branchname>@head' to narrow to a specific head,
or 'heads' for all heads
```

### Root Cause

Two parallel migration branches existed in Alembic:

```
          71521c6321dc (webhook fields)
                 |
        +--------+--------+
        |                 |
        v                 v
  6f4dbeea5805      a1b2c3d4e5f6
  (access levels)   (platform config - NEW)
        |
        v
  121e13619297
  (simplify schema)
        |
        v
  db8a923de76e
  (messages table)
        |
        v
  850df83abd23
  (rename team_name)
  [HEAD 1]
```

**Result:** Alembic found TWO heads (`850df83abd23` and `a1b2c3d4e5f6`) and refused to proceed.

---

## Solution

Created **merge migration** `f709960167e7` that combines both heads:

```python
# f709960167e7_merge_platform_config_with_existing_.py
revision = 'f709960167e7'
down_revision = ('850df83abd23', 'a1b2c3d4e5f6')  # ← Tuple of both heads

def upgrade() -> None:
    pass  # No schema changes, just merges branches

def downgrade() -> None:
    pass
```

### New Migration Chain

```
  850df83abd23 (existing) ──┐
                            ├─→ f709960167e7 (merge) → HEAD
  a1b2c3d4e5f6 (new)     ───┘
```

**Result:** Single HEAD, migration chain unified.

---

## Verification

```bash
# Before fix:
$ alembic heads
850df83abd23 (head)
a1b2c3d4e5f6 (head)  # ← TWO HEADS!

# After fix:
$ alembic heads
f709960167e7 (head)  # ← SINGLE HEAD ✅
```

---

## Deployment Steps (Hotfix to Main)

### 1. Merge to Main

```bash
# Switch to main
git checkout main
git pull origin main

# Merge the fix
git merge claude/general-session-01AN2RJrvKs2J5xLUvBsnA43

# Push to main (triggers CI/CD)
git push origin main
```

### 2. CI/CD Automatic Process

Your CI/CD pipeline will:
1. ✅ Build Docker container
2. ✅ Container starts successfully (no migration error)
3. ✅ Auto-run `alembic upgrade head` (single head exists)
4. ✅ Apply migrations in order:
   - If production is at `850df83abd23`: applies `a1b2c3d4e5f6` → `f709960167e7`
   - If production is at `71521c6321dc`: applies both branches → `f709960167e7`
5. ✅ Service starts normally

### 3. Verify Deployment

After CI/CD completes:

```bash
# Check container logs (should NOT see migration error)
docker logs <container-id> | grep -i "migration"

# Should see:
# [info] Running migrations...
# [info] Database migrations completed successfully
# [info] Starting Arash External API Service

# Verify application is running
curl http://your-production-url/health
```

---

## What This Fixes

✅ **Container Startup** - No more migration errors
✅ **Auto-Migration** - `alembic upgrade head` works correctly
✅ **Platform Config** - New columns added to `teams` table
✅ **CI/CD Pipeline** - Deployment proceeds automatically
✅ **Zero Manual DB Work** - No need to access production database

---

## Migration Details

### Production Database Changes

When the merge migration runs, these changes will be applied:

**From `a1b2c3d4e5f6` (Platform Config Migration):**
```sql
-- Add platform configuration columns to teams table
ALTER TABLE teams ADD COLUMN platform_type VARCHAR(50) NOT NULL DEFAULT 'private';
ALTER TABLE teams ADD COLUMN rate_limit INTEGER;
ALTER TABLE teams ADD COLUMN max_history INTEGER;
ALTER TABLE teams ADD COLUMN default_model VARCHAR(255);
ALTER TABLE teams ADD COLUMN available_models TEXT;
ALTER TABLE teams ADD COLUMN allow_model_switch BOOLEAN;

-- Create index
CREATE INDEX ix_teams_platform_type ON teams(platform_type);
```

**From `f709960167e7` (Merge Migration):**
```sql
-- No schema changes, just records the merge in alembic_version
```

### Database State After Deployment

```sql
-- Production database will have:
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'teams';

-- Result:
id                   | integer
display_name         | varchar(255)
platform_name        | varchar(255)
platform_type        | varchar(50)      ← NEW
monthly_quota        | integer
daily_quota          | integer
is_active            | boolean
rate_limit           | integer          ← NEW
max_history          | integer          ← NEW
default_model        | varchar(255)     ← NEW
available_models     | text             ← NEW
allow_model_switch   | boolean          ← NEW
created_at           | timestamp
updated_at           | timestamp
```

---

## Rollback Plan

If issues occur after deployment:

### Option 1: Rollback Container (Recommended)

```bash
# CI/CD should have previous container version
# Rollback to previous deployment
kubectl rollout undo deployment/arash-bot -n production

# OR via your CI/CD pipeline:
# Redeploy previous git commit
git revert HEAD
git push origin main
```

### Option 2: Rollback Migration (Manual - Last Resort)

**Only if you have DB access:**

```bash
# Connect to production container
kubectl exec -it arash-bot-xxx -- /bin/bash

# Rollback one migration
alembic downgrade -1

# Restart container
```

---

## Timeline

- **18:52 (IR Time):** Production deployment failed with migration error
- **18:53:** Identified two heads: `850df83abd23` and `a1b2c3d4e5f6`
- **18:55:** Created merge migration `f709960167e7`
- **18:56:** Verified single head, committed and pushed fix
- **NOW:** Ready for hotfix deployment to main

---

## Commits Included in Hotfix

1. **5f79665** - ✨ Implement database-driven platform configuration (Option 1)
2. **0a59421** - 🔧 Fix: Add merge migration to resolve multiple heads

---

## Post-Deployment Testing

After successful deployment:

### 1. Verify Platform Config Works

```bash
# Create team with custom config
curl -X POST https://your-production-url/admin/teams \
  -H "Authorization: Bearer YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "platform_name": "Test-Platform",
    "platform_type": "private",
    "rate_limit": 50
  }'

# Should succeed without errors
```

### 2. Verify No Warnings

Check logs for HOSCO-Popak and HOSCO-Avand - should NOT see:
```
[warn] Unknown platform: HOSCO-Popak
```

### 3. Verify Existing Teams Work

```bash
# Test existing team API calls
curl -X POST https://your-production-url/chat \
  -H "Authorization: Bearer EXISTING_TEAM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "text": "Hello"
  }'

# Should work normally
```

---

## Summary

🔴 **Problem:** Multiple migration heads blocked container startup
🔧 **Fix:** Created merge migration to unify branches
✅ **Status:** Ready for hotfix deployment to main
🚀 **Impact:** Zero downtime, auto-migration, no manual DB work

**Next Step:** Merge to main and let CI/CD deploy automatically.
