# How to Run the ADK App Server

## Correct Way to Run

### Method 1: Using Python Module (Recommended)
```bash
python -m google.adk.server.app_server 8080
```

This is the correct way and will:
- Initialize the agent
- Set up the runner
- Register routes
- Start the server

### Method 2: Using Python Directly
```bash
python src/google/adk/server/app_server.py 8080
```

Or from the project root:
```bash
cd /Users/arun.parmar/go/src/adk-python
PYTHONPATH=src python -m google.adk.server.app_server 8080
```

## Common Errors

### Error: "Could not import module 'main'"

**Cause**: You're trying to run:
```bash
uvicorn main:app  # ❌ Wrong - "main" module doesn't exist
```

**Solution**: Use the Python module method instead:
```bash
python -m google.adk.server.app_server 8080  # ✅ Correct
```

### Why uvicorn main:app doesn't work

The routes are registered inside the `main()` function, which means:
- The `app` variable exists at module level
- But routes are only added when `main()` is called
- Running `uvicorn` directly skips the initialization

## Using VS Code Debugger

1. Press `F5`
2. Select "Python: App Server"
3. Server will start in debug mode

## Environment Variables

Make sure these are set (if not using config.ini):
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export ADURL="..."
export ADU="..."
export ADP="..."
export REDBUS_ADG_MODEL="40"
```

## Testing the Server

Once running, test with:
```bash
# Health check
curl http://localhost:8080/health

# Chat endpoint
curl --location 'http://localhost:8080/chat' \
--header 'BUSINESS_UNIT: BUS' \
--header 'COUNTRY: IND' \
--header 'Content-Type: application/json' \
--header 'X-CLIENT: SELF_HELP' \
--data '{"message": "Hi", "orderItemUUID": "8dc29a95411be00600ec264701020100"}'
```

## Troubleshooting

1. **Port already in use**: Change port or kill existing process
   ```bash
   lsof -ti:8080 | xargs kill -9
   ```

2. **Database connection error**: Check `config.ini` or environment variables

3. **Module not found**: Make sure you're in the project root and PYTHONPATH is set
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   ```

