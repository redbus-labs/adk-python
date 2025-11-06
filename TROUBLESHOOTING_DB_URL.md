# Troubleshooting Database URL Errors

## Error: `sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL`

This error occurs when the database URL format is invalid. SQLAlchemy requires a specific URL format.

## Valid URL Formats

### Standard Format
```
postgresql://username:password@host:port/database
```

### With psycopg2 driver
```
postgresql+psycopg2://username:password@host:port/database
```

## Common Issues and Fixes

### Issue 1: Missing `postgresql://` prefix
**❌ Wrong:**
```
localhost:5432/adk_db
postgres:postgres@localhost:5432/adk_db
```

**✅ Correct:**
```
postgresql://postgres:postgres@localhost:5432/adk_db
```

### Issue 2: Special characters in password
If your password contains special characters like `@`, `#`, `%`, etc., they need to be URL-encoded.

**Example:**
- Password: `my@pass#123`
- URL-encoded: `my%40pass%23123`
- Full URL: `postgresql://user:my%40pass%23123@localhost:5432/db`

Or use environment variables:
```bash
export DBUSER="user"
export DBPASSWORD="my@pass#123"
export DBURL="localhost:5432/db"
```

### Issue 3: Empty or None URL
Make sure the environment variable is actually set:
```bash
# Check if set
echo $DATABASE_URL

# Set it
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
```

### Issue 4: Whitespace in URL
The URL is automatically trimmed, but check for hidden characters:
```bash
# Good
export DATABASE_URL="postgresql://user:pass@host/db"

# Bad (extra spaces)
export DATABASE_URL=" postgresql://user:pass@host/db "
```

## Test Your Database URL

Use the test script to validate your URL:
```bash
python test_db_url.py
```

Or test manually:
```python
from sqlalchemy import create_engine

db_url = "postgresql://postgres:postgres@localhost:5432/adk_db"
engine = create_engine(db_url)
print("✅ URL is valid!")
```

## Examples

### Local Development
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
```

### With Default Port
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost/adk_db"
# Port 5432 is assumed
```

### Remote Server
```bash
export DATABASE_URL="postgresql://user:pass@db.example.com:5432/mydb"
```

### With SSL
```bash
export DATABASE_URL="postgresql://user:pass@host:5432/db?sslmode=require"
```

## Debugging Steps

1. **Check environment variable:**
   ```bash
   echo $DATABASE_URL
   ```

2. **Test URL format:**
   ```bash
   python test_db_url.py
   ```

3. **Check PostgreSQL is running:**
   ```bash
   psql -U postgres -h localhost -c "SELECT version();"
   ```

4. **Try connecting manually:**
   ```bash
   psql "postgresql://postgres:postgres@localhost:5432/adk_db"
   ```

5. **Check server logs:**
   The server will log the database URL (first 50 chars) if there's an error.

## Quick Fix

If you're getting the error, try:

1. **Set a simple test URL:**
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
   ```

2. **Verify it works:**
   ```bash
   python test_db_url.py
   ```

3. **Run the server:**
   ```bash
   python -m google.adk.server.postgres_app_server --port 8000
   ```

