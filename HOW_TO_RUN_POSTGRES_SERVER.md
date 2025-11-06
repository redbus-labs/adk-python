# How to Run and Debug Postgres App Server

## Prerequisites

1. **PostgreSQL Database** - Make sure PostgreSQL is running and accessible
2. **Environment Variables** (for RedbusADG):
   - `ADURL` - API gateway URL
   - `ADU` - Username
   - `ADP` - Password
   - `REDBUS_ADG_MODEL` - Model ID (optional, defaults to "40")

## Method 1: Run as Python Script (Recommended for Debugging)

This is the easiest way to run and debug the server:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run directly (uses main() function)
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://user:password@localhost:5432/dbname"
```

**Example with full PostgreSQL connection string:**
```bash
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://postgres:postgres@localhost:5432/adk_db"
```

## Method 2: Run with Uvicorn (Production-like)

If you want to use uvicorn directly, you need to use the correct module path:

```bash
# Correct way - use the full module path
uvicorn google.adk.server.postgres_app_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload

# But note: This won't initialize the runner!
# The runner is initialized in main(), not at module level.
# So this method won't work properly.
```

**⚠️ Important:** Method 2 won't work because `runner` is initialized in `main()`, not at module import time. Use Method 1 instead.

## Method 3: Using Python -m (Alternative)

```bash
cd /Users/arun.parmar/go/src/adk-python
python3 -m google.adk.server.postgres_app_server --port 8000 --db-url "postgresql://..."
```

## Setting Up Environment Variables

Create a `.env` file or export variables:

```bash
# For RedbusADG model
export ADURL="https://your-api-gateway-url.com"
export ADU="your-username"
export ADP="your-password"
export REDBUS_ADG_MODEL="40"  # Optional, defaults to "40"

# PostgreSQL (if not using --db-url flag)
export POSTGRES_URL="postgresql://user:password@localhost:5432/dbname"
```

Or create a startup script:

```bash
#!/bin/bash
# run_server.sh

export ADURL="https://your-api-gateway-url.com"
export ADU="your-username"
export ADP="your-password"
export REDBUS_ADG_MODEL="40"

source .venv/bin/activate

python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://postgres:postgres@localhost:5432/adk_db"
```

## Debugging with VS Code

Create or update `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Postgres App Server",
      "type": "debugpy",
      "request": "launch",
      "module": "google.adk.server.postgres_app_server",
      "args": [
        "--port", "8000",
        "--db-url", "postgresql://postgres:postgres@localhost:5432/adk_db"
      ],
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "ADURL": "https://your-api-gateway-url.com",
        "ADU": "your-username",
        "ADP": "your-password",
        "REDBUS_ADG_MODEL": "40"
      }
    }
  ]
}
```

## Testing the Server

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok"}
```

### 2. Test Chat Endpoint
```bash
curl --location 'http://localhost:8000/chat' \
  --header 'BUSINESS_UNIT: BUS' \
  --header 'COUNTRY: IND' \
  --header 'Content-Type: application/json' \
  --header 'X-CLIENT: SELF_HELP' \
  --data '{
    "message": "Hi",
    "orderItemUUID": "8dc29a95411be00600ec264701020100"
}'
```

### 3. Using the Test Script
```bash
# Make test script executable
chmod +x test_curl_example.sh

# Run test
./test_curl_example.sh
```

Or use the Python test script:
```bash
python test_postgres_api.py http://localhost:8000 "Hello, how are you?"
```

## Common Issues and Solutions

### Issue 1: "Could not import module 'main'"
**Error:** `Error loading ASGI app. Could not import module "main".`

**Solution:** Don't use `uvicorn main:app`. Use Method 1 instead:
```bash
python -m google.adk.server.postgres_app_server --port 8000 --db-url "..."
```

### Issue 2: "Runner not initialized"
**Error:** `HTTPException(status_code=500, detail='Runner not initialized')`

**Solution:** Make sure you're running via `main()`, not directly with uvicorn. The runner is initialized in `main()`.

### Issue 3: PostgreSQL Connection Error
**Error:** `Failed to initialize PostgresRunner: ...`

**Solutions:**
- Check PostgreSQL is running: `psql -U postgres -h localhost`
- Verify connection string format: `postgresql://user:password@host:port/dbname`
- Check database exists: `psql -U postgres -c "CREATE DATABASE adk_db;"`

### Issue 4: RedbusADG Environment Variables Missing
**Error:** `RuntimeError: Environment variable 'ADURL' not set.`

**Solution:** Set the required environment variables:
```bash
export ADURL="https://your-api-url.com"
export ADU="username"
export ADP="password"
```

## Enabling Debug Logging

Add logging configuration to see more details:

```python
# In postgres_app_server.py, add at the top of main():
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Or set via environment:
```bash
export PYTHONPATH=/Users/arun.parmar/go/src/adk-python/src
export LOG_LEVEL=DEBUG
```

## Quick Start Command

```bash
# One-liner to run with all settings
ADURL="https://api-url.com" \
ADU="username" \
ADP="password" \
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://postgres:postgres@localhost:5432/adk_db"
```

## Verifying It's Working

1. **Check server starts:**
   ```bash
   # Should see: "Starting server on port 8000"
   # And: "PostgresRunner initialized successfully."
   ```

2. **Test health endpoint:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test chat endpoint:**
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Hi"}'
   ```

4. **Check logs for:**
   - Agent initialization
   - Session creation
   - Event generation
   - Database operations

