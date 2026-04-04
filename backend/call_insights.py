import urllib.request
import json

data = json.dumps({"anon_id": "test_user_1773853502"}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8000/api/insights",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        print("status: 200")
        print("keys:", list(result.keys()))
        print("llm_summary len:", len(result.get("llm_summary", "")))
        print("llm_summary:", repr(result.get("llm_summary", "")[:200]))
        print("emotional_patterns len:", len(result.get("emotional_patterns", "")))
        print("common_themes len:", len(result.get("common_themes", "")))
        print("growth_observations len:", len(result.get("growth_observations", "")))
        print("recommendations len:", len(result.get("recommendations", "")))
        print("affirmation len:", len(result.get("affirmation", "")))
        print("focus_points:", result.get("focus_points"))
except Exception as e:
    print("Error:", e)
