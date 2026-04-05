"""
reset_admin_password.py
Run this once after the bcrypt/passlib fix to reset the admin password.

Usage:
    conda activate medpredict
    cd backend
    python scripts/reset_admin_password.py

This directly updates the database with a fresh bcrypt hash that works
with bcrypt 4.x (bypassing passlib entirely).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
import psycopg2
from app.core.config import settings

NEW_PASSWORD = "admin123"
USERNAME     = "admin"


def reset_password():
    print(f"\nResetting password for '{USERNAME}' to '{NEW_PASSWORD}'...")

    # Generate fresh bcrypt hash using the new pure-bcrypt approach
    pw_bytes   = NEW_PASSWORD.encode("utf-8")
    salt       = bcrypt.gensalt(rounds=12)
    new_hash   = bcrypt.hashpw(pw_bytes, salt).decode("utf-8")

    # Verify it works before saving
    ok = bcrypt.checkpw(pw_bytes, new_hash.encode("utf-8"))
    if not ok:
        print("ERROR: Hash verification failed — aborting")
        sys.exit(1)
    print(f"Hash generated and verified: {new_hash[:30]}...")

    # Connect and update
    sync_url = settings.SYNC_DATABASE_URL
    print(f"Connecting to: {sync_url[:40]}...")

    try:
        conn = psycopg2.connect(sync_url)
        cur  = conn.cursor()

        # Check user exists
        cur.execute("SELECT id, username FROM users WHERE username = %s", (USERNAME,))
        row = cur.fetchone()
        if not row:
            print(f"User '{USERNAME}' not found — creating it...")
            cur.execute("""
                INSERT INTO users (username, email, hashed_password, role, is_active)
                VALUES (%s, %s, %s, 'admin', true)
                ON CONFLICT (username) DO UPDATE SET hashed_password = EXCLUDED.hashed_password
            """, (USERNAME, "admin@mdps.local", new_hash))
        else:
            print(f"Found user id={row[0]} — updating hash...")
            cur.execute(
                "UPDATE users SET hashed_password = %s WHERE username = %s",
                (new_hash, USERNAME)
            )

        conn.commit()
        cur.close()
        conn.close()
        print(f"\nDone! You can now log in with:  {USERNAME} / {NEW_PASSWORD}")

    except Exception as e:
        print(f"\nDB Error: {e}")
        print("\nIf PostgreSQL is not running, use the SQLite fallback below.")
        _sqlite_fallback(new_hash)


def _sqlite_fallback(new_hash: str):
    """
    If PostgreSQL isn't set up, patch the hash in a local SQLite dev DB.
    For dev/demo only.
    """
    print("\nTrying SQLite fallback (dev mode)...")
    try:
        import sqlite3
        db_path = "dev.db"
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO users (username, email, hashed_password, role)
            VALUES (?, ?, ?, 'admin')
            ON CONFLICT(username) DO UPDATE SET hashed_password = excluded.hashed_password
        """, ("admin", "admin@mdps.local", new_hash))
        conn.commit()
        conn.close()
        print(f"SQLite dev.db updated. Login: admin / admin123")
    except Exception as e2:
        print(f"SQLite fallback also failed: {e2}")


if __name__ == "__main__":
    reset_password()
