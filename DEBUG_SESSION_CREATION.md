# Debugging Session Creation Error

## Error You're Seeing

```
RuntimeError: Failed to create session: 8dc29a95411be00600ec264701020100
```

## What I Added

I've added detailed logging to help identify the exact issue. The logs will now show:

1. **Exception details** - The actual underlying exception
2. **Exception type** - What kind of error occurred
3. **Session details** - app_name, user_id being used
4. **Step-by-step progress** - Each step of the save process

## Common Causes

### 1. Database Tables Don't Exist

**Symptom:** `relation "sessions" does not exist`

**Solution:** Tables should be created automatically by `Base.metadata.create_all(self.engine)` in `PostgresDBHelper.__init__`. Check:

```python
# In postgres_db_helper.py line 202
Base.metadata.create_all(self.engine)
```

**Manual check:**
```sql
-- Connect to your database
psql postgresql://username:password@hostname:5432/database

-- Check if tables exist
\dt

-- Should show:
--  sessions
--  events  
--  event_content_parts
```

### 2. Database Connection Error

**Symptom:** Connection timeout, authentication failed

**Check:**
- Database URL is correct in `config.ini`
- Password is URL-encoded correctly (`%24` for `$`)
- Database is accessible from your network

### 3. Permission Issues

**Symptom:** `permission denied for table sessions`

**Solution:** Ensure user has CREATE, INSERT, UPDATE permissions

### 4. Data Type Mismatch

**Symptom:** `invalid input syntax for type jsonb` or similar

**Check:**
- `state` is a valid dictionary/JSON
- `event_data` is properly serialized

### 5. Constraint Violation

**Symptom:** `duplicate key value violates unique constraint`

**Possible:** Session ID already exists (should be handled by upsert logic)

## How to Debug

### Step 1: Check Logs

After the error, look for:
- `Error creating session` - Shows the underlying exception
- `Exception type` - What kind of error
- `Error in _save_session` - Database-level error

### Step 2: Enable Debug Logging

Set logging level to DEBUG:
```python
import logging
logging.getLogger('google_adk').setLevel(logging.DEBUG)
```

Or in your environment:
```bash
export PYTHONLOGLEVEL=DEBUG
```

### Step 3: Test Database Connection

```python
from google.adk.utils.postgres_db_helper import PostgresDBHelper

db_helper = PostgresDBHelper.get_instance()
with db_helper.get_session() as db:
    # Test query
    result = db.execute("SELECT 1")
    print("Connection works!")
```

### Step 4: Check Table Structure

```sql
-- Connect to database
psql postgresql://username:password@hostname:5432/database

-- Check table structure
\d sessions

-- Should show columns matching PostgresSession model
```

## Next Steps

1. **Restart the server** with the new logging
2. **Make the same request** that failed
3. **Check the logs** for:
   - `Error creating session` - full exception details
   - `Exception type` - what type of error
   - `Error in _save_session` - database error details

4. **Share the full error traceback** - it will show the exact line and cause

The enhanced logging will help identify whether it's:
- Database connection issue
- Table missing issue
- Data validation issue
- Permission issue
- Or something else

