# Setting Up Environment Variables for Debugging

## Quick Fix

Since your `config.ini` already has the database URL, the app will work for database connections. However, if you need environment variables for RedbusADG (ADURL, ADU, ADP), here's how to set them:

### Method 1: Create .env file (Recommended)

1. Create a `.env` file in the project root:
```bash
cd /Users/arun.parmar/go/src/adk-python
cat > .env << 'EOF'
# Database URL (optional - config.ini has it)
# DATABASE_URL=postgresql://username:password@hostname:5432/database

# Redbus ADG Configuration (if needed)
ADURL=your_ad_url_here
ADU=your_ad_user_here
ADP=your_ad_password_here
REDBUS_ADG_MODEL=40
EOF
```

2. Edit `.env` with your actual values

3. The launch.json is configured to load `.env` automatically

### Method 2: Set in Shell Profile

Add to `~/.zshrc` or `~/.bashrc`:
```bash
export ADURL="your_value"
export ADU="your_value"
export ADP="your_value"
export REDBUS_ADG_MODEL="40"
```

Then restart VS Code.

### Method 3: Add to launch.json directly (Not recommended for secrets)

Edit `.vscode/launch.json` and add values directly in the `env` section.

## Current Status

✅ **Database Connection**: Works via `config.ini` (no env vars needed)
⚠️ **RedbusADG**: Needs ADURL, ADU, ADP if you're using RedbusADG model

## Verify

After setting up, restart the debugger and check logs:
- Database URL should be read from config.ini
- ADURL/ADU/ADP should be available if set

## Test

Run the server and check the logs:
```bash
python -m google.adk.server.app_server 8080
```

Look for:
- "Database URL found: postgresql://..."
- "Database URL source: CONFIG FILE"

