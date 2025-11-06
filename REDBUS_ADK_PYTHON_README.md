# Redbus ADK Python - PostgreSQL Runner Implementation

## Overview

This document provides comprehensive documentation for the PostgreSQL-backed Agent Development Kit (ADK) implementation, featuring multi-agent and multi-model support. This implementation provides persistent storage for agent sessions and memory using PostgreSQL, matching the Java ADK implementation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Tables](#database-tables)
3. [Code Structure](#code-structure)
4. [Multi-Agent & Multi-Model Setup](#multi-agent--multi-model-setup)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Integration Guide](#integration-guide)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PostgresRunner                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  PostgresSessionService  │  PostgresMemoryService     │  │
│  │  (Session Storage)       │  (Memory Search)          │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│              ┌──────────────────────┐                       │
│              │  PostgreSQL Database  │                       │
│              └──────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Agent System                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  GenericOrchestrator (RedbusADG)                      │  │
│  │  └── TicketInformationAgent (Gemini)                 │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **PostgresRunner**: Main runner that orchestrates PostgreSQL-backed services
2. **PostgresSessionService**: Manages session persistence in PostgreSQL
3. **PostgresMemoryService**: Provides memory search capabilities using PostgreSQL
4. **PostgresDBHelper**: Database connection and ORM model management
5. **Multi-Agent System**: Orchestrator with sub-agents using different models

---

## Database Tables

### Table: `sessions`

Stores session information and state.

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(255) | Primary key, unique session identifier |
| `app_name` | VARCHAR(255) | Application name (e.g., "ADK_SUPER_AGENT") |
| `user_id` | VARCHAR(255) | User identifier |
| `state` | JSONB | Session state as JSON object |
| `last_update_time` | TIMESTAMP | Last update timestamp |
| `event_data` | JSONB | Events stored as JSON (format: `{"events": [...]}`) |

**Indexes:**
- Primary key on `id`
- Foreign key relationships to `events` table

### Table: `events`

Stores individual events within sessions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR(255) | Primary key, unique event identifier |
| `session_id` | VARCHAR(255) | Foreign key to `sessions.id` (CASCADE DELETE) |
| `author` | VARCHAR(255) | Event author (e.g., "user", agent name) |
| `actions_state_delta` | JSONB | State changes from this event |
| `actions_artifact_delta` | JSONB | Artifact changes from this event |
| `actions_requested_auth_configs` | JSONB | Requested authentication configurations |
| `actions_transfer_to_agent` | VARCHAR(255) | Agent transfer target (nullable) |
| `content_role` | VARCHAR(255) | Content role (e.g., "user", "model") (nullable) |
| `timestamp` | BIGINT | Event timestamp (epoch milliseconds) |
| `invocation_id` | VARCHAR(255) | Invocation identifier (nullable) |

**Indexes:**
- Primary key on `id`
- Foreign key to `sessions.id` with CASCADE DELETE

### Table: `event_content_parts`

Stores content parts for events (text, function calls, function responses).

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | VARCHAR(255) | Primary key, foreign key to `events.id` (CASCADE DELETE) |
| `session_id` | VARCHAR(255) | Session identifier (denormalized for query performance) |
| `part_type` | VARCHAR(255) | Part type: "text", "functionCall", or "functionResponse" |
| `text_content` | TEXT | Text content (nullable, for text parts) |
| `function_call_id` | VARCHAR(255) | Function call ID (nullable, for functionCall parts) |
| `function_call_name` | VARCHAR(255) | Function call name (nullable) |
| `function_call_args` | JSONB | Function call arguments as JSON (nullable) |
| `function_response_id` | VARCHAR(255) | Function response ID (nullable, for functionResponse parts) |
| `function_response_name` | VARCHAR(255) | Function response name (nullable) |
| `function_response_data` | JSONB | Function response data as JSON (nullable) |

**Indexes:**
- Primary key on `event_id`
- Foreign key to `events.id` with CASCADE DELETE

### Table Relationships

```
sessions (1) ──< (many) events (1) ──< (many) event_content_parts
```

- One session can have many events
- One event can have many content parts
- Cascading deletes: Deleting a session deletes all its events and content parts

---

## Code Structure

### Directory Structure

```
src/google/adk/
├── runner/
│   └── postgres_runner.py          # PostgresRunner implementation
├── sessions/
│   └── postgres_session_service.py # PostgreSQL session service
├── memory/
│   └── postgres_memory_service.py   # PostgreSQL memory service
├── utils/
│   └── postgres_db_helper.py        # Database helper and ORM models
├── models/
│   └── redbus_adg.py                # RedbusADG model implementation
└── server/
    └── orchestrators/
        ├── generic_orchestrator.py  # Main orchestrator agent
        └── ticket_information_agent.py # Sub-agent example
```

### Key Files

#### `postgres_runner.py`
Main runner class that combines PostgreSQL-backed services:
- `PostgresSessionService` for session management
- `PostgresMemoryService` for memory search
- `InMemoryArtifactService` for artifacts (can be extended to PostgreSQL)

#### `postgres_session_service.py`
Implements `BaseSessionService` interface:
- `create_session()`: Creates new sessions
- `get_session()`: Retrieves sessions by ID
- `append_event()`: Adds events to sessions
- `list_sessions()`: Lists sessions for app/user
- `delete_session()`: Deletes sessions

#### `postgres_memory_service.py`
Implements `BaseMemoryService` interface:
- `add_session_to_memory()`: Adds session events to memory
- `search_memory()`: Searches historical events by query

#### `postgres_db_helper.py`
Database connection and ORM models:
- `PostgresDBHelper`: Singleton for database connections
- `PostgresSession`: ORM model for sessions table
- `PostgresEvent`: ORM model for events table
- `PostgresEventContentPart`: ORM model for event_content_parts table

---

## Multi-Agent & Multi-Model Setup

### Architecture Pattern

The implementation supports **multi-model** architecture where different agents can use different LLM backends:

- **Orchestrator Agent**: Uses `RedbusADG` (Azure LLM Gateway)
- **Sub-Agents**: Can use different models (e.g., `Gemini`, `RedbusADG`, etc.)

### Example: Multi-Model Agent Setup

```python
from google.adk import Agent
from google.adk.models.redbus_adg import RedbusADG
from google.adk.runner.postgres_runner import PostgresRunner

# Create sub-agent with Gemini model
ticket_agent = Agent(
    name="Ticket_Information_Agent",
    model="gemini-2.0-flash",  # Using Gemini
    instruction="You are an intelligent support agent...",
    description="Agent responsible for ticket information",
)

# Create orchestrator with RedbusADG model
orchestrator = Agent(
    name="ADK_SUPER_AGENT",
    model=RedbusADG(model="40"),  # Using RedbusADG
    instruction="You are an assistant for bus travel...",
    description="Main coordinator for bus related queries",
    sub_agents=[ticket_agent],  # Add sub-agent
)

# Create runner with PostgreSQL backend
runner = PostgresRunner(
    agent=orchestrator,
    app_name="ADK_SUPER_AGENT",
    db_url="postgresql://user:pass@host:5432/dbname"
)

# Use the runner
async def process_user_query(user_message: str, user_id: str, session_id: str):
    """Process a user query using the multi-model agent system."""
    # Get or create session
    session = await runner.session_service.get_session(
        app_name="ADK_SUPER_AGENT",
        user_id=user_id,
        session_id=session_id,
    )
    
    if session is None:
        session = await runner.session_service.create_session(
            app_name="ADK_SUPER_AGENT",
            user_id=user_id,
            session_id=session_id,
        )
    
    # Create user content
    from google.genai import types
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)]
    )
    
    # Run agent and collect events
    events = []
    async for event in runner.run_async(
        app_name="ADK_SUPER_AGENT",
        session_id=session.id,
        new_message=user_content,
    ):
        events.append(event)
        # Process event (e.g., extract response, handle function calls)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(f"Response: {part.text}")
                elif part.function_call:
                    print(f"Function call: {part.function_call.name}")
    
    return events
```

### Model Selection Strategy

Different agents can use different models based on their requirements:

```python
# Example: Different models for different agents
orchestrator = Agent(
    name="Orchestrator",
    model=RedbusADG(model="40"),  # Azure LLM Gateway
    sub_agents=[
        Agent(
            name="TicketAgent",
            model="gemini-2.0-flash",  # Google Gemini
            # ... other config
        ),
        Agent(
            name="BookingAgent",
            model=RedbusADG(model="40"),  # Same as orchestrator
            # ... other config
        ),
    ],
)
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# PostgreSQL Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/database

# RedbusADG Configuration (for Azure LLM Gateway)
ADURL=https://your-azure-gateway-url.com
ADU=your_username
ADP=your_password
REDBUS_ADG_MODEL=40

# Google Gemini Configuration (for Gemini models)
GOOGLE_API_KEY=your_google_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Config File (config.ini)

Alternatively, use a `config.ini` file:

```ini
[production]
database_url=postgresql://user:password@host:5432/database

[default]
runner_type=postgres
database_url=postgresql://user:password@host:5432/database
```

### Configuration Priority

1. **Environment Variables** (highest priority)
2. **Config File** (`config.ini`)
3. **Default Values**

### Database URL Format

PostgreSQL connection URL format:
```
postgresql://[user[:password]@][host][:port][/database][?parameters]
```

Examples:
```
postgresql://user:pass@localhost:5432/mydb
postgresql://user@localhost/mydb
postgresql://localhost/mydb
```

**Note**: URL-encode special characters in passwords (e.g., `$` becomes `%24`).

---

## Usage Examples

### Basic Usage

```python
from google.adk import Agent
from google.adk.runner.postgres_runner import PostgresRunner
from google.adk.models.redbus_adg import RedbusADG
import os

# Initialize agent
agent = Agent(
    name="MyAgent",
    model=RedbusADG(model=os.getenv("REDBUS_ADG_MODEL", "40")),
    instruction="You are a helpful assistant.",
)

# Create runner with PostgreSQL backend
runner = PostgresRunner(
    agent=agent,
    app_name="MY_APP",
    db_url=os.getenv("DATABASE_URL"),  # Optional, reads from env if not provided
)

# Use the runner
async def chat(user_id: str, message: str):
    # Create or get session
    session = await runner.session_service.create_session(
        app_name="MY_APP",
        user_id=user_id,
    )
    
    # Create user message
    from google.genai import types
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=message)]
    )
    
    # Run agent
    async for event in runner.run_async(
        app_name="MY_APP",
        session_id=session.id,
        new_message=user_content,
    ):
        # Process events
        if event.content:
            for part in event.content.parts:
                if part.text:
                    yield part.text
