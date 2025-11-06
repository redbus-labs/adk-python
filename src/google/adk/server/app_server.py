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

import argparse
import configparser
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
import uvicorn

from ..agents.base_agent import BaseAgent
from ..runner.postgres_runner import PostgresRunner
from ..runners import InMemoryRunner
from ..runners import Runner
from .server_handler import ServerHandler
from .orchestrators.generic_orchestrator import init_agent

# Configure logging to show in terminal (can be disabled via ENABLE_LOGGING env var)
def setup_logging():
  """Setup logging configuration if enabled.
  
  Can be controlled via:
  - Environment variable: ENABLE_LOGGING (set to 'true', '1', 'yes' to enable)
  - Default: enabled (True)
  """
  enable_logging = os.getenv('ENABLE_LOGGING', 'true').lower() in ('true', '1', 'yes', 'on')
  
  if enable_logging:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,  # Override any existing configuration
    )
  else:
    # Disable logging by setting level to CRITICAL (only shows critical errors)
    logging.basicConfig(
        level=logging.CRITICAL,
        force=True,
    )

# Setup logging on module import
setup_logging()

logger = logging.getLogger('google_adk.' + __name__)

app = FastAPI(title='ADK App Server')

# Global runner instance
runner: Optional[Runner] = None
handler: Optional[ServerHandler] = None


def load_properties(
    properties_file_path: str, environment: str = 'production'
) -> dict[str, str]:
  """Load properties from INI config file matching Java PropertiesHelper.

  Args:
      properties_file_path: Path to the config.ini file.
      environment: Environment name (e.g., 'production', 'development').

  Returns:
      Dictionary of configuration properties.
  """
  config = {}
  config_file = Path(properties_file_path)

  if not config_file.exists():
    logger.warning('Config file not found: %s', properties_file_path)
    return config

  try:
    # Use ConfigParser with interpolation disabled to handle URL-encoded passwords
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_file)

    # Load default section
    if parser.has_section('default'):
      for key, value in parser.items('default'):
        config[key] = value

    # Override with environment-specific section
    if parser.has_section(environment):
      for key, value in parser.items(environment):
        config[key] = value

    logger.info('Loaded %d properties from %s (environment: %s)', len(config), properties_file_path, environment)

  except Exception as e:
    logger.error('Error loading config file: %s', e, exc_info=True)

  return config


def normalize_db_url(db_url: Optional[str]) -> Optional[str]:
  """Normalize database URL format.

  Validates and normalizes PostgreSQL URL format.

  Args:
      db_url: Database URL in PostgreSQL format.

  Returns:
      Normalized PostgreSQL URL or None.
  """
  if not db_url:
    return None

  db_url = db_url.strip()

  # Ensure it starts with postgresql://
  if not db_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
    if db_url.startswith('postgresql'):
      db_url = f'postgresql://{db_url[len("postgresql"):]}'
    else:
      logger.warning(
          'Database URL does not start with postgresql://. Adding prefix...'
      )
      db_url = f'postgresql://{db_url}'

  return db_url


def _register_routes() -> None:
  """Register FastAPI routes. Must be called after handler is initialized."""
  @app.post('/chat')
  async def chat(request: Request):
    if handler is None:
      raise HTTPException(status_code=500, detail='Server handler not initialized')
    return await handler.handle_chat(request)

  @app.get('/health')
  async def health():
    if handler is None:
      return {'status': 'error', 'detail': 'Server handler not initialized'}
    return await handler.handle_health()


