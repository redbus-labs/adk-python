# Quick Start Guide - Postgres App Server

## ✅ Setup Complete!

Your virtual environment is now created and dependencies are installed.

## Run the Server

### Step 1: Activate Virtual Environment
```bash
source .venv/bin/activate
```

### Step 2: Set Environment Variables (if using RedbusADG)
```bash
export ADURL="https://your-api-gateway-url.com"
export ADU="your-username"
export ADP="your-password"
export REDBUS_ADG_MODEL="40"  # Optional
```

### Step 3: Run the Server
```bash
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://postgres:postgres@localhost:5432/adk_db"
```

**Replace with your actual PostgreSQL connection string:**
- Format: `postgresql://username:password@host:port/database`
- Example: `postgresql://postgres:mypassword@localhost:5432/adk_db`

## Test the Server

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

## Debugging with VS Code

1. Press `F5` or select "Python: Postgres App Server" from the debug dropdown
2. Set breakpoints in your code
3. The server will start and you can debug

## Common Issues

### PostgreSQL Connection Error
- Make sure PostgreSQL is running: `psql -U postgres -h localhost`
- Create database if needed: `psql -U postgres -c "CREATE DATABASE adk_db;"`
- Check connection string format

### RedbusADG Environment Variables
- Set `ADURL`, `ADU`, and `ADP` environment variables
- Or modify `generic_orchestrator.py` to use a different model

### Module Not Found
- Make sure virtual environment is activated: `source .venv/bin/activate`
- Verify installation: `pip list | grep google-adk`

## Next Steps

1. **Test PostgreSQL connection** - Make sure your database is accessible
2. **Set up RedbusADG** - Configure API gateway credentials
3. **Create database tables** - The tables will be created automatically on first use
4. **Test the API** - Use the curl commands above

