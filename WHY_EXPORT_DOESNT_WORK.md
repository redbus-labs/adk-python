# Why `export` Doesn't Work with VS Code Debugging

## The Problem

When you run:
```bash
export ADURL=https://example.com
export ADU=username
export ADP=password
python -m google.adk.server.app_server 8080
```

It works in the **terminal** because the shell passes environment variables to the Python process.

But when you debug in VS Code (press F5), VS Code runs Python in a **separate process** that:
- Doesn't inherit your terminal's environment variables
- Has its own isolated environment
- Only gets variables from:
  1. `.env` file (if configured)
  2. `launch.json` `env` section
  3. System-wide environment variables (not shell exports)

## Visual Explanation

```
Terminal Session:
┌─────────────────────────┐
│ export ADURL=...        │ ← Sets variable in THIS shell
│ python -m app_server    │ ← Inherits from shell ✅
└─────────────────────────┘

VS Code Debugger:
┌─────────────────────────┐
│ Press F5                │
│                         │
│ VS Code → Python        │ ← Separate process
│ (No shell variables)    │ ← Doesn't see export ❌
└─────────────────────────┘
```

## Solutions

### Solution 1: Use .env File (Recommended) ✅

VS Code can automatically load `.env` file:

1. Create `.env` in project root
2. Add variables:
   ```
   ADURL=https://example.com
   ADU=username
   ADP=password
   ```
3. VS Code loads it automatically (via `envFile` in launch.json)

**Why this works:**
- VS Code reads `.env` file directly
- No need to export in terminal
- Works for both debugging AND terminal

### Solution 2: Set in launch.json ✅

Add to `.vscode/launch.json`:
```json
"env": {
  "ADURL": "https://example.com",
  "ADU": "username",
  "ADP": "password"
}
```

**Why this works:**
- VS Code passes these directly to the debug process
- Works for debugging

### Solution 3: Set in Shell Profile (Partial) ⚠️

Add to `~/.zshrc` or `~/.bashrc`:
```bash
export ADURL=https://example.com
export ADU=username
export ADP=password
```

**Why this partially works:**
- ✅ Works for terminal: `python -m app_server`
- ❌ Doesn't work for VS Code debugging (unless you restart VS Code after setting)
- ⚠️ VS Code only reads system environment on startup

### Solution 4: Use Terminal Profile in VS Code ⚠️

In `.vscode/settings.json`:
```json
{
  "terminal.integrated.env.osx": {
    "ADURL": "https://example.com",
    "ADU": "username",
    "ADP": "password"
  }
}
```

**Why this partially works:**
- ✅ Works for VS Code terminal
- ❌ Doesn't work for debugging (debugger uses different process)

## Comparison

| Method | Terminal Run | VS Code Debug | Notes |
|--------|-------------|---------------|-------|
| `export` in terminal | ✅ Yes | ❌ No | Only in that shell session |
| `.env` file | ✅ Yes* | ✅ Yes | *If using python-dotenv |
| `launch.json` env | ❌ No | ✅ Yes | Only for debugging |
| Shell profile (`~/.zshrc`) | ✅ Yes | ⚠️ Maybe | Only if VS Code restarted |

## Why VS Code Debugger is Different

1. **Separate Process**: Debugger runs `debugpy` which spawns Python in a new process
2. **Isolated Environment**: Doesn't inherit from your terminal session
3. **Security**: Intentionally isolated to prevent environment pollution

## Best Practice

**Use `.env` file** because:
- ✅ Works for both terminal and debugging
- ✅ Easy to manage
- ✅ Can be gitignored (keeps secrets safe)
- ✅ Standard practice

## Quick Test

To verify what VS Code sees:

Add this to your code temporarily:
```python
import os
print("ADURL:", os.getenv('ADURL', 'NOT SET'))
print("ADU:", os.getenv('ADU', 'NOT SET'))
print("ADP:", os.getenv('ADP', 'NOT SET'))
```

Run in:
1. **Terminal**: `python -m google.adk.server.app_server 8080` → Should show values if exported
2. **VS Code Debugger** (F5): → Will show "NOT SET" unless you use `.env` or `launch.json`

## Summary

**`export` doesn't work with VS Code debugging because:**
- VS Code debugger runs in a separate process
- It doesn't inherit your terminal's environment
- It only reads from `.env` file or `launch.json` env section

**Solution:** Use `.env` file - it works for both terminal and debugging!

