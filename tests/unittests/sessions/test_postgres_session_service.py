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

from datetime import datetime
from datetime import timezone

from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.events.event import Event
from google.adk.sessions.postgres_session_service import PostgresSessionService
from google.adk.sessions.session import Session
from google.genai import types
import pytest


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_create_get_session():
  """Test creating and getting a session."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'
  state = {'key': 'value'}

  session = await service.create_session(
      app_name=app_name, user_id=user_id, state=state
  )

  assert session.app_name == app_name
  assert session.user_id == user_id
  assert session.id
  assert session.state == state
  assert (
      session.last_update_time
      <= datetime.now().astimezone(timezone.utc).timestamp()
  )

  got_session = await service.get_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

  assert got_session is not None
  assert got_session.app_name == app_name
  assert got_session.user_id == user_id
  assert got_session.id == session.id

  # Cleanup
  await service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_delete_session():
  """Test deleting a session."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'

  session = await service.create_session(app_name=app_name, user_id=user_id)

  await service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

  got_session = await service.get_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

  assert got_session is None


@pytest.mark.asyncio
@pytest.mark.skipif(
    not __import__('os').getenv('TEST_POSTGRES_URL'),
    reason='TEST_POSTGRES_URL environment variable not set',
)
async def test_append_event():
  """Test appending an event to a session."""
  db_url = __import__('os').getenv('TEST_POSTGRES_URL')
  service = PostgresSessionService(db_url=db_url)

  app_name = 'test_app'
  user_id = 'test_user'

  session = await service.create_session(app_name=app_name, user_id=user_id)

  event = Event(
      author='user',
      content=types.Content(parts=[types.Part(text='Hello, world!')]),
  )

  appended_event = await service.append_event(session, event)

  assert appended_event.id == event.id
  assert appended_event.author == 'user'

  # Reload session and verify event was saved
  reloaded_session = await service.get_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

  assert reloaded_session is not None
  assert len(reloaded_session.events) == 1
  assert reloaded_session.events[0].id == event.id

  # Cleanup
  await service.delete_session(
      app_name=app_name, user_id=user_id, session_id=session.id
  )

