#!/usr/bin/env bash
# MindJournal AI - Development Environment Launcher (Linux / macOS)
# Usage: ./scripts/start_dev.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo ""
echo "========================================"
echo "  MindJournal AI - Dev Environment"
echo "========================================"
echo "  Working directory: $PROJECT_ROOT"
echo ""

# ── Backend ──────────────────────────────────────────────────────────────────

echo "[1/2] Preparing backend..." >&2

if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "    Creating virtual environment..." >&2
    python3 -m venv "$BACKEND_DIR/.venv"
fi

echo "    Activating virtual environment..." >&2
# shellcheck source=/dev/null
source "$BACKEND_DIR/.venv/bin/activate"

echo "    Python version: $(python --version)" >&2

if ! pip show fastapi >/dev/null 2>&1; then
    echo "    Installing Python dependencies..." >&2
    pip install -r "$BACKEND_DIR/requirements.txt"
fi

echo "    Starting backend on http://127.0.0.1:8000 ..." >&2
cd "$BACKEND_DIR"
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1 \
    > "$PROJECT_ROOT/backend_dev.log" 2>&1 &
BACKEND_PID=$!
echo "    Backend PID: $BACKEND_PID" >&2
echo ""

# ── Frontend ─────────────────────────────────────────────────────────────────

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[2/2] Preparing frontend (first run)..." >&2
    echo "    Installing npm dependencies..." >&2
    npm install
else
    echo "[2/2] Preparing frontend..." >&2
fi

echo "    Starting frontend on http://127.0.0.1:5173 ..." >&2
cd "$FRONTEND_DIR"
npm run dev \
    > "$PROJECT_ROOT/frontend_dev.log" 2>&1 &
FRONTEND_PID=$!
echo "    Frontend PID: $FRONTEND_PID" >&2
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
echo "========================================"
echo "  Services started successfully!"
echo ""
echo "  Backend API & docs :  http://localhost:8000/docs"
echo "  Frontend UI        :  http://localhost:5173/"
echo ""
echo "  Backend PID : $BACKEND_PID"
echo "  Frontend PID: $FRONTEND_PID"
echo ""
echo "  To stop all services:"
echo "    kill $BACKEND_PID $FRONTEND_PID"
echo "========================================"

# Keep script alive so the user can Ctrl+C
trap "echo 'Stopping services...' >&2; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Done.' >&2; exit 0" INT TERM
wait
