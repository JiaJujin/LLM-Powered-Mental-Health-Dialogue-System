# Check database entries with dates
import sqlite3
import os
from datetime import datetime, timedelta

db_path = r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend\mindjournal.db"

if not os.path.exists(db_path):
    print(f"DB not found at: {db_path}")
    # Try finding the real DB the server uses
    import glob
    candidates = glob.glob(r"c:\Users\86136\Desktop\LLM心理\**\*.db", recursive=True)
    print(f"DB candidates: {candidates}")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables: {tables}")

# Show journal entries with dates
cursor.execute("""
    SELECT id, user_id, entry_date, created_at, emotion_label,
           substr(content, 1, 80) as content_preview
    FROM journal_entries
    ORDER BY created_at DESC
    LIMIT 20
""")
rows = cursor.fetchall()
print(f"\nTotal journal entries: {len(rows)}")
print(f"\nRecent entries:")
for row in rows:
    print(f"  id={row[0]} user_id={row[1]} entry_date={row[2]} created_at={row[3]} emotion={row[4]} content={row[5]!r}")

# Show users
cursor.execute("SELECT id, anon_id, created_at FROM users")
print(f"\nUsers:")
for row in cursor.fetchall():
    print(f"  id={row[0]} anon_id={row[1]} created_at={row[2]}")

# Calculate what 14 days ago is
fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
print(f"\n14 days ago (utcnow): {fourteen_days_ago.date()}")
print(f"Today (utcnow): {datetime.utcnow().date()}")

conn.close()
