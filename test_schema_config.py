#!/usr/bin/env python3
"""Test script to verify schema configuration is being read correctly."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dotenv import load_dotenv
import configparser

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
  load_dotenv(env_file, override=True)
  print(f'✓ Loaded .env file from: {env_file}')
else:
  print(f'⚠ .env file not found at: {env_file}')

# Test 1: Check environment variables
print('\n=== Testing Environment Variables ===')
db_schema_env = os.getenv('DB_SCHEMA') or os.getenv('POSTGRES_SCHEMA')
if db_schema_env:
  print(f'✓ DB_SCHEMA from environment: {db_schema_env}')
else:
  print('⚠ DB_SCHEMA not found in environment variables')

# Test 2: Check config file
print('\n=== Testing Config File ===')
config_file = Path(__file__).parent / 'config.ini'
if config_file.exists():
  try:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_file)
    
    # Check default section
    if parser.has_section('default'):
      schema_default = parser.get('default', 'db_schema', fallback=None) or parser.get('default', 'schema', fallback=None)
      if schema_default:
        print(f'✓ db_schema from [default]: {schema_default}')
      else:
        print('⚠ db_schema not found in [default] section')
    
    # Check production section
    if parser.has_section('production'):
      schema_prod = parser.get('production', 'db_schema', fallback=None) or parser.get('production', 'schema', fallback=None)
      if schema_prod:
        print(f'✓ db_schema from [production]: {schema_prod}')
      else:
        print('⚠ db_schema not found in [production] section')
  except Exception as e:
    print(f'✗ Error reading config file: {e}')
else:
  print(f'⚠ config.ini not found at: {config_file}')

# Test 3: Simulate app_server.py logic
print('\n=== Simulating app_server.py Schema Resolution ===')
properties = {}
if config_file.exists():
  try:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_file)
    if parser.has_section('default'):
      for key, value in parser.items('default'):
        properties[key] = value
    if parser.has_section('production'):
      for key, value in parser.items('production'):
        properties[key] = value
  except Exception as e:
    print(f'✗ Error loading properties: {e}')

# Resolve schema (matching app_server.py logic)
schema = properties.get('db_schema') or properties.get('schema')
if not schema:
  schema = os.getenv('DB_SCHEMA') or os.getenv('POSTGRES_SCHEMA')
if schema:
  schema = schema.strip()
  if not schema:
    schema = None

if schema:
  print(f'✓ Final resolved schema: {schema}')
  print(f'  Source: {"config file" if properties.get("db_schema") or properties.get("schema") else "environment variable"}')
else:
  print('⚠ No schema resolved - will use default (public) schema')

# Test 4: Test PostgresDBHelper initialization
print('\n=== Testing PostgresDBHelper Schema Initialization ===')
try:
  from google.adk.utils.postgres_db_helper import PostgresDBHelper
  
  # Get a test DB URL (or use environment)
  test_db_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('DB_URL')
  if not test_db_url:
    print('⚠ No database URL found - skipping PostgresDBHelper test')
    print('  Set DATABASE_URL, POSTGRES_URL, or DB_URL to test PostgresDBHelper')
  else:
    # Mask password in URL for display
    from urllib.parse import urlparse
    parsed = urlparse(test_db_url)
    if parsed.password:
      masked_url = test_db_url.replace(f':{parsed.password}@', ':***@', 1)
    else:
      masked_url = test_db_url
    print(f'  Using database URL: {masked_url}')
    
    # Test with schema
    if schema:
      print(f'  Testing with schema: {schema}')
      helper = PostgresDBHelper.get_instance(db_url=test_db_url, schema=schema)
      if helper.schema == schema:
        print(f'✓ PostgresDBHelper initialized with schema: {helper.schema}')
      else:
        print(f'✗ Schema mismatch! Expected: {schema}, Got: {helper.schema}')
    else:
      print('  Testing without schema (default/public)')
      helper = PostgresDBHelper.get_instance(db_url=test_db_url, schema=None)
      if helper.schema is None:
        print('✓ PostgresDBHelper initialized without schema (using default)')
      else:
        print(f'✗ Expected None schema, got: {helper.schema}')
except Exception as e:
  print(f'✗ Error testing PostgresDBHelper: {e}')
  import traceback
  traceback.print_exc()

print('\n=== Test Complete ===')