def create_runner(
    agent: BaseAgent,
    runner_type: str = 'postgres',
    db_url: Optional[str] = None,
    schema: Optional[str] = None,
) -> Runner:
  """Create a runner without fallback.

  Args:
      agent: The root agent to run.
      runner_type: Type of runner ('postgres', 'inmemory', etc.).
      db_url: Database URL for PostgresRunner (optional).
      schema: Optional PostgreSQL schema name. If not provided, reads from environment
        variable DB_SCHEMA. If None, uses default (public) schema.

  Returns:
      Runner instance. No fallback - uses the specified runner type.
  """
  if runner_type.lower() == 'postgres':
    # Normalize JDBC URLs to PostgreSQL format
    db_url = normalize_db_url(db_url)
    logger.info('Creating PostgresRunner with app_name=ADK_SUPER_AGENT...')
    # Always use ADK_SUPER_AGENT as app_name to match GenericOrchestrator
    runner = PostgresRunner(
        agent=agent, app_name='ADK_SUPER_AGENT', db_url=db_url, schema=schema
    )
    logger.info('PostgresRunner created successfully.')
    return runner

  elif runner_type.lower() == 'inmemory':
    logger.info('Creating InMemoryRunner...')
    return InMemoryRunner(agent=agent)

  else:
    raise ValueError(f'Unknown runner type: {runner_type}. Supported: postgres, inmemory')