```

### Multi-Agent with Different Models

```python
from google.adk import Agent
from google.adk.runner.postgres_runner import PostgresRunner
from google.adk.models.redbus_adg import RedbusADG

# Sub-agent using Gemini
ticket_agent = Agent(
    name="TicketAgent",
    model="gemini-2.0-flash",
    instruction="Handle ticket-related queries.",
)

# Main orchestrator using RedbusADG
orchestrator = Agent(
    name="Orchestrator",
    model=RedbusADG(model="40"),
    instruction="Route queries to appropriate sub-agents.",
    sub_agents=[ticket_agent],
)

# Create runner
runner = PostgresRunner(agent=orchestrator)

# Use runner
async def handle_query(user_id: str, query: str):
    session = await runner.session_service.create_session(
        app_name="ADK_SUPER_AGENT",
        user_id=user_id,
    )
    
    from google.genai import types
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)]
    )
    
    async for event in runner.run_async(
        app_name="ADK_SUPER_AGENT",
        session_id=session.id,
        new_message=content,
    ):
        # Handle events
        pass
```

### Session Management

```python
# Create session
session = await runner.session_service.create_session(
    app_name="MY_APP",
    user_id="user123",
    session_id="session456",  # Optional, auto-generated if not provided
    state={"custom": "data"},  # Optional initial state
)

