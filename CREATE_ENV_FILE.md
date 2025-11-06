# How to Create .env File - Step by Step

## What is a .env file?

A `.env` file is a text file that stores environment variables (like passwords, API keys, database URLs). It's loaded automatically by VS Code and many applications.

## Where is the "project root"?

The project root is: `/Users/arun.parmar/go/src/adk-python`

This is where you see:
- `src/` directory
- `config.ini` file
- `pyproject.toml` file
- `.venv/` directory (if you have a virtual environment)

## How to Create .env File

### Method 1: Using Terminal (Recommended)

1. Open terminal
2. Navigate to project root:
   ```bash
   cd /Users/arun.parmar/go/src/adk-python
   ```

3. Create the file:
   ```bash
   touch .env
   ```

4. Open it in VS Code:
   ```bash
   code .env
   ```

5. Add your environment variables:
   ```bash
   # Database URL (optional - config.ini already has it)
   # DATABASE_URL=postgresql://username:password@hostname:5432/database

   # Redbus ADG Configuration
   ADURL=your_ad_url_here
   ADU=your_ad_user_here
   ADP=your_ad_password_here
   REDBUS_ADG_MODEL=40
   
   # Google/Gemini API Keys (for Gemini models)
   GOOGLE_API_KEY=your_google_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # PostgreSQL Schema (optional)
   DB_SCHEMA=your_schema_name
   ```

6. Save the file (Cmd+S / Ctrl+S)

### Method 2: Using VS Code

1. In VS Code, right-click in the file explorer (left sidebar)
2. Select "New File"
3. Type `.env` as the filename
4. Press Enter
5. Add your environment variables
6. Save

### Method 3: Using Command Line (One-liner)

```bash
cd /Users/arun.parmar/go/src/adk-python && cat > .env << 'EOF'
ADURL=your_ad_url_here
ADU=your_ad_user_here
ADP=your_ad_password_here
REDBUS_ADG_MODEL=40
EOF
```

## File Format

The `.env` file format is simple:
```
VARIABLE_NAME=value
ANOTHER_VAR=another_value
```

**Important rules:**
- No spaces around the `=` sign
- No quotes needed (unless the value contains spaces)
- One variable per line
- Lines starting with `#` are comments

## Example .env File

```bash
# This is a comment
# Database URL (optional - can also be set in config.ini)
DATABASE_URL=postgresql://username:password@hostname:5432/database

# Redbus ADG Configuration
ADURL=https://your-azure-gateway-url.com
ADU=your_username
ADP=your_password
REDBUS_ADG_MODEL=40

# Google/Gemini API Keys (for Gemini models)
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# PostgreSQL Schema (optional)
DB_SCHEMA=your_schema_name
```

## Verify It Works

After creating `.env`:

1. Restart VS Code debugger (F5)
2. Check the logs - you should see environment variables are loaded
3. Or test in Python:
   ```python
   import os
   print(os.getenv('ADURL'))
   ```

## Security Note

⚠️ **Never commit `.env` to git!** It should already be in `.gitignore`. If not, add it:
```bash
echo ".env" >> .gitignore
```

## Current Status

Since your `config.ini` already has the database URL, you **don't need** to set `DATABASE_URL` in `.env` unless you want to override it.

You only need `.env` if you need:
- ADURL, ADU, ADP (for RedbusADG model)
- Or want to override database URL from environment

