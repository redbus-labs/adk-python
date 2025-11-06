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
import os
from typing import Optional

from ...agents.base_agent import BaseAgent
from ...agents.llm_agent import LlmAgent
from ...models.redbus_adg import RedbusADG

logger = logging.getLogger('google_adk.' + __name__)

NAME = 'ADK_SUPER_AGENT'

INSTRUCTION = (
    'You are an assistant for bus travel. Delegate requests to the appropriate'
    ' sub-agent based on the user\'s query. '
    + 'If the query cannot be handled by any specific agent, or if the user'
    ' explicitly asks to end the conversation, use the `exitLoop` tool. '
    + 'Always try to resolve the user\'s issue before escalating or exiting.'
    + ' The Default Language is English. '
)

DESCRIPTION = 'Main coordinator for bus related queries'


def init_agent() -> Optional[BaseAgent]:
  """Initialize the root agent which is an Orchestrator having multiple sub agents.

  Returns:
      BaseAgent which is an Orchestrator with multiple sub agents.
  """
  try:
    # Try to import TicketInformationAgent if it exists
    try:
      from .ticket_information_agent import init_agent as init_ticket_agent

      ticket_information_agent = init_ticket_agent()
    except ImportError:
      logger.warning(
          'TicketInformationAgent not found. Creating orchestrator without'
          ' sub-agents.'
      )
      ticket_information_agent = None

    # Create the main orchestrator agent using RedbusADG
    # The model ID can be configured via environment variable or defaults to "40"
    # Environment variables required: ADURL, ADU, ADP
    model_id = os.getenv('REDBUS_ADG_MODEL', '40')
    root_agent = LlmAgent(
        name=NAME,
        model=RedbusADG(model=model_id),
        instruction=INSTRUCTION,
        description=DESCRIPTION,
        # sub_agents=[ticket_information_agent] if ticket_information_agent else [],
        
    )

    return root_agent

  except Exception as ex:
    logger.error('Error initializing agent: %s', ex, exc_info=True)
    return None

