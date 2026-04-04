import requests
import json

API = "http://127.0.0.1:8000/api"

# Try to find any user with entries via the journal history endpoint
# Try common test anon_ids
test_ids = [
    "test_user_1773853502",
    "user_1",
    "anon_1",
    "test_user",
]

for aid in test_ids:
    r = requests.get(f"{API}/journal/history", params={"anon_id": aid}, timeout=5)
    if r.status_code == 200:
        data = r.json()
        total = data.get('total', 0)
        print(f"anon_id={aid}: {total} entries")
        if total > 0:
            entries = data.get('entries', [])
            for e in entries[:2]:
                content = (e.get('content') or e.get('content_snippet') or "")[:80]
                print(f"  entry {e.get('entry_id')}: {content!r}")
    else:
        print(f"anon_id={aid}: HTTP {r.status_code}")
