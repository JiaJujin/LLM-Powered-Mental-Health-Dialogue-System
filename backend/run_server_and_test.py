# Run server + trigger insights in one process, capture all print() output
import subprocess
import time
import urllib.request
import json
import threading

venv_python = r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend\.venv\Scripts\python.exe"
server_proc = None

def run_server():
    global server_proc
    proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "app.main:app", "--port", "8001", "--host", "127.0.0.1"],
        cwd=r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    server_proc = proc

t = threading.Thread(target=run_server, daemon=True)
t.start()

print("Waiting for server to start...")
time.sleep(8)
print("Triggering insights API...")

data = json.dumps({"anon_id": "test_user_1773853502"}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8001/api/insights",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        print(f"API status: 200")
        for k in ["llm_summary","emotional_patterns","common_themes","growth_observations","recommendations","affirmation"]:
            v = result.get(k, "")
            print(f"  {k} ({len(v)} chars): {v!r}")
        print(f"  focus_points: {result.get('focus_points')}")
except Exception as e:
    print(f"API Error: {e}")

time.sleep(2)

if server_proc:
    server_proc.terminate()
    try:
        stdout, _ = server_proc.communicate(timeout=5)
        print("\n=== SERVER STDOUT (last 5000 chars) ===")
        print(stdout[-5000:])
    except Exception as e2:
        print(f"Could not read server output: {e2}")