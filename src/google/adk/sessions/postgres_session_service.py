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

from __future__ import annotations

import copy
import json
import logging
import uuid
from datetime import datetime
from typing import Any
from typing import Optional

from google.genai import types
from sqlalchemy import delete
from sqlalchemy.orm import Session as DBSession
from typing_extensions import override

from ..errors.already_exists_error import AlreadyExistsError
from ..events.event import Event
from ..events.event_actions import EventActions
from ..utils.postgres_db_helper import PostgresDBHelper
from ..utils.postgres_db_helper import PostgresEvent
from ..utils.postgres_db_helper import PostgresEventContentPart
from ..utils.postgres_db_helper import PostgresSession
from .base_session_service import BaseSessionService
from .base_session_service import GetSessionConfig
from .base_session_service import ListSessionsResponse
from .session import Session

logger = logging.getLogger('google_adk.' + __name__)


class PostgresSessionService(BaseSessionService):
  """Session service using PostgreSQL matching Java implementation."""

  def __init__(self, db_url: Optional[str] = None, schema: Optional[str] = None):
    """Initialize PostgresSessionService.

    Args:
        db_url: PostgreSQL connection URL. If not provided, reads from environment
          variables.
        schema: Optional PostgreSQL schema name. If not provided, reads from environment
          variable DB_SCHEMA. If None, uses default (public) schema.
    """
    if db_url:
      from urllib.parse import urlparse
      parsed = urlparse(db_url)
      if parsed.password:
        masked_url = db_url.replace(f':{parsed.password}@', ':***@', 1)
      else:
        masked_url = db_url
      logger.info('PostgresSessionService initialized with db_url: %s', masked_url)
    else:
      logger.info(
          'PostgresSessionService initialized without db_url, will read from environment'
      )
    self.db_helper = PostgresDBHelper.get_instance(db_url=db_url, schema=schema)

  @override
  async def create_session(
      self,
      *,
      app_name: str,
      user_id: str,
      state: Optional[dict[str, Any]] = None,
      session_id: Optional[str] = None,
  ) -> Session:
    """Creates a new session."""
    if not app_name:
      raise ValueError('appName cannot be null')
    if not user_id:
      raise ValueError('userId cannot be null')

    resolved_session_id = (
        session_id.strip() if session_id and session_id.strip() else str(uuid.uuid4())
    )

    initial_state = state or {}
    initial_events: list[Event] = []
    now = datetime.now()

    new_session = Session(
        id=resolved_session_id,
        app_name=app_name,
        user_id=user_id,
        state=initial_state,
        events=initial_events,
        last_update_time=now.timestamp(),
    )

    logger.info('Attempting to create session: %s', resolved_session_id)

    try:
      self._save_session(new_session)
      logger.info('Session %s created successfully.', resolved_session_id)
      return self._copy_session(new_session)
    except Exception as ex:
      logger.error(
          'Error creating session %s: %s',
          resolved_session_id,
          ex,
          exc_info=True,
      )
      logger.error('Session details: app_name=%s, user_id=%s', app_name, user_id)
      logger.error('Exception type: %s', type(ex).__name__)
      logger.error('Exception args: %s', ex.args)
      # Log the full exception message for debugging
      if hasattr(ex, 'orig') and ex.orig:
        logger.error('Database error (orig): %s', ex.orig)
      if hasattr(ex, 'statement') and ex.statement:
        logger.error('SQL statement: %s', ex.statement)
      raise RuntimeError(f'Failed to create session: {resolved_session_id}. Error: {str(ex)}') from ex

  def _copy_session(self, original: Session) -> Session:
    """Creates a deep copy of a Session object."""
    return Session(
        id=original.id,
        app_name=original.app_name,
        user_id=original.user_id,
        state=copy.deepcopy(original.state),
        events=copy.deepcopy(original.events),
        last_update_time=original.last_update_time,
    )

  @override
  async def get_session(
      self,
      *,
      app_name: str,
      user_id: str,
      session_id: str,
      config: Optional[GetSessionConfig] = None,
  ) -> Optional[Session]:
    """Gets a session."""
    if not app_name:
      raise ValueError('appName cannot be null')
    if not user_id:
      raise ValueError('userId cannot be null')
    if not session_id:
      raise ValueError('sessionId cannot be null')

    logger.info(
        'Attempting to get session: %s for app: %s and user: %s',
        session_id,
        app_name,
        user_id,
    )

    try:
      stored_session = self._get_session_from_db(session_id)
      if stored_session is None:
        logger.debug('Session %s not found.', session_id)
        return None

      # Validate that the session belongs to the specified app and user
      if stored_session.app_name != app_name or stored_session.user_id != user_id:
        logger.warn(
            'Session %s found but belongs to different app/user. Expected: %s/%s, Found: %s/%s',
            session_id,
            app_name,
            user_id,
            stored_session.app_name,
            stored_session.user_id,
        )
        return None

      logger.info('Session %s retrieved successfully.', session_id)
      return self._copy_session(stored_session)
    except Exception as ex:
      logger.error('Error getting session %s: %s', session_id, ex, exc_info=True)
      logger.error('Exception type: %s', type(ex).__name__)
      logger.error('Exception args: %s', ex.args)
      if hasattr(ex, '__cause__') and ex.__cause__:
        logger.error('Root cause: %s', ex.__cause__)
      raise RuntimeError(f'Failed to get session: {session_id}') from ex

  @override
  async def list_sessions(
      self, *, app_name: str, user_id: Optional[str] = None
  ) -> ListSessionsResponse:
    """Lists all the sessions for a user."""
    if not app_name:
      raise ValueError('appName cannot be null')

    # TODO: Implement list_sessions functionality
    logger.warn(
        'list_sessions method is not yet implemented for PostgresSessionService. Returning empty response.'
    )
    return ListSessionsResponse(sessions=[])

  @override
  async def delete_session(
      self, *, app_name: str, user_id: str, session_id: str
  ) -> None:
    """Deletes a session."""
    if not app_name:
      raise ValueError('appName cannot be null')
    if not user_id:
      raise ValueError('userId cannot be null')
    if not session_id:
      raise ValueError('sessionId cannot be null')

    logger.info('Attempting to delete session: %s', session_id)

    try:
      with self.db_helper.get_session() as db_session:
        db_session.execute(delete(PostgresSession).where(PostgresSession.id == session_id))
        db_session.commit()
      logger.info('Session %s deleted successfully (or not found).', session_id)
    except Exception as ex:
      logger.error('Error deleting session %s: %s', session_id, ex, exc_info=True)
      raise RuntimeError(f'Failed to delete session: {session_id}') from ex

  @override
  async def append_event(self, session: Session, event: Event) -> Event:
    """Appends an event to a session."""
    if event.partial:
      return event

    if not session:
      raise ValueError('session cannot be null')
    if not event:
      raise ValueError('event cannot be null')
    if not session.app_name:
      raise ValueError('session.appName cannot be null')
    if not session.user_id:
      raise ValueError('session.userId cannot be null')
    if not session.id:
      raise ValueError('session.id cannot be null')

    session_id = session.id
    logger.debug('Attempting to append event to session: %s', session_id)

    try:
      stored_session = self._get_session_from_db(session_id)
      if stored_session is None:
        logger.warn(
            'appendEvent called for session %s which is not found in PostgresSessionService',
            session_id,
        )
        raise ValueError(f'Session not found: {session_id}')

      # Create a new list with the appended event
      updated_events = copy.deepcopy(stored_session.events)
      updated_events.append(event)

      # Create a new session with updated events and timestamp
      now = datetime.now()
      updated_session = Session(
          id=stored_session.id,
          app_name=stored_session.app_name,
          user_id=stored_session.user_id,
          state=copy.deepcopy(stored_session.state),
          events=updated_events,
          last_update_time=now.timestamp(),
      )

      # Save the updated session back to the database
      self._save_session(updated_session)

      logger.debug('Event appended successfully to session %s.', session_id)
      # Call super implementation if there are additional side effects
      await super().append_event(session, event)
      return event
    except Exception as ex:
      logger.error('Error appending event to session %s: %s', session_id, ex, exc_info=True)
      raise RuntimeError(f'Failed to append event to session: {session_id}') from ex

  def _get_session_from_db(self, session_id: str) -> Optional[Session]:
    """Gets a session from the database."""
    try:
      logger.debug('Querying database for session: %s', session_id)
      with self.db_helper.get_session() as db_session:
        logger.debug('Database session obtained, querying PostgresSession')
        pg_session = db_session.query(PostgresSession).filter(
            PostgresSession.id == session_id
        ).first()

        if pg_session is None:
          logger.debug('Session %s not found in database', session_id)
          return None

        logger.debug(
            'Session found: id=%s, app_name=%s, user_id=%s',
            pg_session.id,
            pg_session.app_name,
            pg_session.user_id,
        )

        # Convert database model to Session object
        # Match Java implementation: read events from event_data JSONB column
        logger.debug('Loading events from event_data for session: %s', session_id)
        events = []
        try:
          # Read events from event_data JSONB column (matching Java implementation)
          event_data = pg_session.event_data or {}
          if isinstance(event_data, dict) and 'events' in event_data:
            events_raw = event_data['events']
            logger.debug('Found events in event_data: type=%s', type(events_raw))
            
            # Handle both formats:
            # 1. Python format: events is already a list of dicts
            # 2. Java format: events is a JSON string that needs to be parsed
            events_list = None
            if isinstance(events_raw, list):
              # Python format: already a list
              events_list = events_raw
            elif isinstance(events_raw, str):
              # Java format: events is a JSON string, parse it
              try:
                # Remove quotes if double-encoded (matching Java's insertEvents logic)
                raw = events_raw
                if raw.startswith('"') and raw.endswith('"'):
                  raw = raw[1:-1].replace('\\"', '"')
                # Parse the JSON string to get the array
                events_list = json.loads(raw)
              except json.JSONDecodeError as parse_error:
                logger.warning(
                    'Error parsing events JSON string for session %s: %s',
                    session_id,
                    parse_error,
                )
                events_list = None
            else:
              logger.warning(
                  'Unexpected events format in event_data for session %s: %s',
                  session_id,
                  type(events_raw),
              )
            
            if events_list and isinstance(events_list, list):
              logger.debug('Found events array in event_data: %d events', len(events_list))
              for event_json in events_list:
                try:
                  # Convert event JSON dict to Event object
                  event = Event.model_validate(event_json)
                  events.append(event)
                except Exception as event_error:
                  logger.warning(
                      'Error converting event JSON to Event: %s. Skipping event.',
                      event_error,
                  )
                  logger.debug('Event JSON that failed: %s', event_json)
            else:
              logger.debug('No valid events array found in event_data for session: %s', session_id)
          else:
            logger.debug('No events found in event_data for session: %s', session_id)
        except Exception as events_error:
          logger.warning(
              'Error loading events from event_data for session %s: %s. Continuing without events.',
              session_id,
              events_error,
              exc_info=True,
          )
          # Continue without events rather than failing

        logger.debug('Loaded %d events for session: %s', len(events), session_id)

        # Parse state - ensure it's a dict
        state = pg_session.state or {}
        if not isinstance(state, dict):
          logger.warning(
              'Session %s state is not a dict: %s. Converting to empty dict.',
              session_id,
              type(state),
          )
          state = {}

        # Convert last_update_time to timestamp
        try:
          if isinstance(pg_session.last_update_time, datetime):
            last_update_timestamp = pg_session.last_update_time.timestamp()
          else:
            # If it's already a timestamp or something else
            logger.warning(
                'Session %s last_update_time is not datetime: %s. Using current time.',
                session_id,
                type(pg_session.last_update_time),
            )
            last_update_timestamp = datetime.now().timestamp()
        except Exception as time_error:
          logger.error(
              'Error converting last_update_time for session %s: %s. Using current time.',
              session_id,
              time_error,
          )
          last_update_timestamp = datetime.now().timestamp()

        return Session(
            id=pg_session.id,
            app_name=pg_session.app_name,
            user_id=pg_session.user_id,
            state=state,
            events=events,
            last_update_time=last_update_timestamp,
        )
    except Exception as e:
      logger.error(
          'Error in _get_session_from_db for session %s: %s',
          session_id,
          e,
          exc_info=True,
      )
      logger.error('Exception type: %s', type(e).__name__)
      logger.error('Exception message: %s', str(e))
      raise

  def _save_session(self, session: Session) -> None:
    """Saves a session to the database."""
    try:
      logger.debug(
          'Saving session to database: id=%s, app_name=%s, user_id=%s',
          session.id,
          session.app_name,
          session.user_id,
      )
      with self.db_helper.get_session() as db_session:
        # Upsert the main session data
        logger.debug('Querying for existing session: %s', session.id)
        pg_session = (
            db_session.query(PostgresSession).filter(PostgresSession.id == session.id).first()
        )

        event_data = {'events': [e.model_dump(mode='json') for e in session.events]}
        logger.debug('Event data prepared: %d events', len(session.events))

        if pg_session is None:
          logger.debug('Creating new PostgresSession object')
          pg_session = PostgresSession(
              id=session.id,
              app_name=session.app_name,
              user_id=session.user_id,
              state=session.state,
              last_update_time=datetime.fromtimestamp(session.last_update_time),
              event_data=event_data,
          )
          logger.debug('Adding new session to database session')
          db_session.add(pg_session)
        else:
          logger.debug('Updating existing session')
          pg_session.app_name = session.app_name
          pg_session.user_id = session.user_id
          pg_session.state = session.state
          pg_session.last_update_time = datetime.fromtimestamp(session.last_update_time)
          pg_session.event_data = event_data

        logger.debug('Committing session data')
        db_session.commit()
        logger.debug('Session data committed successfully')

        # Insert/update events
        logger.debug('Inserting events')
        self._insert_events(db_session, session)
        logger.debug('Events inserted')

        logger.debug('Committing events')
        db_session.commit()
        logger.debug('Session %s saved/updated successfully.', session.id)
    except Exception as e:
      logger.error(
          'Error in _save_session for session %s: %s',
          session.id,
          e,
          exc_info=True,
      )
      logger.error('Session state: %s', session.state)
      logger.error('Session events count: %d', len(session.events))
      raise

  def _insert_events(self, db_session: DBSession, session: Session) -> None:
    """Inserts events into the database."""
    try:
      for event in session.events:
        # Delete existing event and content parts
        db_session.execute(delete(PostgresEventContentPart).where(
            PostgresEventContentPart.event_id == event.id
        ))
        db_session.execute(delete(PostgresEvent).where(PostgresEvent.id == event.id))

        # Create event
        actions = event.actions or EventActions()
        pg_event = PostgresEvent(
            id=event.id,
            session_id=session.id,
            author=event.author,
            actions_state_delta=actions.state_delta or {},
            actions_artifact_delta=actions.artifact_delta or {},
            actions_requested_auth_configs=actions.requested_auth_configs or [],
            actions_transfer_to_agent=actions.transfer_to_agent,
            content_role=event.content.role if event.content else None,
            timestamp=int(event.timestamp),
            invocation_id=event.invocation_id,
        )
        db_session.add(pg_event)

        # Insert content parts
        if event.content and event.content.parts:
          for part in event.content.parts:
            if part.text is not None:
              part_type = 'text'
              text_content = part.text
              function_call_id = None
              function_call_name = None
              function_call_args = None
              function_response_id = None
              function_response_name = None
              function_response_data = None
            elif part.function_call is not None:
              part_type = 'functionCall'
              text_content = None
              function_call_id = part.function_call.id
              function_call_name = part.function_call.name
              function_call_args = part.function_call.args
              function_response_id = None
              function_response_name = None
              function_response_data = None
            elif part.function_response is not None:
              part_type = 'functionResponse'
              text_content = None
              function_call_id = None
              function_call_name = None
              function_call_args = None
              function_response_id = part.function_response.id
              function_response_name = part.function_response.name
              function_response_data = part.function_response.response
            else:
              continue

            pg_part = PostgresEventContentPart(
                event_id=event.id,
                session_id=session.id,
                part_type=part_type,
                text_content=text_content,
                function_call_id=function_call_id,
                function_call_name=function_call_name,
                function_call_args=function_call_args,
                function_response_id=function_response_id,
                function_response_name=function_response_name,
                function_response_data=function_response_data,
            )
            db_session.add(pg_part)

    except Exception as ex:
      logger.error(
          'Error inserting events for session %s. Rolling back transaction.',
          session.id,
          exc_info=True,
      )
      db_session.rollback()
      raise

  def _pg_event_to_event(self, pg_event: PostgresEvent) -> Event:
    """Converts a PostgresEvent to an Event."""
    # Reconstruct content from content parts
    parts = []
    for pg_part in pg_event.content_parts:
      if pg_part.part_type == 'text':
        parts.append(types.Part(text=pg_part.text_content))
      elif pg_part.part_type == 'functionCall':
        parts.append(
            types.Part(
                function_call=types.FunctionCall(
                    id=pg_part.function_call_id or '',
                    name=pg_part.function_call_name or '',
                    args=pg_part.function_call_args or {},
                )
            )
        )
      elif pg_part.part_type == 'functionResponse':
        parts.append(
            types.Part(
                function_response=types.FunctionResponse(
                    id=pg_part.function_response_id or '',
                    name=pg_part.function_response_name or '',
                    response=pg_part.function_response_data or {},
                )
            )
        )

    content = types.Content(parts=parts, role=pg_event.content_role) if parts else None

    # Reconstruct actions
    actions = EventActions(
        state_delta=pg_event.actions_state_delta or {},
        artifact_delta=pg_event.actions_artifact_delta or {},
        requested_auth_configs=pg_event.actions_requested_auth_configs or [],
        transfer_to_agent=pg_event.actions_transfer_to_agent,
    )

    return Event(
        id=pg_event.id,
        invocation_id=pg_event.invocation_id or '',
        author=pg_event.author,
        timestamp=float(pg_event.timestamp),
        content=content,
        actions=actions,
    )

