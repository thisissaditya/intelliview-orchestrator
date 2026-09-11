"""
One-off script: adds the `timezone` column directly to the local
SQLite dev database (intelliview.db), bypassing Alembic since Alembic
is configured for Postgres and this local file isn't managed by it
in this environment.

Run this from the repo root:
    python3 add_timezone_column.py
"""

import sqlite3

DB_PATH = "./intelliview.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(interview_schedules)")
existing_columns = {row[1] for row in cur.fetchall()}

if "timezone" in existing_columns:
    print("Column 'timezone' already exists — nothing to do.")
else:
    cur.execute(
        "ALTER TABLE interview_schedules "
        "ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'UTC'"
    )
    conn.commit()
    print("Added 'timezone' column to interview_schedules.")

cur.execute("PRAGMA table_info(interview_schedules)")
print("\nCurrent columns:")
for row in cur.fetchall():
    print(f"  {row[1]} ({row[2]})")

conn.close()
