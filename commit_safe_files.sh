#!/bin/bash
# Script to safely commit files without sensitive data

echo "🔍 Checking for sensitive files..."
if git status --porcelain | grep -q "config.ini"; then
  echo "⚠️  WARNING: config.ini is in git status. Make sure it's in .gitignore!"
fi

echo ""
echo "�� Staging safe files..."

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

# Documentation
git add REDBUS_ADK_PYTHON_README.md
git add *.md

# Example configs
git add config.ini.example
git add config.example.json
git add config.example.yaml

# Gitignore update
git add .gitignore

echo ""
echo "✅ Files staged. Verifying no sensitive files..."
echo ""
git status --short

echo ""
echo "🔒 Security check:"
if git diff --cached --name-only | grep -E "config\.ini$|\.env$"; then
  echo "❌ ERROR: Sensitive files detected in staged changes!"
  exit 1
else
  echo "✅ No sensitive files detected in staged changes"
fi

echo ""
echo "📝 Ready to commit. Run:"
echo "   git commit -m 'feat(postgres): Add PostgreSQL-backed services'"
