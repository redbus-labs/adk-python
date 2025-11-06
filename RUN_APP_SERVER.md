# Running the ADK App Server

## Overview

The `app_server.py` is a production-ready server that matches the Java `AppServer.java` implementation with:
- Multiple runner support (PostgresRunner, InMemoryRunner)
- Automatic fallback to InMemoryRunner if database connection fails
- Fast startup (doesn't block on DB connection)
- Config file support (INI format)
- Separate handler file for request processing

## Quick Start

### Method 1: Using Config File (Recommended)

```bash
# 1. Create config.ini file
cp config.ini.example config.ini
# Edit config.ini with your database URL

# 2. Run server
python -m google.adk.server.app_server [port] [config_path] [environment]
```

**Examples:**
```bash
# Default (port 8000, default config path, production)
python -m google.adk.server.app_server

# Custom port
python -m google.adk.server.app_server 8080

# Custom port and config file
python -m google.adk.server.app_server 8080 /path/to/config.ini

# Custom port, config, and environment
python -m google.adk.server.app_server 8080 /path/to/config.ini development
```

### Method 2: Using Environment Variables

```bash
# Set database URL
export DATABASE_URL="postgresql://username:password@hostname:5432/database"

# Run server
python -m google.adk.server.app_server
```

## Config File Format

Create `config.ini`:

```ini
[default]
runner_type = postgres
database_url = postgresql://postgres:postgres@localhost:5432/adk_db

[production]
database_url = postgresql://username:password@hostname:5432/database
db_schema = your_schema_name
runner_type = postgres

[development]
database_url = postgresql://postgres:postgres@localhost:5432/adk_db_dev
runner_type = inmemory
```

## Runner Types

### PostgresRunner
- Uses PostgreSQL for session and memory storage
- Falls back to InMemoryRunner if connection fails
- Configured via `database_url` in config or `DATABASE_URL` env var

### InMemoryRunner
- Fast startup, no database required
- Good for development/testing
- Data is not persisted (lost on restart)

## Automatic Fallback

The server automatically falls back to InMemoryRunner if:
- PostgresRunner fails to initialize
- Database connection fails
- Database URL is not provided

This ensures **fast startup** even if the database is unavailable.

## Testing

### Health Check
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "runner_type": "PostgresRunner"
}
```

### Chat Endpoint
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

## Command Line Arguments

Matching Java AppServer.java:
```
python -m google.adk.server.app_server [port] [config_path] [environment]
```

- `port`: Server port (default: 8000)
- `config_path`: Path to config.ini file (default: `/Users/arun.parmar/go/src/adk-java/core/config.ini`)
- `environment`: Environment name (default: 'production')

## Example Usage

```bash
# Production with custom config
python -m google.adk.server.app_server 8000 /path/to/config.ini production

# Development with in-memory runner
python -m google.adk.server.app_server 8000 /path/to/config.ini development

# Test with in-memory (no config needed)
python -m google.adk.server.app_server 8080
```

## Architecture

```
app_server.py
  ├── Loads config.ini
  ├── Initializes agent (GenericOrchestrator.init_agent())
  ├── Creates runner (with fallback)
  └── Starts FastAPI server

server_handler.py
  ├── handle_chat() - Processes /chat requests
  └── handle_health() - Processes /health requests
```

## Features

✅ **Multiple Runner Support** - PostgresRunner, InMemoryRunner
✅ **Automatic Fallback** - Fast startup even if DB fails
✅ **Config File Support** - INI format like Java
✅ **Environment Support** - Production, development, test
✅ **Fast Startup** - Non-blocking initialization
✅ **Separate Handler** - Clean separation of concerns

