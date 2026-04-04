"""
End-to-end test: start server, trigger insights, print all server stdout.
"""
import subprocess
import sys
import time
import threading
import queue

venv_python = r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend\.venv\Scripts\python.exe"
BACKEND_DIR = r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend"

server_proc = None
output_lines = []

def start_server():
    global server_proc
    server_proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "app.main:app", "--port", "8002", "--host", "127.0.0.1"],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    # Read stdout line by line
    for line in server_proc.stdout:
        output_lines.append(line)
        print("[SERVER]", line, end="")

t = threading.Thread(target=start_server, daemon=True)
t.start()

# Wait for server to be ready
print("Waiting for server to start...")
for i in range(30):
    time.sleep(1)
    # Check if server printed "Application startup complete"
    for line in output_lines:
        if "Application startup complete" in line:
            print(f"Server ready after {i+1} seconds")
            break
    else:
        continue
    break

# Now trigger insights with user who has entries
print("\n\n=== TRIGGERING INSIGHTS WITH USER a5829009-a08e-4c9c-ad11-c857f46281f9 ===\n")
import urllib.request
import json

data = json.dumps({"anon_id": "a5829009-a08e-4c9c-ad11-c857f46281f9"}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8002/api/insights",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        print(f"\nAPI status: 200")
        for k in ["llm_summary","emotional_patterns","common_themes","growth_observations","recommendations","affirmation"]:
            v = result.get(k, "")
            print(f"  {k} ({len(v)} chars): {v!r}")
        print(f"  focus_points: {result.get('focus_points')}")
except Exception as e:
    print(f"API Error: {e}")

time.sleep(3)
print("\n\n=== FULL SERVER OUTPUT (from output_lines buffer) ===")
for line in output_lines:
    print("[SERVER]", line, end="")

if server_proc:
    server_proc.terminate()
    server_proc.communicate(timeout=5)
