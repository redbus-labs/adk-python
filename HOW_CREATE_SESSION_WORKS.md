# How `create_session` Saves Data to Database

## Complete Flow Diagram

```
1. API Request (/chat endpoint)
   ↓
2. server_handler.py
   session = await self.runner.session_service.create_session(...)
   ↓
3. postgres_session_service.py
   create_session() method
   ↓
4. Creates Session object (in-memory)
   ↓
5. Calls _save_session(session)
   ↓
6. Gets database session from PostgresDBHelper
   ↓
7. Converts Session → PostgresSession (SQLAlchemy model)
   ↓
8. INSERT INTO sessions table (SQLAlchemy)
   ↓
9. COMMIT transaction
   ↓
10. Database: sessions table updated
```

## Step-by-Step Code Flow

### Step 1: API Request Handler
**File:** `src/google/adk/server/server_handler.py`
```python
# Line 117
session = await self.runner.session_service.create_session(
    app_name=app_name,
    user_id=user_id,
    session_id=session_id,
    state=initial_state,
)
```

### Step 2: Create Session Method
**File:** `src/google/adk/sessions/postgres_session_service.py`
```python
# Line 70-106
async def create_session(
    self,
    *,
    app_name: str,
    user_id: str,
    state: Optional[dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Session:
    # 1. Validate inputs
    if not app_name:
        raise ValueError('appName cannot be null')
    if not user_id:
        raise ValueError('userId cannot be null')
    
    # 2. Generate session ID if not provided
    resolved_session_id = (
        session_id.strip() if session_id and session_id.strip() 
        else str(uuid.uuid4())
    )
    
    # 3. Create in-memory Session object
    new_session = Session(
        id=resolved_session_id,
        app_name=app_name,
        user_id=user_id,
        state=initial_state,  # From request headers
        events=[],  # Empty initially
        last_update_time=now.timestamp(),
    )
    
    # 4. Save to database
    self._save_session(new_session)
    
    return self._copy_session(new_session)
```

### Step 3: Save to Database
**File:** `src/google/adk/sessions/postgres_session_service.py`
```python
# Line 287-320
def _save_session(self, session: Session) -> None:
    """Saves a session to the database."""
    
    # Get database session context manager
    with self.db_helper.get_session() as db_session:
        # Check if session already exists (upsert logic)
        pg_session = (
            db_session.query(PostgresSession)
            .filter(PostgresSession.id == session.id)
            .first()
        )
        
        # Prepare event data
        event_data = {
            'events': [e.model_dump(mode='json') for e in session.events]
        }
        
        if pg_session is None:
            # INSERT: Create new PostgresSession object
            pg_session = PostgresSession(
                id=session.id,
                app_name=session.app_name,
                user_id=session.user_id,
                state=session.state,  # JSONB column
                last_update_time=datetime.fromtimestamp(session.last_update_time),
                event_data=event_data,  # JSONB column
            )
            db_session.add(pg_session)  # Queue for INSERT
        else:
            # UPDATE: Modify existing session
            pg_session.app_name = session.app_name
            pg_session.user_id = session.user_id
            pg_session.state = session.state
            pg_session.last_update_time = datetime.fromtimestamp(session.last_update_time)
            pg_session.event_data = event_data
        
        # Execute INSERT/UPDATE
        db_session.commit()
        
        # Insert events (if any)
        self._insert_events(db_session, session)
        
        # Final commit
        db_session.commit()
```

### Step 4: Database Helper
**File:** `src/google/adk/utils/postgres_db_helper.py`
```python
# Line 300-312
@contextmanager
def get_session(self):
    """Get a database session context manager."""
    session = self.session_factory()  # SQLAlchemy session
    try:
        yield session
        session.commit()  # Auto-commit on success
    except Exception:
        session.rollback()  # Rollback on error
        raise
    finally:
        session.close()  # Close connection
```

### Step 5: SQLAlchemy Model
**File:** `src/google/adk/utils/postgres_db_helper.py`
```python
# Line 76-92
class PostgresSession(Base):
    """Represents a session stored in PostgreSQL."""
    
    __tablename__ = 'sessions'  # Table name
    
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    app_name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[str] = mapped_column(String(255))
    state: Mapped[dict[str, Any]] = mapped_column(PostgresJSONB, default={})
    last_update_time: Mapped[datetime] = mapped_column(DateTime)
    event_data: Mapped[dict[str, Any]] = mapped_column(PostgresJSONB, default={})
```

## Actual SQL Generated

When `db_session.add(pg_session)` is called, SQLAlchemy generates:

```sql
INSERT INTO sessions (
    id,
    app_name,
    user_id,
    state,
    last_update_time,
    event_data
) VALUES (
    '8dc29a95411be00600ec264701020100',  -- session_id
    'ADK_SUPER_AGENT',                    -- app_name
    'default',                             -- user_id
    '{"business_unit": "BUS", "country": "IND", ...}',  -- state (JSONB)
    '2025-01-06 10:30:45.123',            -- last_update_time
    '{"events": []}'                       -- event_data (JSONB)
);
```

## Key Components

### 1. **Context Manager** (`get_session()`)
- Opens database connection
- Auto-commits on success
- Auto-rollback on error
- Closes connection automatically

### 2. **Upsert Logic**
- Checks if session exists: `db_session.query(PostgresSession).filter(...).first()`
- If `None`: INSERT (new record)
- If exists: UPDATE (modify existing)

### 3. **JSONB Columns**
- `state`: Stored as PostgreSQL JSONB (from `session.state` dict)
- `event_data`: Stored as PostgreSQL JSONB (events serialized to JSON)

### 4. **Transaction Management**
- `db_session.add()` - Queues the INSERT
- `db_session.commit()` - Executes the SQL
- Wrapped in try/except for error handling

## Data Flow Example

**Input (from API request):**
```python
{
    "message": "Hi",
    "orderItemUUID": "8dc29a95411be00600ec264701020100"
}
headers: {
    "BUSINESS_UNIT": "BUS",
    "COUNTRY": "IND",
    "X-CLIENT": "SELF_HELP"
}
```

**Creates Session object:**
```python
Session(
    id="8dc29a95411be00600ec264701020100",
    app_name="ADK_SUPER_AGENT",
    user_id="default",
    state={
        "business_unit": "BUS",
        "country": "IND",
        "x_client": "SELF_HELP",
        "order_item_uuid": "8dc29a95411be00600ec264701020100"
    },
    events=[],
    last_update_time=1704547845.123
)
```

**Saved to Database:**
```sql
INSERT INTO sessions VALUES (
    '8dc29a95411be00600ec264701020100',
    'ADK_SUPER_AGENT',
    'default',
    '{"business_unit": "BUS", "country": "IND", ...}'::jsonb,
    '2025-01-06 10:30:45.123',
    '{"events": []}'::jsonb
);
```

## Summary

1. **`create_session()`** creates an in-memory `Session` object
2. **`_save_session()`** converts it to SQLAlchemy `PostgresSession` model
3. **`db_session.add()`** queues the INSERT operation
4. **`db_session.commit()`** executes the SQL INSERT statement
5. **Database** stores the row in `sessions` table

The key is the **SQLAlchemy ORM** that converts Python objects to SQL INSERT statements automatically!

