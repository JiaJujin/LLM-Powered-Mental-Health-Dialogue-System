import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Step 1: Create a journal entry
print("=== Step 1: Create Journal Entry ===")
journal_data = {
    "anon_id": "test_user_debug",
    "content": "This is a test journal entry to debug the history issue.",
    "title": "Test Entry Debug",
    "mood": "Happy",
    "weather": "Sunny",
    "entry_date": "2025-03-18"
}

response = requests.post(f"{BASE_URL}/api/journal", json=journal_data)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:500]}")

# Step 2: Query history
print("\n=== Step 2: Query History ===")
history_params = {
    "anon_id": "test_user_debug",
    "date_from": "",
    "date_to": "",
    "mood": ""
}

history_response = requests.get(f"{BASE_URL}/api/journal/history", params=history_params)
print(f"Status: {history_response.status_code}")
history = history_response.json()
print(f"Total entries: {history.get('total', 0)}")
print(f"Entries: {json.dumps(history.get('entries', []), indent=2, ensure_ascii=False)}")

# Step 3: Query history without filters
print("\n=== Step 3: Query History (no filters) ===")
history_response2 = requests.get(f"{BASE_URL}/api/journal/history", params={"anon_id": "test_user_debug"})
print(f"Status: {history_response2.status_code}")
history2 = history_response2.json()
print(f"Total entries: {history2.get('total', 0)}")