def main():
  """Main entry point matching AppServer.java."""
  global runner

  # Load .env file explicitly to ensure environment variables are set
  # This is needed because VS Code's envFile might not load before Client initialization
  # Try multiple locations for .env file
  env_file_paths = [
      Path(__file__).parent.parent.parent.parent / '.env',  # Project root from this file
      Path.cwd() / '.env',  # Current working directory
  ]
  
  env_loaded = False
  for env_path in env_file_paths:
    if env_path.exists():
      load_dotenv(env_path, override=True)
      logger.info('Loaded .env file from: %s', env_path)
      env_loaded = True
      break
  
  if not env_loaded:
    logger.warning('No .env file found in: %s', [str(p) for p in env_file_paths])
  
  # Log what DATABASE_URL is set to (masked) for debugging
  db_url_from_env = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('DB_URL')
  if db_url_from_env:
    from urllib.parse import urlparse
    parsed = urlparse(db_url_from_env)
    if parsed.username:
      logger.info('DATABASE_URL found in environment with username: %s', parsed.username)
    else:
      logger.warning('DATABASE_URL found but has no username')

  # Parse command line arguments (matching Java: port, config_file, environment)
  parser = argparse.ArgumentParser(description='ADK App Server')
  parser.add_argument(
      'port',
      type=int,
      nargs='?',
      default=8000,
      help='Port number to run the server on (default: 8000)',
  )
  parser.add_argument(
      '--config',
      type=str,
      default=None,
      help='Path to config.ini file',
  )
  parser.add_argument(
      '--environment',
      type=str,
      default='production',
      help='Environment name (default: production)',
  )
  parser.add_argument(
      '--enable-logging',
      action='store_true',
      help='Enable detailed logging (can also use ENABLE_LOGGING env var)',
  )
  parser.add_argument(
      '--disable-logging',
      action='store_true',
      help='Disable detailed logging',
  )
  
  args = parser.parse_args()
  
  # Override logging setting from command line if provided
  if args.enable_logging:
    os.environ['ENABLE_LOGGING'] = 'true'
    setup_logging()  # Re-run setup with new setting
  elif args.disable_logging:
    os.environ['ENABLE_LOGGING'] = 'false'
    setup_logging()  # Re-run setup with new setting
  
  port = args.port
  
  # Default to config.ini in current directory if it exists, otherwise use Java config path
  default_config_path = Path(__file__).parent.parent.parent.parent / 'config.ini'

  if args.config:
    properties_file_path = args.config
  else:
    if default_config_path.exists():
      properties_file_path = str(default_config_path)
    else:
      # Fallback to Java config path
      properties_file_path = '/Users/arun.parmar/go/src/adk-java/core/config.ini'

  environment = args.environment

  # Load properties from config file
  properties = load_properties(properties_file_path, environment)

  # Get database URL - environment variables take priority over config file
  # This allows environment variables to override config file values
  db_url_env = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('DB_URL')
  
  if db_url_env:
    # Validate the environment variable URL
    from urllib.parse import urlparse
    parsed_env = urlparse(db_url_env)
    if parsed_env.username:
      logger.info('Database URL source: ENVIRONMENT VARIABLE')
      logger.info('Environment URL username: %s', parsed_env.username)
      db_url = db_url_env
    else:
      logger.warning(
          'DATABASE_URL from environment variable has no username. '
          'Falling back to config file.'
      )
      db_url_env = None  # Fall through to config file
    
  if not db_url_env:
    logger.info('Database URL source: CONFIG FILE')
    db_url_config = properties.get('database_url') or properties.get('db_url')
    db_user = properties.get('db_user') or os.getenv('DBUSER')
    db_password = properties.get('db_password') or os.getenv('DBPASSWORD')

    if db_url_config:
      logger.info('Found database_url in config: %s', db_url_config[:50] + '...' if len(db_url_config) > 50 else db_url_config)
      # Parse URL to check if credentials are embedded
      from urllib.parse import urlparse, urlunparse, quote_plus
      parsed = urlparse(db_url_config)
      
      if parsed.username and parsed.password:
        # URL already has credentials - use as-is (password should be URL-encoded in config)
        db_url = db_url_config
        logger.info('Using database URL from config with embedded credentials')
        logger.info('Config URL username: %s', parsed.username)
      elif db_user and db_password:
        # Construct URL from separate credentials
        from urllib.parse import urlunparse, quote_plus

        parsed = urlparse(db_url_config)
        encoded_user = quote_plus(db_user)
        encoded_password = quote_plus(db_password)
        netloc = f'{encoded_user}:{encoded_password}@{parsed.hostname}'
        if parsed.port:
          netloc = f'{netloc}:{parsed.port}'
        db_url = urlunparse(
            ('postgresql', netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
        )
        logger.debug('Constructed database URL from separate db_user and db_password')
      else:
        # Use URL as-is (might work if credentials are in connection string)
        db_url = db_url_config
        logger.warning('Using database URL without explicit credentials - ensure URL includes username/password')

  # Log database URL source (without exposing credentials)
  if db_url:
    # Mask password in URL for logging
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    if parsed.username:
      logger.info('Database URL username: %s', parsed.username)
    if parsed.password:
      masked_url = db_url.replace(f':{parsed.password}@', ':***@', 1)
      logger.info('Database URL found (password masked): %s', masked_url)
    else:
      masked_url = db_url
      logger.info('Database URL found (no password): %s', masked_url)
    logger.info('Database host: %s, port: %s, database: %s', parsed.hostname, parsed.port, parsed.path.lstrip('/'))
  else:
    logger.warning(
        'No database URL found in config or environment variables. '
        'PostgresDBHelper will try to read from environment.'
    )

  # Get runner type from properties
  runner_type = properties.get('runner_type', 'postgres').lower()

  # Get schema from properties or environment
  schema = properties.get('db_schema') or properties.get('schema')
  if not schema:
    schema = os.getenv('DB_SCHEMA') or os.getenv('POSTGRES_SCHEMA')
  if schema:
    schema = schema.strip()
    if not schema:
      schema = None
    logger.info('Using PostgreSQL schema: %s', schema)
  else:
    logger.info('No schema specified, using default (public) schema')

  # Initialize agent using GenericOrchestrator
  root_agent = init_agent()
  if root_agent is None:
    logger.error('Failed to initialize agent from GenericOrchestrator.')
    sys.exit(1)

  # Create runner (no fallback - keep the same runner type)
  try:
    runner = create_runner(
        agent=root_agent, runner_type=runner_type, db_url=db_url, schema=schema
    )
    logger.info('Runner initialized: %s', type(runner).__name__)
  except Exception as e:
    logger.error('Failed to initialize runner: %s', e, exc_info=True)
    # No fallback - exit with error if runner creation fails
    sys.exit(1)

  # Setup server handler
  global handler
  handler = ServerHandler(runner)

  # Register routes (must be done after handler is initialized)
  _register_routes()

  # Start server
  logger.info('Server starting on port %d...', port)
  try:
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')
    logger.info('Server started!')
  except KeyboardInterrupt:
    logger.info('Server stopped by user')
  except Exception as e:
    logger.error('Server error: %s', e, exc_info=True)
    raise


if __name__ == '__main__':
  main()

