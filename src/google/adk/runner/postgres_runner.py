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

from typing import Optional

from ..agents.base_agent import BaseAgent
from ..artifacts.in_memory_artifact_service import InMemoryArtifactService
from ..memory.postgres_memory_service import PostgresMemoryService
from ..sessions.postgres_session_service import PostgresSessionService
from ..runners import Runner


class PostgresRunner(Runner):
  """A PostgreSQL-backed Runner matching Java PostgresRunner implementation.

  This runner uses PostgreSQL-backed implementations for session and memory
  services, providing persistent storage for agent execution.

  Attributes:
      agent: The root agent to run.
      app_name: The application name of the runner. Defaults to "ADK_SUPER_AGENT".
  """

  def __init__(
      self,
      agent: Optional[BaseAgent] = None,
      *,
      app_name: Optional[str] = None,
      db_url: Optional[str] = None,
      schema: Optional[str] = None,
  ):
    """Initializes the PostgresRunner.

    Args:
        agent: The root agent to run.
        app_name: The application name of the runner. Defaults to "ADK_SUPER_AGENT".
        db_url: PostgreSQL connection URL. If not provided, reads from environment
          variables.
        schema: Optional PostgreSQL schema name. If not provided, reads from environment
          variable DB_SCHEMA. If None, uses default (public) schema.
    """
    if app_name is None:
      # Always use ADK_SUPER_AGENT as the app name to match GenericOrchestrator
      app_name = 'ADK_SUPER_AGENT'

    session_service = PostgresSessionService(db_url=db_url, schema=schema)
    memory_service = PostgresMemoryService(db_url=db_url, schema=schema)
    # Artifact service - using InMemory for now (can be replaced with PostgresArtifactService later)
    artifact_service = InMemoryArtifactService()

    super().__init__(
        app_name=app_name,
        agent=agent,
        artifact_service=artifact_service,
        session_service=session_service,
        memory_service=memory_service,
    )

