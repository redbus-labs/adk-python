# How to Edit .env File - Complete Guide

## Step-by-Step Instructions

### Step 1: Create the .env File

**Option A: Using VS Code (Easiest)**
1. In VS Code, click the "New File" icon in the file explorer (or right-click → New File)
2. Type: `.env` (including the dot at the beginning)
3. Press Enter

**Option B: Using Terminal**
```bash
cd /Users/arun.parmar/go/src/adk-python
touch .env
code .env  # Opens in VS Code
```

### Step 2: Add Your Environment Variables

Copy and paste this template into your `.env` file:

```bash
# Redbus AD Gateway Configuration
# These are required for RedbusADG model to work
ADURL=https://your-redbus-ad-gateway-url.com
ADU=your_username_here
ADP=your_password_here

# Model Configuration
REDBUS_ADG_MODEL=40

# Database URL (Optional - config.ini already has it)
# Uncomment and use this if you want to override config.ini
# DATABASE_URL=postgresql://username:password@hostname:5432/database
```

### Step 3: Replace with Your Actual Values

Replace the placeholder values:

1. **ADURL** - Your Redbus AD Gateway API URL
   - Example: `ADURL=https://api.redbus.com/gateway`
   - Get this from your Redbus AD Gateway documentation

2. **ADU** - Your username for Redbus AD Gateway
   - Example: `ADU=myusername`
   - Your Redbus AD Gateway username

3. **ADP** - Your password for Redbus AD Gateway
   - Example: `ADP=mypassword`
   - Your Redbus AD Gateway password

4. **REDBUS_ADG_MODEL** - Model ID (already set to 40, usually correct)
   - Example: `REDBUS_ADG_MODEL=40`
   - This is the model identifier

### Step 4: Save the File

Press `Cmd+S` (Mac) or `Ctrl+S` (Windows/Linux) to save.

## Example .env File (After Editing)

```bash
# Redbus AD Gateway Configuration
ADURL=https://gateway.redbus.com/api/v1
ADU=cartesian_user
ADP=SecurePassword123!

# Model Configuration
REDBUS_ADG_MODEL=40
```

## Important Formatting Rules

1. **No spaces around equals sign:**
   ✅ Correct: `ADURL=https://example.com`
   ❌ Wrong: `ADURL = https://example.com`

2. **No quotes needed (unless value has spaces):**
   ✅ Correct: `ADU=username`
   ✅ Also OK: `ADU="user name"` (if username has spaces)
   ❌ Wrong: `ADU='username'` (unnecessary quotes)

3. **One variable per line:**
   ✅ Correct:
   ```
   ADURL=https://example.com
   ADU=username
   ```
   ❌ Wrong: `ADURL=https://example.com ADU=username`

4. **Comments start with #:**
   ```bash
   # This is a comment
   ADURL=https://example.com  # This is also a comment
   ```

## How to Find Your Values

If you don't know your ADURL, ADU, ADP values:

1. **Check your Java implementation** - Look for where these are set in your Java code
2. **Check your deployment/config** - Look in your deployment configuration files
3. **Ask your team** - These are typically provided by your DevOps/infrastructure team
4. **Check existing environment** - If you have these set elsewhere:
   ```bash
   echo $ADURL
   echo $ADU
   echo $ADP
   ```

## Verify It Works

After saving `.env`:

1. **Restart VS Code debugger** (F5)
2. **Check logs** - You should see RedbusADG initializing with the API URL
3. **Test the endpoint** - The `/chat` endpoint should work with RedbusADG model

## Quick Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| ADURL | ✅ Yes | Redbus AD Gateway API URL | `https://gateway.redbus.com/api` |
| ADU | ✅ Yes | Username for AD Gateway | `myusername` |
| ADP | ✅ Yes | Password for AD Gateway | `mypassword` |
| REDBUS_ADG_MODEL | ⚠️ Optional | Model ID (default: 40) | `40` |
| DATABASE_URL | ⚠️ Optional | Database URL (config.ini has it) | `postgresql://...` |

## Troubleshooting

**Problem: Variables not loading**
- Make sure `.env` is in project root: `/Users/arun.parmar/go/src/adk-python/.env`
- Restart VS Code after creating/editing `.env`
- Check for typos in variable names

**Problem: Still getting errors**
- Check that values don't have extra spaces
- Make sure there are no quotes around values (unless needed)
- Verify variable names match exactly: `ADURL`, `ADU`, `ADP` (case-sensitive)

