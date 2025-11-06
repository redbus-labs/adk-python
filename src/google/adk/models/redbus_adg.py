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
import re
from typing import Any
from typing import AsyncGenerator
from typing import Optional

import httpx
from google.genai import types
from typing_extensions import override

from ..tools.base_tool import BaseTool
from .base_llm import BaseLlm
from .llm_request import LlmRequest
from .llm_response import LlmResponse

logger = logging.getLogger('google_adk.' + __name__)

_DEFAULT_API_URL_ENV_VAR = 'ADURL'
_USERNAME_ENV_VAR = 'ADU'
_PASSWORD_ENV_VAR = 'ADP'
_FORBIDDEN_CHARACTERS_REGEX = re.compile(r'[^a-zA-Z0-9_\.-]')
_CONTINUE_OUTPUT_MESSAGE = (
    'Continue output. DO NOT look at this line. ONLY look at the content '
    'before this line and system instruction.'
)


def clean_for_identifier_pattern(input_str: Optional[str]) -> Optional[str]:
  """Cleans a string by removing any characters that are not allowed.

  The allowed pattern is [a-zA-Z0-9_\\.-]. This pattern is typically required
  for names or identifiers.

  Args:
    input_str: The string to clean. Can be None.

  Returns:
    The cleaned string, containing only allowed characters. Returns None if
    the input was None.
  """
  if input_str is None:
    return None
  return _FORBIDDEN_CHARACTERS_REGEX.sub('', input_str)


