# Database Configuration Guide

The Postgres App Server now supports reading database connection details from multiple sources without requiring command-line arguments.

## Configuration Priority

The server reads database configuration in the following priority order:

1. **Command line argument** (`--db-url`) - Highest priority
2. **Config file** (`--config`) - Medium priority
3. **Environment variables** - Lowest priority

## Method 1: Environment Variables (Recommended)

Set one of these environment variables:

### Standard Format (Single Variable)
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
```

### Alternative Variable Names
```bash
export POSTGRES_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
# OR
export POSTGRESQL_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
# OR
export DB_URL="postgresql://postgres:postgres@localhost:5432/adk_db"
```

### Legacy Format (Separate Components)
```bash
export DBURL="localhost:5432/adk_db"
export DBUSER="postgres"
export DBPASSWORD="postgres"
```

### Using .env File
Create a `.env` file in the project root:
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/adk_db
```

Then load it (if using python-dotenv):
```bash
source .env  # Or use python-dotenv to load automatically
```

## Method 2: Config File

Create a YAML or JSON config file:

### YAML Config (`config.yaml`)
```yaml
production:
  database:
    url: "postgresql://postgres:postgres@localhost:5432/adk_db"

development:
  database:
    url: "postgresql://postgres:postgres@localhost:5432/adk_db_dev"
```

### JSON Config (`config.json`)
```json
{
  "production": {
    "database": {
      "url": "postgresql://postgres:postgres@localhost:5432/adk_db"
    }
  },
  "development": {
    "database": {
      "url": "postgresql://postgres:postgres@localhost:5432/adk_db_dev"
    }
  }
}
```

### Alternative Config Formats

The config file also supports these formats:

```yaml
# Direct root-level key
db_url: "postgresql://postgres:postgres@localhost:5432/adk_db"
```

```yaml
# Root-level database section
database:
  url: "postgresql://postgres:postgres@localhost:5432/adk_db"
```

### Running with Config File
```bash
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --config config.yaml \
  --environment production
```

## Method 3: Command Line (Fallback)

If you need to override config or env vars:
```bash
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --db-url "postgresql://postgres:postgres@localhost:5432/adk_db"
```

## Running the Server

### Simple Command (Uses Environment Variables)
```bash
# Set environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/adk_db"

# Run server (no --db-url needed!)
python -m google.adk.server.postgres_app_server --port 8000
```

### With Config File
```bash
python -m google.adk.server.postgres_app_server \
  --port 8000 \
  --config config.yaml \
  --environment production
```

## Complete Example Setup

### 1. Create `.env` file:
```bash
cat > .env << EOF
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/adk_db
ADURL=https://your-api-gateway-url.com
ADU=your-username
ADP=your-password
REDBUS_ADG_MODEL=40
EOF
```

### 2. Load environment variables:
```bash
source .env  # Or export them manually
```

### 3. Run server:
```bash
python -m google.adk.server.postgres_app_server --port 8000
```

## VS Code Debugging

The VS Code launch configuration has been updated to use environment variables. Set `DATABASE_URL` in your environment or `.env` file, and it will be picked up automatically.

## Error Messages

If no database URL is found, you'll see:
```
Database URL not found. Please provide one of:
  - Command line: --db-url "postgresql://..."
  - Config file: --config config.yaml
  - Environment variable: DATABASE_URL, POSTGRES_URL, DB_URL, or DBURL/DBUSER/DBPASSWORD
```

## Security Best Practices

1. **Never commit credentials to version control**
   - Add `.env` to `.gitignore`
   - Use environment variables in production
   - Use secret management services for production

2. **Use config files for different environments**
   - `config.production.yaml`
   - `config.development.yaml`
   - Keep config files out of version control

3. **Prefer environment variables**
   - Easier to manage in containers/Kubernetes
   - No risk of committing secrets
   - Works well with CI/CD pipelines

