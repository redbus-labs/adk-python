# Debugging Environment Variables

## Issue
When debugging in VS Code, environment variables may be empty because they're not set in VS Code's environment.

## Solutions

### Option 1: Use .env file (Recommended)

1. Create `.env` file in project root:
```bash
# Copy from example
cp .env.example .env
```

2. Edit `.env` with your values:
```bash
DATABASE_URL=postgresql://username:password@hostname:5432/database
ADURL=your_ad_url_here
ADU=your_ad_user_here
ADP=your_ad_password_here
REDBUS_ADG_MODEL=40
```

3. The launch.json will automatically load `.env` file (via `"envFile": "${workspaceFolder}/.env"`)

### Option 2: Set in VS Code Settings

1. Open VS Code Settings (Cmd+, / Ctrl+,)
2. Search for "python.envFile"
3. Set it to `${workspaceFolder}/.env`

### Option 3: Set in Terminal Profile

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export DATABASE_URL="postgresql://username:password@hostname:5432/database"
export ADURL="your_value"
export ADU="your_value"
export ADP="your_value"
export REDBUS_ADG_MODEL="40"
```

Then restart VS Code (so it picks up the new environment).

### Option 4: Use config.ini (Current Setup)

Since `config.ini` already has the database URL, the app will read from there even if environment variables are empty. The database connection should work.

However, `ADURL`, `ADU`, `ADP` are still needed for RedbusADG model. These can be:
- Set in `.env` file
- Set in your shell profile
- Or passed directly in launch.json (not recommended for secrets)

## Verify Environment Variables

Add this to your code temporarily to debug:
```python
import os
logger.info('DATABASE_URL: %s', os.getenv('DATABASE_URL', 'NOT SET'))
logger.info('ADURL: %s', os.getenv('ADURL', 'NOT SET'))
```

## Current Setup

The app_server.py prioritizes:
1. Environment variables (DATABASE_URL, POSTGRES_URL, DB_URL)
2. Config file (config.ini) - database_url field
3. PostgresDBHelper will try to read from environment as fallback

So even if environment variables are empty, the database URL from `config.ini` will be used.

