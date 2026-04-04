# Trigger insights via httpx (in .venv)
import sys
import os

# Use httpx from the .venv
venv_python = r"c:\Users\86136\Desktop\LLM心理\mindjournal-ai\backend\.venv\Scripts\python.exe"
os.system(f'"{venv_python}" -c "import httpx; r = httpx.post(\'http://127.0.0.1:8000/api/insights\', json={\\'anon_id\\': \\'test_user_1773853502\\'}, timeout=120); print(\\'status\\', r.status_code); data = r.json(); print(\\'summary_len\\', len(data.get(\\'llm_summary\\',\\'\\'))); print(\\'summary\\', repr(data.get(\\'llm_summary\\',\\'\\')[:100]))"')