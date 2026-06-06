#!/usr/bin/env bash
# LifeLine — one-command dev launcher (macOS / Linux / Git-Bash).
#
# Usage:
#   ./dev.sh           # setup-if-needed, then start backend + frontend
#   ./dev.sh setup     # only do setup (venv, deps, donors.csv)
#   ./dev.sh fresh     # reinstall backend + frontend deps, then start
#
# Backend runs on :8000, frontend on :5173. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
DATA="$ROOT/data"
VENV_PY="$BACKEND/.venv/bin/python"

MODE="${1:-run}"

find_python() {
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" --version >/dev/null 2>&1; then echo "$c"; return 0; fi
    fi
  done
  return 1
}

echo "== LifeLine dev launcher =="

# 1. donors.csv
if [ ! -f "$DATA/donors.csv" ]; then
  PY="$(find_python)" || { echo "Python not found. Install Python 3.10+ and re-run."; exit 1; }
  echo "Generating data/donors.csv ..."
  ( cd "$DATA" && "$PY" generate_donors.py )
else
  echo "donors.csv present."
fi

# 2. backend venv + deps
if [ "$MODE" = "fresh" ] && [ -d "$BACKEND/.venv" ]; then
  echo "Removing backend/.venv (fresh) ..."; rm -rf "$BACKEND/.venv"
fi
if [ ! -x "$VENV_PY" ]; then
  PY="$(find_python)" || { echo "Python not found. Install Python 3.10+ and re-run."; exit 1; }
  echo "Creating backend/.venv ..."
  "$PY" -m venv "$BACKEND/.venv"
  "$VENV_PY" -m pip install --upgrade pip --quiet
  echo "Installing backend requirements ..."
  "$VENV_PY" -m pip install -r "$BACKEND/requirements.txt"
else
  echo "backend/.venv present."
fi

# 3. backend .env
if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  echo "Created backend/.env from .env.example — add your GROQ_API_KEY before C1."
fi

# 4. frontend deps
if [ "$MODE" = "fresh" ] && [ -d "$FRONTEND/node_modules" ]; then
  echo "Removing frontend/node_modules (fresh) ..."; rm -rf "$FRONTEND/node_modules"
fi
if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "Installing frontend deps (npm install) ..."
  ( cd "$FRONTEND" && npm install )
else
  echo "frontend/node_modules present."
fi

if [ "$MODE" = "setup" ]; then
  echo "Setup complete. Run ./dev.sh to start the servers."
  exit 0
fi

# 5. launch both; Ctrl+C kills the group
echo "Starting backend (:8000) and frontend (:5173) ..."
( cd "$BACKEND" && "$VENV_PY" -m uvicorn main:app --reload --port 8000 ) &
BACK_PID=$!
( cd "$FRONTEND" && npm run dev ) &
FRONT_PID=$!

trap 'echo; echo "Stopping ..."; kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true' INT TERM EXIT

echo ""
echo "  App:      http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
wait
