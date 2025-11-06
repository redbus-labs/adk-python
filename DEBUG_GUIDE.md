# Debugging Guide for ADK App Server

## Setting Up Debugging in VS Code

### 1. Using VS Code Debugger

1. **Open the file** you want to debug: `src/google/adk/server/server_handler.py`

2. **Set breakpoints** by clicking in the gutter (left margin) next to line numbers:
   - Click on line 95 (where session handling starts)
   - Click on line 97 (get_session call)
   - Click on line 110 (create_session call)
   - Click on line 123 (run_async call)

3. **Start debugging**:
   - Press `F5` or go to `Run > Start Debugging`
   - Or use the Debug panel (Ctrl+Shift+D / Cmd+Shift+D)
   - Select "Python: App Server" configuration
   - Click the green play button

4. **Send a test request**:
   ```bash
   curl --location 'http://localhost:8080/chat' \
   --header 'BUSINESS_UNIT: BUS' \
   --header 'COUNTRY: IND' \
   --header 'Content-Type: application/json' \
   --header 'X-CLIENT: SELF_HELP' \
   --data '{"message": "Hi", "orderItemUUID": "8dc29a95411be00600ec264701020100"}'
   ```

5. **Debug controls**:
   - **F10** - Step Over (execute current line)
   - **F11** - Step Into (go into function calls)
   - **Shift+F11** - Step Out (exit current function)
   - **F5** - Continue (resume execution)
   - **Shift+F5** - Stop debugging

### 2. Inspecting Variables

While debugging, you can:
- **Hover** over variables to see their values
- **Watch** specific variables in the Watch panel
- **Inspect** variables in the Variables panel (left sidebar)
- **Evaluate** expressions in the Debug Console (bottom panel)

### 3. Important Variables to Watch

When debugging `handle_chat`:
- `body` - The request body
- `session_id` - The session ID (from orderItemUUID)
- `user_message` - The user's message
- `app_name` - Should be "ADK_SUPER_AGENT"
- `user_id` - Defaults to "default"
- `initial_state` - Contains headers and order info
- `session` - The session object

### 4. Common Debugging Scenarios

#### Debug Session Creation
1. Set breakpoint at line 95 (`if session_id:`)
2. Step through to see if `session_id` is set correctly
3. Step into `get_session` (F11) to see what happens
4. Check if exception is caught at line 100

#### Debug Agent Execution
1. Set breakpoint at line 123 (`async for event in self.runner.run_async`)
2. Step through to see events being generated
3. Check the event structure at line 129

#### Debug Database Issues
1. Set breakpoint in `postgres_session_service.py` at line 147 (`stored_session = self._get_session_from_db`)
2. Step into `_get_session_from_db` to see database query
3. Check for database connection errors

## Using Python Debugger (pdb)

### Method 1: Add breakpoint in code
```python
import pdb; pdb.set_trace()
```

Add this line where you want to break:
```python
# In server_handler.py, line 95
session = None
if session_id:
    import pdb; pdb.set_trace()  # Break here
    try:
        session = await self.runner.session_service.get_session(...)
```

Run with:
```bash
python -m google.adk.server.app_server 8080
```

### Method 2: Use breakpoint() function (Python 3.7+)
```python
# In server_handler.py
if session_id:
    breakpoint()  # Opens debugger
    try:
        session = await self.runner.session_service.get_session(...)
```

## Using Logging for Debugging

Add detailed logging:
```python
logger.debug('Session ID: %s', session_id)
logger.debug('User ID: %s', user_id)
logger.debug('App Name: %s', app_name)
logger.debug('Initial State: %s', initial_state)
```

Then run with debug logging:
```bash
PYTHONPATH=src python -m google.adk.server.app_server 8080 --log-level DEBUG
```

## Remote Debugging

If you need to debug a running server:

1. Install debugpy:
```bash
pip install debugpy
```

2. Add to your code:
```python
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()  # Optional: wait for debugger to attach
```

3. In VS Code, create a "Remote Attach" configuration

## Tips

1. **Use conditional breakpoints**: Right-click on breakpoint → Edit Breakpoint → Add condition
   - Example: `session_id == "8dc29a95411be00600ec264701020100"`

2. **Use logpoints**: Right-click on line → Add Logpoint
   - Logs without stopping execution

3. **Check the Debug Console**: View logs and evaluate expressions while debugging

4. **Use the Call Stack**: See the sequence of function calls that led to the current point

