#!/usr/bin/env python3
"""Test script to validate database URL format."""

import os
import sys
from urllib.parse import urlparse, quote_plus

def validate_db_url(db_url: str) -> bool:
  """Validate database URL format."""
  if not db_url or not db_url.strip():
    print("❌ Error: Database URL is empty")
    return False

  db_url = db_url.strip()
  print(f"Testing URL: {db_url[:50]}...")

  # Check if it starts with postgresql://
  if not db_url.startswith(('postgresql://', 'postgresql+psycopg2://')):
    print("❌ Error: URL must start with 'postgresql://' or 'postgresql+psycopg2://'")
    print(f"   Got: {db_url[:50]}")
    return False

  # Try to parse it
  try:
    parsed = urlparse(db_url)
    print(f"✅ URL format is valid")
    print(f"   Scheme: {parsed.scheme}")
    print(f"   Host: {parsed.hostname}")
    print(f"   Port: {parsed.port}")
    print(f"   Database: {parsed.path.lstrip('/')}")
    print(f"   User: {parsed.username}")
    return True
  except Exception as e:
    print(f"❌ Error parsing URL: {e}")
    return False

def main():
  """Main function."""
  # Check environment variables
  db_url = (
      os.getenv('DATABASE_URL')
      or os.getenv('POSTGRES_URL')
      or os.getenv('POSTGRESQL_URL')
      or os.getenv('DB_URL')
      or os.getenv('DBURL')
  )

  if db_url:
    print("Found database URL from environment variables:")
    validate_db_url(db_url)
  else:
    print("No database URL found in environment variables.")
    print("\nChecking for legacy format (DBURL, DBUSER, DBPASSWORD)...")
    
    dburl = os.getenv('DBURL')
    dbuser = os.getenv('DBUSER')
    dbpassword = os.getenv('DBPASSWORD')

    if dburl and dbuser and dbpassword:
      print(f"DBURL: {dburl}")
      print(f"DBUSER: {dbuser}")
      print(f"DBPASSWORD: {'*' * len(dbpassword)}")
      
      # Construct URL
      if not dburl.startswith('postgresql://'):
        encoded_user = quote_plus(dbuser)
        encoded_password = quote_plus(dbpassword)
        db_url = f'postgresql://{encoded_user}:{encoded_password}@{dburl}'
      else:
        db_url = dburl
      
      print("\nConstructed URL:")
      validate_db_url(db_url)
    else:
      print("❌ No database configuration found.")
      print("\nPlease set one of:")
      print("  export DATABASE_URL='postgresql://user:pass@host:port/db'")
      print("  OR")
      print("  export DBURL='host:port/db'")
      print("  export DBUSER='user'")
      print("  export DBPASSWORD='pass'")

if __name__ == '__main__':
  main()

