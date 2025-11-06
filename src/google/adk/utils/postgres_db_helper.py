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

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from typing import Optional

from sqlalchemy import BigInteger
from sqlalchemy import create_engine
from sqlalchemy import Dialect
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import DateTime
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger('google_adk.' + __name__)


class PostgresJSONB(TypeDecorator):
  """A JSONB type for PostgreSQL."""

  impl = Text
  cache_ok = True

  def load_dialect_impl(self, dialect: Dialect):
    if dialect.name == 'postgresql':
      return dialect.type_descriptor(postgresql.JSONB)
    return dialect.type_descriptor(Text)

  def process_bind_param(self, value, dialect: Dialect):
    if value is not None:
      if dialect.name == 'postgresql':
        return value
      return json.dumps(value)
    return value

  def process_result_value(self, value, dialect: Dialect):
    if value is not None:
      if dialect.name == 'postgresql':
        return value
      return json.loads(value)
    return value


class Base(DeclarativeBase):
  """Base class for database tables."""

  pass


# Module-level schema variable (can be set by PostgresDBHelper)
_DB_SCHEMA: Optional[str] = None


class PostgresSession(Base):
  """Represents a session stored in PostgreSQL matching Java schema."""

  __tablename__ = 'sessions'
  __table_args__ = {}  # Will be updated dynamically in PostgresDBHelper.__init__

  id: Mapped[str] = mapped_column(String(255), primary_key=True)
  app_name: Mapped[str] = mapped_column(String(255))
  user_id: Mapped[str] = mapped_column(String(255))
  state: Mapped[dict[str, Any]] = mapped_column(PostgresJSONB, default={})
  last_update_time: Mapped[datetime] = mapped_column(DateTime)
  event_data: Mapped[dict[str, Any]] = mapped_column(PostgresJSONB, default={})

  events: Mapped[list['PostgresEvent']] = relationship(
      'PostgresEvent',
      back_populates='session',
      cascade='all, delete-orphan',
  )


class PostgresEvent(Base):
  """Represents an event stored in PostgreSQL matching Java schema."""

  __tablename__ = 'events'
  __table_args__ = {}  # Will be updated dynamically in PostgresDBHelper.__init__

  id: Mapped[str] = mapped_column(String(255), primary_key=True)
  session_id: Mapped[str] = mapped_column(
      String(255), ForeignKey('sessions.id', ondelete='CASCADE')
  )
  author: Mapped[str] = mapped_column(String(255))
  actions_state_delta: Mapped[dict[str, Any]] = mapped_column(
      PostgresJSONB, default={}
  )
  actions_artifact_delta: Mapped[dict[str, Any]] = mapped_column(
      PostgresJSONB, default={}
  )
  actions_requested_auth_configs: Mapped[dict[str, Any]] = mapped_column(
      PostgresJSONB, default={}
  )
  actions_transfer_to_agent: Mapped[Optional[str]] = mapped_column(
      String(255), nullable=True
  )
  content_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
  timestamp: Mapped[int] = mapped_column(BigInteger)
  invocation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

  session: Mapped[PostgresSession] = relationship(
      'PostgresSession', back_populates='events'
  )
  content_parts: Mapped[list['PostgresEventContentPart']] = relationship(
      'PostgresEventContentPart',
      back_populates='event',
      cascade='all, delete-orphan',
  )


class PostgresEventContentPart(Base):
  """Represents an event content part stored in PostgreSQL matching Java schema."""

  __tablename__ = 'event_content_parts'
  __table_args__ = {}  # Will be updated dynamically in PostgresDBHelper.__init__

  event_id: Mapped[str] = mapped_column(
      String(255), ForeignKey('events.id', ondelete='CASCADE'), primary_key=True
  )
  session_id: Mapped[str] = mapped_column(String(255))
  part_type: Mapped[str] = mapped_column(
      String(50)
  )  # "text", "functionCall", "functionResponse"
  text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
  function_call_id: Mapped[Optional[str]] = mapped_column(
      String(255), nullable=True
  )
  function_call_name: Mapped[Optional[str]] = mapped_column(
      String(255), nullable=True
  )
  function_call_args: Mapped[Optional[dict[str, Any]]] = mapped_column(
      PostgresJSONB, nullable=True
  )
  function_response_id: Mapped[Optional[str]] = mapped_column(
      String(255), nullable=True
  )
  function_response_name: Mapped[Optional[str]] = mapped_column(
      String(255), nullable=True
  )
  function_response_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
      PostgresJSONB, nullable=True
  )

  event: Mapped[PostgresEvent] = relationship(
      'PostgresEvent', back_populates='content_parts'
  )