# Get session
session = await runner.session_service.get_session(
    app_name="MY_APP",
    user_id="user123",
    session_id="session456",
)

# List sessions
sessions = await runner.session_service.list_sessions(
    app_name="MY_APP",
    user_id="user123",
)

# Delete session
await runner.session_service.delete_session(
    app_name="MY_APP",
    user_id="user123",
    session_id="session456",
)
```

### Memory Search

```python
# Add session to memory (automatically done when events are appended)
await runner.memory_service.add_session_to_memory(session)

# Search memory
results = await runner.memory_service.search_memory(
    app_name="MY_APP",
    user_id="user123",
    query="ticket cancellation",
)

# Process results
for memory_entry in results.memories:
    print(f"Found: {memory_entry.content}")
    print(f"Author: {memory_entry.author}")
    print(f"Timestamp: {memory_entry.timestamp}")
```

---

## Integration Guide

### Using in Your Own Project

#### Option 1: Fork and Extend

1. **Fork the Repository**
   ```bash
   git clone https://github.com/your-org/adk-python.git
   cd adk-python
   ```

2. **Install Dependencies**
   ```bash
   # Create virtual environment
   uv venv --python "python3.11" ".venv"
   source .venv/bin/activate
   
   # Install dependencies
   uv sync --all-extras
   ```

3. **Create Your Agent Structure**
   ```
   your_project/
   ├── agents/
   │   ├── __init__.py
   │   └── your_agent.py
   └── main.py
   ```

4. **Implement Your Agent**
   ```python
   # agents/your_agent.py
   from google.adk import Agent
   from google.adk.models.redbus_adg import RedbusADG
   
   def init_agent():
       return Agent(
           name="YourAgent",
           model=RedbusADG(model="40"),
           instruction="Your agent instructions",
       )
   ```

5. **Use PostgresRunner**
   ```python
   # main.py
   from google.adk.runner.postgres_runner import PostgresRunner
   from agents.your_agent import init_agent
   import os
   
   agent = init_agent()
   runner = PostgresRunner(
       agent=agent,
       db_url=os.getenv("DATABASE_URL"),
   )
   
   # Use runner...
   ```

#### Option 2: Install as Package

1. **Install from Source**
   ```bash
   pip install -e /path/to/adk-python
   ```

2. **Use in Your Code**
   ```python
   from google.adk.runner.postgres_runner import PostgresRunner
   from google.adk import Agent
   
   # Your code here
   ```

#### Option 3: Copy Specific Files

Copy only the files you need:

```bash
# Copy PostgreSQL implementation files
cp -r src/google/adk/runner/postgres_runner.py your_project/
cp -r src/google/adk/sessions/postgres_session_service.py your_project/
cp -r src/google/adk/memory/postgres_memory_service.py your_project/
cp -r src/google/adk/utils/postgres_db_helper.py your_project/
```

Then adapt imports and use in your project.

### Database Setup

1. **Create PostgreSQL Database**
   ```sql
   CREATE DATABASE your_database;
   ```

2. **Create Tables** (tables should already exist, but if needed):
   ```sql
   -- Tables are created automatically by SQLAlchemy
   -- Or create manually using the table definitions above
   ```

2. **Set Connection String**
   ```bash
   export DATABASE_URL="postgresql://user:password@host:5432/database"
   ```

### Environment Setup

1. **Create `.env` file**
   ```bash
   DATABASE_URL=postgresql://user:password@host:5432/database
   ADURL=https://your-gateway-url.com
   ADU=your_username
   ADP=your_password
   GOOGLE_API_KEY=your_key
   ```

2. **Load in Your Code**
   ```python
   from dotenv import load_dotenv
   import os
   
   load_dotenv()  # Loads .env file
   
   db_url = os.getenv("DATABASE_URL")
   ```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Error**: `connection to server at "host" failed`

**Solutions**:
- Verify database URL format: `postgresql://user:pass@host:5432/db`
- Check network connectivity to database server
- Verify credentials
- Ensure database exists

