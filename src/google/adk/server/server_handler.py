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

from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import StreamingResponse
from google.genai import types

from ..runners import Runner

logger = logging.getLogger('google_adk.' + __name__)


class ServerHandler:
  """Handler for server requests matching Java ServerHandler implementation.

  This class processes HTTP requests and delegates to the runner for agent
  execution, similar to the Java ServerHandler class.
  """

  def __init__(self, runner: Runner):
    """Initialize ServerHandler.

    Args:
        runner: The runner instance to use for agent execution.
    """
    self.runner = runner

  async def handle_chat(self, request: Request) -> StreamingResponse:
    """Handle chat requests matching Java ServerHandler.handle() method.

    Args:
        request: The FastAPI request object.

    Returns:
        StreamingResponse with Server-Sent Events (SSE).

    Raises:
        HTTPException: If request is invalid or runner is not initialized.
    """
    if self.runner is None:
      raise HTTPException(status_code=500, detail='Runner not initialized')

    try:
      body = await request.json()

      # Extract headers
      business_unit = request.headers.get('BUSINESS_UNIT', '')
      country = request.headers.get('COUNTRY', '')
      x_client = request.headers.get('X-CLIENT', '')

      # Extract body fields
      session_id = body.get('session_id')
      user_message = body.get('message')
      order_item_uuid = body.get('orderItemUUID')
      app_name = body.get('app_name') or self.runner.app_name
      user_id = body.get('user_id', 'default')

      if not user_message:
        raise HTTPException(status_code=400, detail='message is required')

      # Use orderItemUUID as session_id if provided and no session_id specified
      if not session_id and order_item_uuid:
        session_id = order_item_uuid

      # Create initial state with headers and order info
      initial_state = {}
      if business_unit:
        initial_state['business_unit'] = business_unit
      if country:
        initial_state['country'] = country
      if x_client:
        initial_state['x_client'] = x_client
      if order_item_uuid:
        initial_state['order_item_uuid'] = order_item_uuid

      # Create or get session
      session = None
      if session_id:
        logger.debug(
            'Attempting to get session: %s for app: %s, user: %s',
            session_id,
            app_name,
            user_id,
        )
        try:
          session = await self.runner.session_service.get_session(
              app_name=app_name, user_id=user_id, session_id=session_id
          )
          logger.debug('Session lookup result: %s', 'found' if session else 'not found')
        except Exception as e:
          logger.warning(
              'Failed to get existing session %s: %s. Creating new session.',
              session_id,
              e,
          )
          session = None

      # Create new session if not found or if no session_id provided
      if session is None:
        session = await self.runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            state=initial_state,
        )

      # Convert user message to Content object
      new_message = types.Content(
          role='user', parts=[types.Part(text=user_message)]
      )

      # Run the agent and stream events
      async def event_generator():
        try:
          async for event in self.runner.run_async(
              user_id=user_id,
              session_id=session.id,
              new_message=new_message,
          ):
            # Convert event to string format (matching Java event.stringifyContent())
            event_json = event.model_dump_json()
            yield f'data: {event_json}\n\n'
          yield 'data: [DONE]\n\n'
        except Exception as e:
          logger.error('Error in event generator: %s', e, exc_info=True)
          yield f'data: {{"error": "{str(e)}"}}\n\n'

      return StreamingResponse(
          event_generator(), media_type='text/event-stream'
      )

    except HTTPException:
      raise
    except Exception as e:
      logger.error('Error handling chat request: %s', e, exc_info=True)
      raise HTTPException(status_code=500, detail=str(e))

  async def handle_health(self) -> dict[str, str]:
    """Handle health check requests.

    Returns:
        Dictionary with status information.
    """
    return {
        'status': 'ok',
        'runner_type': type(self.runner).__name__,
    }