class PostgresDBHelper:
  """Helper class for PostgreSQL database operations matching Java implementation."""

  _instance: Optional['PostgresDBHelper'] = None
  _lock = None

  def __init__(self, db_url: str, schema: Optional[str] = None):
    """Initialize the PostgreSQL database helper.

    Args:
        db_url: PostgreSQL connection URL (e.g., postgresql://user:pass@host/db)
        schema: Optional PostgreSQL schema name. If provided, tables will use this schema.
          If None, tables will use the default (public) schema.

    Raises:
        ValueError: If db_url is empty or None.
        sqlalchemy.exc.ArgumentError: If db_url format is invalid.
    """
    if not db_url or not db_url.strip():
      raise ValueError(
          'Database URL cannot be empty. Please provide a valid PostgreSQL connection URL.'
      )

    db_url = db_url.strip()

    # Validate URL format
    if not db_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
      raise ValueError(
          f'Invalid database URL format. Expected postgresql:// or postgresql+psycopg2://, '
          f'got: {db_url[:50]}...'
      )

    # Set schema (can be None for default/public schema)
    global _DB_SCHEMA
    _DB_SCHEMA = schema
    self.schema = schema

    # Update table schema for all models
    # SQLAlchemy creates Table objects lazily, so we need to ensure they exist
    # and update both __table_args__ and the Table object's schema property
    if schema:
      PostgresSession.__table_args__ = {'schema': schema}
      PostgresEvent.__table_args__ = {'schema': schema}
      PostgresEventContentPart.__table_args__ = {'schema': schema}
      # Trigger table metadata creation if not already created, then update schema
      # Accessing __table__ will trigger its creation if it doesn't exist
      try:
        PostgresSession.__table__.schema = schema
        logger.debug('Updated PostgresSession.__table__.schema to: %s', schema)
      except AttributeError:
        logger.warning('PostgresSession.__table__ not yet created, schema will be set via __table_args__')
      try:
        PostgresEvent.__table__.schema = schema
        logger.debug('Updated PostgresEvent.__table__.schema to: %s', schema)
      except AttributeError:
        logger.warning('PostgresEvent.__table__ not yet created, schema will be set via __table_args__')
      try:
        PostgresEventContentPart.__table__.schema = schema
        logger.debug('Updated PostgresEventContentPart.__table__.schema to: %s', schema)
      except AttributeError:
        logger.warning('PostgresEventContentPart.__table__ not yet created, schema will be set via __table_args__')
    else:
      # Remove schema to use default (public) schema
      PostgresSession.__table_args__ = {}
      PostgresEvent.__table_args__ = {}
      PostgresEventContentPart.__table_args__ = {}
      # Update the actual Table object's schema to None (default/public)
      try:
        PostgresSession.__table__.schema = None
        logger.debug('Updated PostgresSession.__table__.schema to None (default)')
      except AttributeError:
        pass  # Table not created yet, will use default schema
      try:
        PostgresEvent.__table__.schema = None
        logger.debug('Updated PostgresEvent.__table__.schema to None (default)')
      except AttributeError:
        pass  # Table not created yet, will use default schema
      try:
        PostgresEventContentPart.__table__.schema = None
        logger.debug('Updated PostgresEventContentPart.__table__.schema to None (default)')
      except AttributeError:
        pass  # Table not created yet, will use default schema

    try:
      self.db_url = db_url
      self.engine: Engine = create_engine(db_url)
      self.session_factory = sessionmaker(bind=self.engine)

      if schema:
        logger.info(
            'PostgresDBHelper initialized with database URL. '
            'Using schema: %s',
            schema,
        )
      else:
        logger.info(
            'PostgresDBHelper initialized with database URL. '
            'Using default (public) schema.'
        )
    except Exception as e:
      logger.error(
          'Failed to create database engine with URL: %s... Error: %s',
          db_url[:50] if len(db_url) > 50 else db_url,
          str(e),
      )
      raise

  @classmethod
  def get_instance(
      cls, db_url: Optional[str] = None, schema: Optional[str] = None
  ) -> 'PostgresDBHelper':
    """Get singleton instance of PostgresDBHelper.

    Args:
        db_url: PostgreSQL connection URL. If not provided, reads from environment
          variables in this order:
          1. DATABASE_URL (standard)
          2. POSTGRES_URL
          3. DB_URL
          4. DBURL, DBUSER, DBPASSWORD (legacy format)
        schema: Optional PostgreSQL schema name. If not provided, reads from environment
          variable DB_SCHEMA. If None, uses default (public) schema.

    Returns:
        PostgresDBHelper instance.
    """
    # Resolve schema from parameter or environment
    resolved_schema = schema
    if resolved_schema is None:
      resolved_schema = os.getenv('DB_SCHEMA') or os.getenv('POSTGRES_SCHEMA')
      if resolved_schema:
        resolved_schema = resolved_schema.strip()
        if not resolved_schema:
          resolved_schema = None

    # Normalize db_url from parameter or environment
    resolved_db_url = db_url

    if resolved_db_url is None:
      # Try standard environment variables first
      resolved_db_url = (
          os.getenv('DATABASE_URL')
          or os.getenv('POSTGRES_URL')
          or os.getenv('DB_URL')
      )

      # If still None, try legacy format: DBURL, DBUSER, DBPASSWORD
      if resolved_db_url is None:
        db_url_env = os.getenv('DBURL')
        db_user = os.getenv('DBUSER')
        db_password = os.getenv('DBPASSWORD')
        if db_url_env and db_user and db_password:
          # Parse DBURL to construct full connection string
          # DBURL might be just host:port/db or full URL
          if not db_url_env.startswith('postgresql://'):
            from urllib.parse import quote_plus

            encoded_user = quote_plus(db_user)
            encoded_password = quote_plus(db_password)
            resolved_db_url = f'postgresql://{encoded_user}:{encoded_password}@{db_url_env}'
          else:
            resolved_db_url = db_url_env

    # Validate resolved URL
    if resolved_db_url is None:
      raise ValueError(
          'Database URL not provided and no environment variables found. '
          'Please set DATABASE_URL, POSTGRES_URL, DB_URL, or DBURL/DBUSER/DBPASSWORD.'
      )

    if not resolved_db_url.strip():
      raise ValueError('Database URL from environment variable is empty.')

    # Log the URL being used (mask password)
    from urllib.parse import urlparse
    parsed = urlparse(resolved_db_url)
    if parsed.password:
      masked_url = resolved_db_url.replace(f':{parsed.password}@', ':***@', 1)
    else:
      masked_url = resolved_db_url
    logger.info('PostgresDBHelper using database URL: %s', masked_url)
    logger.info('PostgresDBHelper username: %s', parsed.username or 'NOT SET')
    logger.info('PostgresDBHelper host: %s', parsed.hostname or 'NOT SET')
    if not parsed.username:
      logger.error(
          'WARNING: Database URL has no username! This will cause authentication failures. '
          'URL: %s',
          masked_url,
      )

    # Create or update instance if URL or schema changed
    if cls._instance is None:
      logger.info('Creating new PostgresDBHelper instance')
      cls._instance = cls(resolved_db_url, schema=resolved_schema)
    elif (
        cls._instance.db_url != resolved_db_url
        or cls._instance.schema != resolved_schema
    ):
      logger.warning(
          'PostgresDBHelper instance already exists with different URL or schema. '
          'Recreating with new configuration: URL=%s, schema=%s',
          masked_url,
          resolved_schema or 'default',
      )
      cls._instance = cls(resolved_db_url, schema=resolved_schema)
    else:
      logger.debug('Using existing PostgresDBHelper instance')

    return cls._instance

  @classmethod
  def reset_instance(cls):
    """Reset the singleton instance (useful for testing)."""
    cls._instance = None

  @contextmanager
  def get_session(self):
    """Get a database session context manager.

    Yields:
        SQLAlchemy session.
    """
    session = self.session_factory()
    try:
      yield session
      session.commit()
    except Exception:
      session.rollback()
      raise
    finally:
      session.close()

