"""Quick DB connection check — run before starting the app.

Usage:
    python test_connection.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

required = ["DB_HOST", "DB_USER", "DB_PASSWORD"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(f"[FAIL] Missing environment variables: {', '.join(missing)}")
    print("       Make sure your .env file is filled in correctly.")
    sys.exit(1)

host = os.environ["DB_HOST"]
port = os.environ.get("DB_PORT", "5432")
dbname = os.environ.get("DB_NAME", "postgres")
user = os.environ["DB_USER"]
sslmode = os.environ.get("DB_SSLMODE", "disable")

print(f"Connecting to  host={host}  port={port}  dbname={dbname}  user={user}  sslmode={sslmode} ...")

try:
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(
        host=host,
        port=int(port),
        dbname=dbname,
        user=user,
        password=os.environ["DB_PASSWORD"],
        sslmode=sslmode,
    )
    cur = conn.cursor()
    cur.execute("SELECT 1")
    cur.close()
    conn.close()
    print("[OK] Connection successful — database is reachable.")
except psycopg2.OperationalError as e:
    print(f"[FAIL] Could not connect:\n  {e}")
    print("\nThings to check:")
    print("  1. Is your Supabase project active (not paused)?")
    print("  2. Is DB_HOST the Session pooler hostname from Supabase → Project Settings → Database → Connection pooling?")
    print("  3. Is DB_USER in the format  postgres.<project-ref>  (not just 'postgres')?")
    print("  4. Is DB_PASSWORD correct?")
    sys.exit(1)
