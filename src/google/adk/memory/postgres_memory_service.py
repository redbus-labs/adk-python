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

import logging
from typing import TYPE_CHECKING

from google.genai import types
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from typing_extensions import override

from ..utils.postgres_db_helper import PostgresDBHelper
from ..utils.postgres_db_helper import PostgresEvent
from ..utils.postgres_db_helper import PostgresEventContentPart
from ..utils.postgres_db_helper import PostgresSession
from . import _utils
from .base_memory_service import BaseMemoryService
from .base_memory_service import SearchMemoryResponse
from .memory_entry import MemoryEntry

if TYPE_CHECKING:
  from ..sessions.session import Session

logger = logging.getLogger('google_adk.' + __name__)


class PostgresMemoryService(BaseMemoryService):
  """Memory service using PostgreSQL matching Java implementation."""

  def __init__(self, db_url: str | None = None, schema: str | None = None):
    """Initialize PostgresMemoryService.

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
      logger.info('PostgresMemoryService initialized with db_url: %s', masked_url)
    else:
      logger.info(
          'PostgresMemoryService initialized without db_url, will read from environment'
      )
    self.db_helper = PostgresDBHelper.get_instance(db_url=db_url, schema=schema)

  @override
  async def add_session_to_memory(self, session: Session):
    """Adds a session to the memory service.

    Events are already stored in PostgreSQL by PostgresSessionService, so this
    method can be a no-op or verify events exist.
    """
    logger.debug('Adding session %s to memory (events already stored).', session.id)
    # Events are already stored in PostgreSQL by PostgresSessionService
    # No additional action needed

  @override
  async def search_memory(
      self, *, app_name: str, user_id: str, query: str
  ) -> SearchMemoryResponse:
    """Searches for sessions that match the query."""
    logger.debug(
        'Searching memory for app: %s, user: %s, query: %s', app_name, user_id, query
    )

    response = SearchMemoryResponse()

    try:
      with self.db_helper.get_session() as db_session:
        # Query events and content parts filtered by app_name and user_id
        # Join with sessions table to filter by app_name and user_id
        query_filter = and_(
            PostgresSession.app_name == app_name,
            PostgresSession.user_id == user_id,
            PostgresEventContentPart.text_content.isnot(None),
            func.lower(PostgresEventContentPart.text_content).like(f'%{query.lower()}%'),
        )

        results = (
            db_session.query(PostgresEvent, PostgresEventContentPart, PostgresSession)
            .join(PostgresSession, PostgresEvent.session_id == PostgresSession.id)
            .join(
                PostgresEventContentPart,
                PostgresEvent.id == PostgresEventContentPart.event_id,
            )
            .filter(query_filter)
            .options(joinedload(PostgresEvent.content_parts))
            .all()
        )

        # Convert to MemoryEntry objects
        for pg_event, pg_part, pg_session in results:
          # Only include text parts
          if pg_part.part_type != 'text' or not pg_part.text_content:
            continue

          # Create content from the text part
          content = types.Content(parts=[types.Part(text=pg_part.text_content)])

          memory_entry = MemoryEntry(
              content=content,
              author=pg_event.author,
              timestamp=_utils.format_timestamp(float(pg_event.timestamp)),
          )
          response.memories.append(memory_entry)

        logger.debug('Found %d memory entries for query: %s', len(response.memories), query)
        return response

    except Exception as ex:
      logger.error('Error searching memory: %s', ex, exc_info=True)
      raise

