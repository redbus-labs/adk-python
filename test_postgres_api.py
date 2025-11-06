#!/usr/bin/env python3
"""Simple test script to verify the Postgres ADK API server works."""

import asyncio
import json
import sys
from typing import Optional

import httpx


async def test_chat_endpoint(
    base_url: str = 'http://localhost:8000',
    message: str = 'Hello, how are you?',
    session_id: Optional[str] = None,
    user_id: str = 'test_user',
):
  """Test the /chat endpoint."""
  url = f'{base_url}/chat'
  payload = {
      'message': message,
      'user_id': user_id,
      'session_id': session_id,
  }

  print(f'Testing POST {url}')
  print(f'Payload: {json.dumps(payload, indent=2)}')

  async with httpx.AsyncClient(timeout=30.0) as client:
    try:
      async with client.stream('POST', url, json=payload) as response:
        print(f'Status Code: {response.status_code}')
        if response.status_code != 200:
          print(f'Error: {await response.aread()}')
          return

        print('\nStreaming events:')
        print('=' * 50)
        async for line in response.aiter_lines():
          if line.startswith('data: '):
            data = line[6:]  # Remove 'data: ' prefix
            if data == '[DONE]':
              print('\n[DONE]')
              break
            try:
              event = json.loads(data)
              if event.get('content') and event.get('content').get('parts'):
                text = ' '.join(
                    part.get('text', '')
                    for part in event['content']['parts']
                    if part.get('text')
                )
                if text:
                  print(f"[{event.get('author', 'unknown')}]: {text}")
            except json.JSONDecodeError:
              print(f'Raw data: {data}')

    except httpx.TimeoutException:
      print('Request timed out')
    except Exception as e:
      print(f'Error: {e}', file=sys.stderr)
      import traceback

      traceback.print_exc()


async def test_health_endpoint(base_url: str = 'http://localhost:8000'):
  """Test the /health endpoint."""
  url = f'{base_url}/health'
  print(f'\nTesting GET {url}')

  async with httpx.AsyncClient(timeout=5.0) as client:
    try:
      response = await client.get(url)
      print(f'Status Code: {response.status_code}')
      print(f'Response: {response.json()}')
    except Exception as e:
      print(f'Error: {e}', file=sys.stderr)


async def main():
  """Main test function."""
  base_url = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
  message = sys.argv[2] if len(sys.argv) > 2 else 'Hello, how are you?'

  print('=' * 50)
  print('Postgres ADK API Server Test')
  print('=' * 50)

  # Test health endpoint first
  await test_health_endpoint(base_url)

  # Test chat endpoint
  print('\n' + '=' * 50)
  await test_chat_endpoint(base_url, message)

  print('\n' + '=' * 50)
  print('Test completed!')


if __name__ == '__main__':
  asyncio.run(main())