class RedbusADG(BaseLlm):
  """Redbus AD Gateway to access Azure LLMs.

  This implementation provides a custom LLM interface that connects to an
  Azure LLM gateway API, similar to the Java RedbusADG implementation.
  """

  def __init__(self, model: str):
    """Initialize RedbusADG.

    Args:
      model: The model identifier to use.
    """
    super().__init__(model=model)

  @classmethod
  @override
  def supported_models(cls) -> list[str]:
    """Provides the list of supported models.

    Returns:
      A list of supported models.
    """
    return [
        r'redbus-adg-.*',
        r'redbus.*',
    ]

  @override
  async def generate_content_async(
      self, llm_request: LlmRequest, stream: bool = False
  ) -> AsyncGenerator[LlmResponse, None]:
    """Generates content from the given request.

    Args:
      llm_request: The request to send to the LLM.
      stream: Whether to do streaming call.

    Yields:
      LlmResponse: The model response(s).
    """
    if stream:
      async for response in self._generate_content_stream(llm_request):
        yield response
    else:
      response = await self._generate_content_std(llm_request)
      yield response

  async def _generate_content_std(
      self, llm_request: LlmRequest
  ) -> LlmResponse:
    """Generates content using non-streaming API call.

    Args:
      llm_request: The request to send to the LLM.

    Returns:
      LlmResponse: The model response.
    """
    contents = llm_request.contents
    # Last content must be from the user, otherwise the model won't respond.
    if not contents or (
        contents[-1].role != 'user' and contents[-1].role != 'USER'
    ):
      user_content = types.Content(
          role='user', parts=[types.Part(text=_CONTINUE_OUTPUT_MESSAGE)]
      )
      contents = list(contents) + [user_content]

    # Extract system text
    system_text = ''
    if llm_request.config and llm_request.config.system_instruction:
      system_instruction = llm_request.config.system_instruction
      # Handle both string and Content object (matching Java implementation)
      if isinstance(system_instruction, str):
        system_text = system_instruction
      elif isinstance(system_instruction, types.Content):
        if system_instruction.parts:
          system_text = '\n'.join(
              part.text
              for part in system_instruction.parts
              if part.text
          )

    # Build messages array
    messages = []
    # Add system message
    messages.append({'role': 'system', 'content': system_text})

    # Add user/model messages
    for item in contents:
      message_quantum: dict[str, Any] = {}
      # Map model/assistant to assistant, else user
      if item.role in ('model', 'assistant', 'MODEL', 'ASSISTANT'):
        message_quantum['role'] = 'assistant'
      else:
        message_quantum['role'] = 'user'

      # Handle function response
      if (
          item.parts
          and len(item.parts) > 0
          and item.parts[0].function_response
      ):
        function_response = item.parts[0].function_response
        if function_response.response:
          message_quantum['content'] = json.dumps(
              function_response.response, indent=1
          )
      else:
        # Extract text from parts
        text_parts = [
            part.text for part in item.parts if part and part.text
        ]
        message_quantum['content'] = ' '.join(text_parts)

      messages.append(message_quantum)

    # Build tools/functions array
    functions = []
    for tool_name, tool in llm_request.tools_dict.items():
      base_tool: BaseTool = tool
      declaration = base_tool._get_declaration()
      if not declaration:
        logger.warning(
            "Skipping tool '%s' with missing declaration.", base_tool.name
        )
        continue

      # Build tool map
      tool_map: dict[str, Any] = {}
      tool_map['name'] = clean_for_identifier_pattern(declaration.name or '')
      tool_map['description'] = clean_for_identifier_pattern(
          declaration.description or ''
      )

      # Build parameters if present
      if declaration.parameters:
        parameters_map: dict[str, Any] = {'type': 'object'}
        if declaration.parameters.properties:
          properties_map: dict[str, Any] = {}
          for key, schema in declaration.parameters.properties.items():
            # Convert schema to dict
            schema_dict = self._schema_to_dict(schema)
            # Update type string
            self._update_type_string(schema_dict)
            properties_map[key] = schema_dict
          parameters_map['properties'] = properties_map

        if declaration.parameters.required:
          parameters_map['required'] = declaration.parameters.required

        tool_map['parameters'] = parameters_map

      functions.append(tool_map)

    logger.debug('functions: %s', json.dumps(functions, indent=1))

    model_id = self.model

    # Check if last response has function response
    is_last_response_tool_executed = (
        contents
        and contents[-1].parts
        and len(contents[-1].parts) > 0
        and contents[-1].parts[0].function_response is not None
    )

    # Call LLM
    agent_response = await self._call_llm_chat(
        model_id,
        messages,
        None if is_last_response_tool_executed else (functions if functions else None),
        stream=False,
    )

    # Parse usage metadata
    usage_metadata = self._get_usage_metadata(agent_response)

    # Parse response
    response_quantum: dict[str, Any] = {}
    if 'response' in agent_response:
      response_obj = agent_response['response']
      if 'openAIResponse' in response_obj:
        openai_response = response_obj['openAIResponse']
        if 'choices' in openai_response and len(openai_response['choices']) > 0:
          response_quantum = openai_response['choices'][0]

    # Build LlmResponse
    parts: list[types.Part] = []
    part = self._oai_content_block_to_part(response_quantum)
    parts.append(part)

    # Check if tool call is required
    if (
        'finish_reason' in response_quantum
        and response_quantum['finish_reason'] == 'function_call'
    ):
      function_call = part.function_call
      if function_call:
        content = types.Content(
            role='model',
            parts=[types.Part(function_call=function_call)],
        )
        return LlmResponse(content=content, usage_metadata=usage_metadata)
    else:
      content = types.Content(role='model', parts=parts)
      return LlmResponse(content=content, usage_metadata=usage_metadata)

  async def _generate_content_stream(
      self, llm_request: LlmRequest
  ) -> AsyncGenerator[LlmResponse, None]:
    """Generates content using streaming API call.

    Args:
      llm_request: The request to send to the LLM.

    Yields:
      LlmResponse: The model response chunks.
    """
    contents = llm_request.contents
    if not contents or (
        contents[-1].role != 'user' and contents[-1].role != 'USER'
    ):
      user_content = types.Content(
          role='user', parts=[types.Part(text=_CONTINUE_OUTPUT_MESSAGE)]
      )
      contents = list(contents) + [user_content]

    # Extract system text
    system_text = ''
    if llm_request.config and llm_request.config.system_instruction:
      system_instruction = llm_request.config.system_instruction
      # Handle both string and Content object (matching Java implementation)
      if isinstance(system_instruction, str):
        system_text = system_instruction
      elif isinstance(system_instruction, types.Content):
        if system_instruction.parts:
          system_text = '\n'.join(
              part.text
              for part in system_instruction.parts
              if part.text
          )

    # Build messages array
    messages = []
    messages.append({'role': 'system', 'content': system_text})

    for item in contents:
      message_quantum: dict[str, Any] = {}
      if item.role in ('model', 'assistant', 'MODEL', 'ASSISTANT'):
        message_quantum['role'] = 'assistant'
      else:
        message_quantum['role'] = 'user'

      if (
          item.parts
          and len(item.parts) > 0
          and item.parts[0].function_response
      ):
        function_response = item.parts[0].function_response
        if function_response.response:
          message_quantum['content'] = json.dumps(
              function_response.response, indent=1
          )
      else:
        text_parts = [
            part.text for part in item.parts if part and part.text
        ]
        message_quantum['content'] = ' '.join(text_parts)

      messages.append(message_quantum)

    # Build functions array
    functions = []
    for tool_name, tool in llm_request.tools_dict.items():
      base_tool: BaseTool = tool
      declaration = base_tool._get_declaration()
      if not declaration:
        logger.warning(
            "Skipping tool '%s' with missing declaration.", base_tool.name
        )
        continue

      tool_map: dict[str, Any] = {}
      tool_map['name'] = clean_for_identifier_pattern(declaration.name or '')
      tool_map['description'] = clean_for_identifier_pattern(
          declaration.description or ''
      )

      if declaration.parameters:
        parameters_map: dict[str, Any] = {'type': 'object'}
        if declaration.parameters.properties:
          properties_map: dict[str, Any] = {}
          for key, schema in declaration.parameters.properties.items():
            schema_dict = self._schema_to_dict(schema)
            self._update_type_string(schema_dict)
            properties_map[key] = schema_dict
          parameters_map['properties'] = properties_map

        if declaration.parameters.required:
          parameters_map['required'] = declaration.parameters.required

        tool_map['parameters'] = parameters_map

      functions.append(tool_map)

    logger.info('Functions for LLM: %s', json.dumps(functions, indent=1))

    model_id = self.model
    is_last_response_tool_executed = (
        contents
        and contents[-1].parts
        and len(contents[-1].parts) > 0
        and contents[-1].parts[0].function_response is not None
    )

    # Stream responses
    async for response in self._call_llm_chat_stream(
        model_id,
        messages,
        None
        if is_last_response_tool_executed
        else (functions if functions else None),
        stream=True,
    ):
      yield response

  async def _call_llm_chat(
      self,
      model: str,
      messages: list[dict[str, Any]],
      tools: Optional[list[dict[str, Any]]],
      stream: bool,
  ) -> dict[str, Any]:
    """Makes a POST request to the LLM API gateway.

    Args:
      model: The model ID.
      messages: The list of messages.
      tools: The list of tools/functions (can be None).
      stream: Whether to stream.

    Returns:
      The response body as a dict.

    Raises:
      RuntimeError: If environment variables are not set.
    """
    username = os.getenv(_USERNAME_ENV_VAR)
    password = os.getenv(_PASSWORD_ENV_VAR)
    api_url = os.getenv(_DEFAULT_API_URL_ENV_VAR)


    if not username or not username.strip():
      raise RuntimeError(
          f"Environment variable '{_USERNAME_ENV_VAR}' not set."
      )
    if not password or not password.strip():
      raise RuntimeError(
          f"Environment variable '{_PASSWORD_ENV_VAR}' not set."
      )
    if not api_url or not api_url.strip():
      raise RuntimeError(
          f"Environment variable '{_DEFAULT_API_URL_ENV_VAR}' not set."
      )

    payload = {
        'username': username,
        'password': password,
        'api': model,
    }

    request_obj: dict[str, Any] = {
        'messages': messages,
        'temperature': 0.9,
        'stream': stream,
    }

    if tools:
      request_obj['functions'] = tools

    payload['request'] = request_obj
    json_string = json.dumps(payload)
    

    try:
      async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            api_url,
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            content=json_string.encode('utf-8'),
        )

        status_code = response.status_code
        if status_code >= 200 and status_code < 300:
          return response.json()
        else:
          logger.error(
              'HTTP request failed with status code %d: %s',
              status_code,
              response.text,
          )
          return {}

    except Exception as ex:
      logger.error('HTTP request failed during non-streaming call.', exc_info=ex)
      return {}

  async def _call_llm_chat_stream(
      self,
      model: str,
      messages: list[dict[str, Any]],
      tools: Optional[list[dict[str, Any]]],
      stream: bool,
  ) -> AsyncGenerator[LlmResponse, None]:
    """Makes a streaming POST request to the LLM API gateway.

    Args:
      model: The model ID.
      messages: The list of messages.
      tools: The list of tools/functions (can be None).
      stream: Whether to stream.

    Yields:
      LlmResponse: Streaming response chunks.

    Raises:
      RuntimeError: If environment variables are not set.
    """
    username = os.getenv(_USERNAME_ENV_VAR)
    password = os.getenv(_PASSWORD_ENV_VAR)
    api_url = os.getenv(_DEFAULT_API_URL_ENV_VAR)

    if not username or not username.strip():
      raise RuntimeError(
          f"Environment variable '{_USERNAME_ENV_VAR}' not set."
      )
    if not password or not password.strip():
      raise RuntimeError(
          f"Environment variable '{_PASSWORD_ENV_VAR}' not set."
      )
    if not api_url or not api_url.strip():
      raise RuntimeError(
          f"Environment variable '{_DEFAULT_API_URL_ENV_VAR}' not set."
      )

    payload = {
        'username': username,
        'password': password,
        'stream': stream,
        'api': model,
    }

    request_obj: dict[str, Any] = {
        'messages': messages,
        'temperature': 0.9,
        'stream': stream,
    }

    if tools:
      request_obj['functions'] = tools

    payload['request'] = request_obj
    json_string = json.dumps(payload)

    try:
      async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            'POST',
            api_url,
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            content=json_string.encode('utf-8'),
        ) as response:
          if response.status_code < 200 or response.status_code >= 300:
            logger.error(
                'HTTP request failed with status code %d: %s',
                response.status_code,
                await response.aread(),
            )
            return

          # Buffer for accumulating function call arguments per choice index
          function_call_name_buffer: dict[int, str] = {}
          function_call_args_buffer: dict[int, str] = {}
          function_call_detected = False
          accumulated_text = ''

          # Usage tracking variables
          total_prompt_tokens = 0
          total_completion_tokens = 0
          total_tokens = 0

          async for line_bytes in response.aiter_lines():
            line = line_bytes.strip()

            if line.startswith('data:'):
              line = line[5:].strip()

            if line == '[DONE]':
              logger.info('[DONE] marker found, completing stream')
              if accumulated_text and not function_call_detected:
                usage_metadata = self._get_usage_metadata(
                    total_prompt_tokens, total_completion_tokens, total_tokens
                )
                final_response = LlmResponse(
                    content=types.Content(
                        role='model',
                        parts=[types.Part(text=accumulated_text)],
                    ),
                    partial=False,
                    usage_metadata=usage_metadata,
                )
                yield final_response
              break

            if not line:
              continue

            try:
              chunk = json.loads(line)
            except json.JSONDecodeError as e:
              logger.warning('Failed to parse JSON line: %s', e)
              continue
            except Exception as e:
              logger.warning('Error parsing line: %s', e)
              continue

            # Parse usage information if present
            if 'usage' in chunk:
              usage = chunk['usage']
              if usage:
                total_prompt_tokens = max(
                    total_prompt_tokens, usage.get('prompt_tokens', 0)
                )
                total_completion_tokens = max(
                    total_completion_tokens, usage.get('completion_tokens', 0)
                )
                total_tokens = max(total_tokens, usage.get('total_tokens', 0))
                logger.info(
                    'Updated token counts: prompt=%d, completion=%d, total=%d',
                    total_prompt_tokens,
                    total_completion_tokens,
                    total_tokens,
                )

            if 'choices' in chunk:
              choices = chunk['choices']
              if not choices or len(choices) == 0:
                continue

              for i, choice in enumerate(choices):
                if not choice:
                  continue

                done = choice.get('finish_reason') == 'stop'
                delta = choice.get('delta')

                if delta:
                  # Buffer function_call arguments
                  if 'function_call' in delta:
                    # If there's accumulated text, emit it before function call
                    if accumulated_text:
                      aggregated_text_response = LlmResponse(
                          content=types.Content(
                              role='model',
                              parts=[types.Part(text=accumulated_text)],
                          ),
                          partial=False,
                      )
                      logger.info(
                          'Emitting aggregated text before FunctionCall: %s',
                          aggregated_text_response,
                      )
                      yield aggregated_text_response
                      accumulated_text = ''

                    function_call_json = delta['function_call']
                    function_name = function_call_json.get('name')
                    arguments_fragment = function_call_json.get('arguments')

                    if function_name:
                      function_call_name_buffer[i] = function_name
                    if arguments_fragment:
                      if i not in function_call_args_buffer:
                        function_call_args_buffer[i] = ''
                      function_call_args_buffer[i] += arguments_fragment

                  # If finish_reason is function_call, emit the function call event
                  if choice.get('finish_reason') == 'function_call':
                    function_name = function_call_name_buffer.get(i)
                    args_string = function_call_args_buffer.get(i, '')

                    function_args: dict[str, Any] = {}
                    if args_string:
                      try:
                        function_args = json.loads(args_string)
                      except json.JSONDecodeError as e:
                        logger.warning(
                            'Failed to parse accumulated function_call arguments '
                            'as JSON: %s',
                            args_string,
                            exc_info=e,
                        )

                    if function_name:
                      function_call = types.FunctionCall(
                          name=function_name, args=function_args
                      )
                      function_call_response = LlmResponse(
                          content=types.Content(
                              role='model',
                              parts=[types.Part(function_call=function_call)],
                          ),
                          partial=False,
                      )
                      logger.info(
                          'Emitting FunctionCall LlmResponse: %s',
                          function_call_response,
                      )
                      yield function_call_response

                    # Clear buffers for this index
                    function_call_args_buffer.pop(i, None)
                    function_call_name_buffer.pop(i, None)
                    function_call_detected = True

                  # Handle text content as a separate event
                  text = delta.get('content', '')
                  if text:
                    accumulated_text += text
                    text_response = LlmResponse(
                        content=types.Content(
                            role='model', parts=[types.Part(text=text)]
                        ),
                        partial=True,
                    )
                    yield text_response

                elif 'function_call' in choice:
                  # Check function_call directly in choice if delta is null
                  # (matching Java implementation)
                  function_call_json = choice['function_call']
                  function_name = function_call_json.get('name')
                  arguments_fragment = function_call_json.get('arguments')

                  if function_name:
                    function_call_name_buffer[i] = function_name
                  if arguments_fragment:
                    if i not in function_call_args_buffer:
                      function_call_args_buffer[i] = ''
                    function_call_args_buffer[i] += arguments_fragment
                  function_call_detected = True

                elif 'content' in choice:
                  # Handle non-delta content (likely final response)
                  text = choice.get('content', '')
                  if text:
                    final_response = LlmResponse(
                        content=types.Content(
                            role='model', parts=[types.Part(text=text)]
                        ),
                        partial=False,
                    )
                    logger.info('Emitting Final Text LlmResponse: %s', final_response)
                    yield final_response

    except Exception as ex:
      logger.error('HTTP request failed during streaming call.', exc_info=ex)

  def _oai_content_block_to_part(
      self, choice: dict[str, Any]
  ) -> types.Part:
    """Converts OpenAI-like content block to Part.

    This method is specifically for parsing *complete* OpenAI-like content blocks
    in a non-streaming context. It matches the Java implementation.

    Args:
      choice: The choice object from OpenAI-like response.

    Returns:
      A Part object.

    Raises:
      ValueError: If the format is not supported.
    """
    # Check for message object (for non-streaming)
    message = choice.get('message')
    if not message:
      # For streaming, a 'message' object should usually be present.
      # For non-streaming, 'delta' might be directly at the choice level
      # Or directly within 'delta'
      raise ValueError(
          "Input choice does not contain a 'message' object for content parsing."
      )

    # Check for function_call in message
    if 'function_call' in message:
      function = message['function_call']

      if 'name' in function:
        name = function.get('name')
        args: dict[str, Any] = {}

        # Try to get arguments as a JSONObject directly
        if 'arguments' in function:
          arguments_obj = function['arguments']
          if isinstance(arguments_obj, dict):
            args = arguments_obj
          elif isinstance(arguments_obj, str):
            # If not a direct dict, try to parse as stringified JSON
            try:
              args = json.loads(arguments_obj)
            except json.JSONDecodeError as e:
              logger.warning(
                  'Failed to parse function arguments as JSON string: %s',
                  arguments_obj,
                  exc_info=e,
              )
              # Continue with empty args if parsing fails

        if name:
          function_call = types.FunctionCall(name=name, args=args)
          return types.Part(function_call=function_call)

    # Check for content in message
    if 'content' in message:
      content = message['content']
      if isinstance(content, str):
        text = content
        return types.Part(text=text)

    # Fallback if no recognizable content or function call is found
    raise ValueError(
        'Unsupported content block format or missing required fields in '
        f'message: {message}'
    )

  def _get_usage_metadata(
      self,
      agent_response: Optional[dict[str, Any]] = None,
      prompt_tokens: Optional[int] = None,
      completion_tokens: Optional[int] = None,
      total_tokens: Optional[int] = None,
  ) -> Optional[types.GenerateContentResponseUsageMetadata]:
    """Extracts usage metadata from response.

    Args:
      agent_response: The full agent response (for non-streaming).
      prompt_tokens: Prompt tokens (for streaming).
      completion_tokens: Completion tokens (for streaming).
      total_tokens: Total tokens (for streaming).

    Returns:
      Usage metadata if available, None otherwise.
    """
    if agent_response:
      response_obj = agent_response.get('response')
      if response_obj:
        openai_response = response_obj.get('openAIResponse')
        if openai_response:
          usage = openai_response.get('usage')
          if usage:
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            if total_tokens == 0:
              total_tokens = prompt_tokens + completion_tokens

            if total_tokens > 0:
              logger.info(
                  'Non-streaming token counts: prompt=%d, completion=%d, '
                  'total=%d',
                  prompt_tokens,
                  completion_tokens,
                  total_tokens,
              )
              return types.GenerateContentResponseUsageMetadata(
                  prompt_token_count=prompt_tokens,
                  candidates_token_count=completion_tokens,
                  total_token_count=total_tokens,
              )

    if prompt_tokens is not None or completion_tokens is not None:
      if total_tokens is None:
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
      if total_tokens > 0 or (prompt_tokens or 0) > 0 or (completion_tokens or 0) > 0:
        return types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt_tokens or 0,
            candidates_token_count=completion_tokens or 0,
            total_token_count=total_tokens,
        )

    return None

  def _update_type_string(self, value_dict: dict[str, Any]) -> None:
    """Recursively updates type strings to lowercase in schema dict.

    Args:
      value_dict: The schema dict to update.
    """
    if not value_dict:
      return

    if 'type' in value_dict and isinstance(value_dict['type'], str):
      value_dict['type'] = value_dict['type'].lower()

    if 'items' in value_dict:
      items = value_dict['items']
      if isinstance(items, dict):
        self._update_type_string(items)
        if 'properties' in items:
          properties = items['properties']
          if isinstance(properties, dict):
            for value in properties.values():
              if isinstance(value, dict):
                self._update_type_string(value)

  def _schema_to_dict(self, schema: types.Schema) -> dict[str, Any]:
    """Converts a Schema object to a dictionary.

    Args:
      schema: The Schema object to convert.

    Returns:
      A dictionary representation of the schema.
    """
    result: dict[str, Any] = {}
    if schema.type:
      result['type'] = schema.type
    if schema.format:
      result['format'] = schema.format
    if schema.description:
      result['description'] = schema.description
    if schema.enum:
      result['enum'] = schema.enum
    if schema.items:
      result['items'] = self._schema_to_dict(schema.items)
    if schema.properties:
      result['properties'] = {
          k: self._schema_to_dict(v) for k, v in schema.properties.items()
      }
    if schema.required:
      result['required'] = schema.required
    return result

