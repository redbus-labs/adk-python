# Files to Commit (Excluding .md Files)

## 📁 Core Implementation Files

### PostgreSQL Services
- `src/google/adk/utils/postgres_db_helper.py` - Database helper with optional schema support
- `src/google/adk/sessions/postgres_session_service.py` - PostgreSQL session service
- `src/google/adk/memory/postgres_memory_service.py` - PostgreSQL memory service
- `src/google/adk/runner/postgres_runner.py` - PostgreSQL runner implementation
- `src/google/adk/runner/__init__.py` - Runner package init

### Server Implementation
- `src/google/adk/server/app_server.py` - Main application server with logging control
- `src/google/adk/server/server_handler.py` - Request handler for /chat and /health endpoints
- `src/google/adk/server/orchestrators/generic_orchestrator.py` - Generic orchestrator agent
- `src/google/adk/server/orchestrators/ticket_information_agent.py` - Ticket information agent (Gemini)

### Model Implementation
- `src/google/adk/models/redbus_adg.py` - RedbusADG model for Azure LLM gateway
- `src/google/adk/models/__init__.py` - Model exports (modified)

## 📁 Test Files

- `tests/unittests/sessions/test_postgres_session_service.py` - Session service tests
- `tests/unittests/memory/test_postgres_memory_service.py` - Memory service tests

## 📁 Example/Config Template Files

- `config.ini.example` - Example config file (no real credentials)
- `config.example.json` - Example JSON config
- `config.example.yaml` - Example YAML config
- `java_to_python_mapping_example.py` - Example mapping file

## 📁 Configuration Files

- `.gitignore` - Updated to exclude config.ini and sensitive files

## 📝 Git Commands to Commit

```bash
# Core implementation files
git add src/google/adk/utils/postgres_db_helper.py
git add src/google/adk/sessions/postgres_session_service.py
git add src/google/adk/memory/postgres_memory_service.py
git add src/google/adk/runner/
git add src/google/adk/server/
git add src/google/adk/models/redbus_adg.py
git add src/google/adk/models/__init__.py

# Test files
git add tests/unittests/sessions/test_postgres_session_service.py
git add tests/unittests/memory/test_postgres_memory_service.py

# Example/Config files
git add config.ini.example
git add config.example.json
git add config.example.yaml
git add java_to_python_mapping_example.py

# Configuration
git add .gitignore

# Verify no sensitive files
git status

# Commit
git commit -m "feat(postgres): Add PostgreSQL-backed session and memory services

- Implement PostgresSessionService and PostgresMemoryService
- Add PostgresRunner for PostgreSQL-backed execution
- Add PostgresDBHelper with optional schema support
- Implement RedbusADG model for Azure LLM gateway
- Add multi-agent/multi-model support (RedbusADG + Gemini)
- Add logging configuration with enable/disable option
- Add example config files and comprehensive tests"
```

## 🔒 Security Verification

All files have been verified:
- ✅ No hardcoded credentials
- ✅ No API keys
- ✅ No real database URLs
- ✅ All use placeholders or read from environment

