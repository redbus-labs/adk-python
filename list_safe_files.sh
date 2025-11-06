#!/bin/bash
# List all safe files to commit (excluding sensitive data)

echo "=== Safe Files to Commit ==="
echo ""

echo "📁 Core Implementation Files:"
git status --porcelain | grep -E "^\?\?" | awk '{print $2}' | grep "^src/google/adk/" | grep "\.py$" | sort

echo ""
echo "📁 Test Files:"
git status --porcelain | grep -E "^\?\?" | awk '{print $2}' | grep "^tests/" | sort

echo ""
echo "📁 Documentation Files:"
git status --porcelain | grep -E "^\?\?" | awk '{print $2}' | grep "\.md$" | sort

echo ""
echo "📁 Example/Config Template Files:"
git status --porcelain | grep -E "^\?\?" | awk '{print $2}' | grep -E "example|\.example\." | sort

echo ""
echo "📁 Modified Files:"
git status --porcelain | grep -E "^ M" | awk '{print $2}' | sort

echo ""
echo "❌ Files NOT to commit (contains sensitive data):"
echo "  - config.ini (database credentials)"
echo "  - .env (API keys and credentials)"
echo "  - test_*.py (test scripts)"
echo "  - test_*.sh (test scripts)"
