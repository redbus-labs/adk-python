#!/usr/bin/env python3
"""Example showing how Java code maps to Python in ADK.

This file demonstrates the mapping between Java RxJava patterns and Python async/await.
"""

# ============================================================================
# JAVA CODE (Reference):
# ============================================================================
"""
ConcurrentMap<String, Object> state = new ConcurrentHashMap<>();

Session session = this.runner
    .sessionService()
    .getSession(GenericOrchestrator.name, appName, itemUUid, null)
    .blockingGet();

if (session == null)
  session = this.runner
      .sessionService()
      .createSession(GenericOrchestrator.name, appName, state, itemUUid)
      .blockingGet();

Content userContent = Content.fromParts(Part.fromText(userMsg));

Flowable<Event> events = this.runner.runAsync(appName, session.id(), userContent);

events.blockingForEach(event -> response.put("message", event.stringifyContent()));
"""

# ============================================================================
# PYTHON EQUIVALENT (Current Implementation):
# ============================================================================

from typing import Optional
from google.genai import types


# 1. STATE: ConcurrentHashMap -> Regular dict
# ============================================
# Java: ConcurrentMap<String, Object> state = new ConcurrentHashMap<>();
# Python: Regular dict (FastAPI handles concurrency with async context)
initial_state: dict[str, object] = {}
# OR if you need thread-safety (rarely needed in async context):
# from threading import Lock
# state_lock = Lock()
# with state_lock:
#     initial_state['key'] = 'value'


# 2. SESSION RETRIEVAL: blockingGet() -> await
# ==============================================
# Java: session = runner.sessionService().getSession(...).blockingGet()
# Python: async/await pattern
async def get_or_create_session_example():
  # Get session (non-blocking async call)
  session = await runner.session_service.get_session(
      app_name=app_name,
      user_id=user_id,
      session_id=session_id,
  )
  
  # Create if null (same pattern)
  if session is None:
    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )
  
  return session


# 3. CONTENT CREATION: Same pattern
# ==================================
# Java: Content.fromParts(Part.fromText(userMsg))
# Python: types.Content(role='user', parts=[types.Part(text=user_message)])
user_content = types.Content(
    role='user',
    parts=[types.Part(text='Hello, how are you?')]
)


# 4. EVENT STREAMING: Flowable<Event> -> AsyncGenerator[Event, None]
# ====================================================================
# Java: Flowable<Event> events = runner.runAsync(...)
# Python: AsyncGenerator[Event, None] via async for
async def process_events_example():
  # Run agent and iterate over events
  async for event in runner.run_async(
      user_id=user_id,
      session_id=session.id,
      new_message=user_content,
  ):
    # Process each event (equivalent to blockingForEach)
    event_json = event.model_dump_json()
    # In FastAPI, we yield this for SSE streaming
    yield f'data: {event_json}\n\n'


# ============================================================================
# COMPLETE EXAMPLE (from postgres_app_server.py):
# ============================================================================

async def chat_endpoint_example(request):
  """Complete example showing the full flow."""
  
  # 1. Create state (equivalent to ConcurrentHashMap)
  initial_state = {}
  if business_unit:
    initial_state['business_unit'] = business_unit
  if country:
    initial_state['country'] = country
  
  # 2. Get or create session (blockingGet() -> await)
  session = await runner.session_service.get_session(
      app_name=app_name,
      user_id=user_id,
      session_id=session_id,
  )
  
  if session is None:
    session = await runner.session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )
  
  # 3. Create content
  new_message = types.Content(
      role='user',
      parts=[types.Part(text=user_message)]
  )
  
  # 4. Stream events (Flowable -> AsyncGenerator)
  async def event_generator():
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=new_message,
    ):
      # Equivalent to: event.stringifyContent()
      yield f'data: {event.model_dump_json()}\n\n'
    yield 'data: [DONE]\n\n'
  
  return StreamingResponse(event_generator(), media_type='text/event-stream')


# ============================================================================
# KEY DIFFERENCES:
# ============================================================================
"""
1. Thread Safety:
   - Java: ConcurrentHashMap for thread-safe state
   - Python: Regular dict (FastAPI async context is single-threaded per request)

2. Async Operations:
   - Java: .blockingGet() blocks the thread
   - Python: await doesn't block, yields control to event loop

3. Reactive Streams:
   - Java: Flowable<T> (RxJava reactive stream)
   - Python: AsyncGenerator[T, None] (async iterator)

4. Iteration:
   - Java: .blockingForEach() blocks and processes each item
   - Python: async for yields control and processes items asynchronously

5. Error Handling:
   - Java: Exceptions in Flowable can be caught with onError
   - Python: try/except around async for loop
"""

