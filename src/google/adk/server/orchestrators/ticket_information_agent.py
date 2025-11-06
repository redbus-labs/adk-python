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
from typing import Optional

from dotenv import load_dotenv

from ...agents.base_agent import BaseAgent
from ...agents.llm_agent import LlmAgent

logger = logging.getLogger('google_adk.' + __name__)

NAME = 'Ticket_Information_Agent'

INSTRUCTION = """
# You are an intelligent support agent helping customers with information related to the user's query.
# Follow these instructions strictly:

## Rule 1: After providing an answer, ask: 'Did you find my answer helpful?' in the same language as the user.
- If the user confirms (e.g., "yes", "||ANSWER HELPED USER||"), respond with: "||ANSWER HELPED USER||" and "I'm glad that I could help you!" in the same language as the user.
- If the user indicates the answer wasn't helpful, reply with: "I'm sorry that I couldn't help you." in the same language as the user.
- Do NOT ask open-ended follow-up questions like "Do you need any further help?".
## Rule 2: ALWAYS reply in the same language as the recent user messages, and **STRICTLY** keep the answer in english
## Rule 3: ALWAYS Call the Functions to get the updated Response. 
"""

DESCRIPTION = (
    'Agent responsible for providing information related to the user\'s query only.'
)


def init_agent() -> Optional[BaseAgent]:
  """Initialize the Ticket Information Agent.

  Returns:
      BaseAgent which helps in getting the information related to the user's query
      using the functions provided.
  """
  try:
    agent = LlmAgent(
        name=NAME,
        model='gemini-2.0-flash',
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        # TODO: Add tools when implementing the full functionality
        # tools=[
        #     FunctionTool.create(get_ticket_details),
        #     FunctionTool.create(get_bus_details),
        #     ...
        # ],
    )

    return agent

  except Exception as ex:
    logger.error('Error initializing TicketInformationAgent: %s', ex, exc_info=True)
    return None

