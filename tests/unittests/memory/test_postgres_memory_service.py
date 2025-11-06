# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.events.event import Event
from google.adk.memory.postgres_memory_service import PostgresMemoryService
from google.adk.sessions.postgres_session_service import PostgresSessionService
from google.adk.sessions.session import Session
from google.genai import types
import pytest


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_add_session_to_memory():
  """Test adding a session to memory."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  memory_service = PostgresMemoryService(db_url=db_url)
  session_service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'

  # Create a session with events
  session = await session_service.create_session(
      app_name=app_name, user_id=user_id
  )

  event = Event(
      author='user',
      content=types.Content(parts=[types.Part(text='I like Python programming.')]),
  )

  await session_service.append_event(session, event)

  # Add session to memory (no-op, events already stored)
  await memory_service.add_session_to_memory(session)

  # Reload session to ensure it's in database
  reloaded_session = await session_service.get_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

  assert reloaded_session is not None

  # Cleanup
  await session_service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_search_memory():
  """Test searching memory."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  memory_service = PostgresMemoryService(db_url=db_url)
  session_service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'

  # Create a session with events
  session = await session_service.create_session(
      app_name=app_name, user_id=user_id
  )

  event1 = Event(
      author='user',
      content=types.Content(parts=[types.Part(text='I like Python programming.')]),
  )

  event2 = Event(
      author='user',
      content=types.Content(parts=[types.Part(text='Python is great for AI development.')]),
  )

  await session_service.append_event(session, event1)
  await session_service.append_event(session, event2)

  # Add session to memory
  await memory_service.add_session_to_memory(session)

  # Search for "Python"
  result = await memory_service.search_memory(
      app_name=app_name, user_id=user_id, query='Python'
  )

  assert len(result.memories) >= 1
  assert any('Python' in memory.content.parts[0].text for memory in result.memories)

  # Cleanup
  await session_service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_search_memory_case_insensitive():
  """Test that memory search is case-insensitive."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  memory_service = PostgresMemoryService(db_url=db_url)
  session_service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'

  # Create a session with events
  session = await session_service.create_session(
      app_name=app_name, user_id=user_id
  )

  event = Event(
      author='user',
      content=types.Content(parts=[types.Part(text='Python is a programming language.')]),
  )

  await session_service.append_event(session, event)
  await memory_service.add_session_to_memory(session)

  # Search with lowercase
  result_lower = await memory_service.search_memory(
      app_name=app_name, user_id=user_id, query='python'
  )

  # Search with uppercase
  result_upper = await memory_service.search_memory(
      app_name=app_name, user_id=user_id, query='PYTHON'
  )

  assert len(result_lower.memories) >= 1
  assert len(result_upper.memories) >= 1

  # Cleanup
  await session_service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

