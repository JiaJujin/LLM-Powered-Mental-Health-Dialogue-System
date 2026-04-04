#!/bin/bash
# MindJournal AI - Backend Server Launcher (Linux/macOS)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "========================================"
echo "   MindJournal AI - Backend Server"
echo "========================================"
echo ""

# Step 1: Create and activate virtual environment
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo "[Step 1] Creating Python virtual environment..."
    python3 -m venv "$BACKEND_DIR/.venv"
fi

echo "[Step 2] Activating virtual environment..."
source "$BACKEND_DIR/.venv/bin/activate"

python3 --version

# Step 2: Install dependencies
echo "[Step 3] Checking dependencies..."
if ! pip show fastapi >/dev/null 2>&1; then
    echo "   Installing Python dependencies..."
    pip install -r "$BACKEND_DIR/requirements.txt"
fi

# Step 3: Start server
echo "[Step 4] Starting FastAPI server..."
echo ""
echo "   Backend:  http://127.0.0.1:8000"
echo "   Swagger:  http://127.0.0.1:8000/docs"
echo "   Health:   http://127.0.0.1:8000/api/health"
echo ""
echo "   Press Ctrl+C to stop the server."
echo "========================================"
echo ""

cd "$BACKEND_DIR"
uvicorn app.main:app --reload --port 8000 --host 127.0.0.1
