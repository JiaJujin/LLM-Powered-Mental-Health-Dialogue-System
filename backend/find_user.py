# Check DB schema
import sqlite3

conn = sqlite3.connect('mindjournal.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

for tbl in tables:
    name = tbl[0]
    cursor.execute(f"SELECT * FROM {name} LIMIT 3")
    rows = cursor.fetchall()
    print(f"\n=== {name} ({len(rows)} sample rows) ===")
    if rows:
        cursor.execute(f"PRAGMA table_info({name})")
        cols = [c[1] for c in cursor.fetchall()]
        print(f"  Columns: {cols}")
        for row in rows[:2]:
            print(f"  {dict(zip(cols, row))}")

conn.close()