#### 2. Table Not Found

**Error**: `relation "sessions" does not exist`

**Solutions**:
- Verify tables exist in the database
- Check database connection has proper permissions
- Ensure tables are created with correct names

#### 3. Environment Variables Not Loaded

**Error**: `Missing key inputs argument!`

**Solutions**:
- Ensure `.env` file exists in project root
- Load `.env` explicitly: `load_dotenv()`
- Verify environment variables are set: `os.getenv("GOOGLE_API_KEY")`

#### 4. Session Creation Failed

**Error**: `RuntimeError: Failed to create session`

**Solutions**:
- Check database connection
- Verify table permissions
- Check logs for detailed error messages
- Ensure `app_name` matches across runner and session operations

#### 5. Multi-Model API Key Issues

**Error**: `Missing key inputs argument!` for Gemini

**Solutions**:
- Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` in `.env`
- Load `.env` file before creating agents
- Verify API key is valid

### Debugging Tips

1. **Enable Debug Logging**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check Database Connection**
   ```python
   from google.adk.utils.postgres_db_helper import PostgresDBHelper
   db_helper = PostgresDBHelper.get_instance(db_url)
   with db_helper.get_session() as db:
       result = db.execute("SELECT 1")
       print("Connection successful")
   ```

3. **Verify Environment Variables**
   ```python
   import os
   print("DATABASE_URL:", os.getenv("DATABASE_URL"))
   print("GOOGLE_API_KEY:", "SET" if os.getenv("GOOGLE_API_KEY") else "NOT SET")
   ```

---

## Best Practices

### 1. Session Management

- Always use consistent `app_name` across your application
- Reuse sessions when possible (don't create new session for each request)
- Clean up old sessions periodically

### 2. Multi-Model Usage

- Use appropriate models for different tasks
- Orchestrator can use one model, sub-agents can use different models
- Consider model costs and latency when choosing models

### 3. Database Configuration

- Use connection pooling (handled automatically by SQLAlchemy)
- Set appropriate timeouts
- Monitor database performance

### 4. Error Handling

- Always handle exceptions when creating/getting sessions
- Implement retry logic for transient database errors
- Log errors for debugging

### 5. Security

- Never commit `.env` files or `config.ini` with credentials
- Use environment variables for sensitive data
- Rotate API keys and database passwords regularly

---

## Additional Resources

- [ADK Project Overview](../contributing/adk_project_overview_and_architecture.md)
- [Database Configuration Guide](./DATABASE_CONFIG_GUIDE.md)
- [Environment Variables Setup](./DEBUG_ENV_VARS.md)
- [How Session Creation Works](./HOW_CREATE_SESSION_WORKS.md)

---

## License

Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0.

