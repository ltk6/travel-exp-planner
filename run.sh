#!/bin/bash
# =============================================================================
# Travel Planner - Service Runner (Linux & macOS)
# =============================================================================

# Exit immediately if a command exits with a non-zero status.
# We will handle background service launching manually, so we don't set -e yet.

# Colored output helpers
GREEN="\033[1;32m"
BLUE="\033[1;34m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${BLUE}=======================================${RESET}"
echo -e "${BOLD}   Travel Planner - Backend + Next.js  ${RESET}"
echo -e "${BLUE}=======================================${RESET}"

# Trap Ctrl+C to kill background processes started by this script
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo -e "\n${YELLOW}[INFO] Shutting down services launched in this session...${RESET}"
    if [ -n "$BACKEND_PID" ]; then
        echo -e "${BLUE}[INFO] Stopping backend (PID: $BACKEND_PID)...${RESET}"
        kill "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "$FRONTEND_PID" ]; then
        echo -e "${BLUE}[INFO] Stopping frontend (PID: $FRONTEND_PID)...${RESET}"
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    echo -e "${GREEN}[OK] Done.${RESET}"
    exit 0
}
trap cleanup SIGINT SIGTERM

# 1. Detect Python version
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python is not installed. Please install Python 3 and try again.${RESET}"
    exit 1
fi

# 2. Python venv
if [ ! -d "venv" ]; then
    echo -e "${BLUE}[INFO] Creating Python virtual environment using $PYTHON_CMD...${RESET}"
    $PYTHON_CMD -m venv venv
fi

echo -e "${BLUE}[INFO] Activating venv...${RESET}"
source venv/bin/activate

# 3. Python requirements
echo -e "${BLUE}=======================================${RESET}"
echo -e "${BOLD}1/3  Verifying Python requirements     ${RESET}"
echo -e "${BLUE}=======================================${RESET}"

REQ_MARKER="venv/.requirements-installed"
NEED_PIP=1

if [ -f "$REQ_MARKER" ]; then
    PIP_STATE=$($PYTHON_CMD -c "import os; print(1 if os.path.exists('$REQ_MARKER') and os.path.getmtime('$REQ_MARKER') >= os.path.getmtime('requirements.txt') else 0)")
    if [ "$PIP_STATE" -eq 1 ]; then
        NEED_PIP=0
    fi
fi

if [ "$NEED_PIP" -eq 1 ]; then
    echo -e "${BLUE}[INFO] Installing Python dependencies...${RESET}"
    $PYTHON_CMD -m pip install --upgrade pip
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "\n${YELLOW}[WARN] pip install failed. Backend may not start, but continuing${RESET}"
        echo -e "${YELLOW}       to launch frontend anyway. Fix dependencies then re-run.${RESET}\n"
    else
        touch "$REQ_MARKER"
    fi
else
    echo -e "${GREEN}[OK] Python requirements up-to-date (delete $REQ_MARKER to force reinstall)${RESET}"
fi

# Sanity check: flask must be importable inside the venv
$PYTHON_CMD -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[WARN] Flask not in venv. Forcing direct install...${RESET}"
    $PYTHON_CMD -m pip install flask flask-cors
fi

export PYTHONPATH=$(pwd)

# 4. Node dependencies
echo -e "${BLUE}=======================================${RESET}"
echo -e "${BOLD}2/3  Verifying frontend dependencies  ${RESET}"
echo -e "${BLUE}=======================================${RESET}"

if [ ! -d "frontend/n16_web_ui/node_modules" ]; then
    echo -e "${BLUE}[INFO] Installing Next.js dependencies (1-2 min, one-time)...${RESET}"
    (cd frontend/n16_web_ui && npm install)
else
    echo -e "${GREEN}[OK] frontend/n16_web_ui/node_modules ready${RESET}"
fi

# 5. Detect running services
echo -e "${BLUE}=======================================${RESET}"
echo -e "${BOLD}3/3  Launching services                ${RESET}"
echo -e "${BLUE}=======================================${RESET}"

BACKEND_RUNNING=0
FRONTEND_RUNNING=0

# Use Python socket to check loopback ports safely without depending on netstat/lsof formatting
$PYTHON_CMD -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5); s.connect(('127.0.0.1', 5000))" >/dev/null 2>&1 && BACKEND_RUNNING=1
$PYTHON_CMD -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5); s.connect(('127.0.0.1', 3000))" >/dev/null 2>&1 && FRONTEND_RUNNING=1

if [ "$BACKEND_RUNNING" -eq 1 ]; then
    echo -e "${GREEN}[OK] Backend already running on :5000 - skip launching${RESET}"
else
    echo -e "${BLUE}[INFO] Launching backend on :5000 (logs: backend.log)...${RESET}"
    export PYTHONPATH=$(pwd)
    nohup $PYTHON_CMD -m backend.n8_orchestrator.app > backend.log 2>&1 &
    BACKEND_PID=$!
fi

if [ "$FRONTEND_RUNNING" -eq 1 ]; then
    echo -e "${GREEN}[OK] Frontend already running on :3000 - skip launching${RESET}"
else
    echo -e "${BLUE}[INFO] Launching frontend on :3000 (logs: frontend.log)...${RESET}"
    (cd frontend/n16_web_ui && nohup npm run dev > ../../frontend.log 2>&1 &)
    # Give a tiny slice of time for subshell to spawn dev server and write pid
    sleep 0.5
    # Find the PID of the npm/next dev server process
    FRONTEND_PID=$(pgrep -f "next-dev" | head -n 1)
    if [ -z "$FRONTEND_PID" ]; then
        FRONTEND_PID=$(pgrep -f "npm run dev" | head -n 1)
    fi
fi

# 6. Wait for Frontend readiness
echo ""
echo -e "${BLUE}[INFO] Waiting for frontend to be ready (max 60s)...${RESET}"
WAIT=0
while [ $WAIT -lt 30 ]; do
    let WAIT=WAIT+1
    $PYTHON_CMD -c "import urllib.request; urllib.request.urlopen('http://localhost:3000', timeout=1)" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[OK] Frontend ready after ~$WAIT polls${RESET}"
        break
    fi
    sleep 2
done

if [ $WAIT -ge 30 ]; then
    echo -e "${YELLOW}[WARN] Frontend slow to start - opening browser anyway${RESET}"
fi

# 7. Open Browser based on OS
OS_NAME=$(uname)
if [ "$OS_NAME" = "Darwin" ]; then
    # macOS
    open http://localhost:3000
elif [ "$OS_NAME" = "Linux" ]; then
    # Linux (requires xdg-utils)
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open http://localhost:3000
    else
        echo -e "${YELLOW}[WARN] xdg-open not found. Please open http://localhost:3000 manually.${RESET}"
    fi
fi

echo ""
echo -e "${GREEN}[SUCCESS] Services are up and running!${RESET}"
echo -e "  Frontend:  ${BOLD}http://localhost:3000${RESET}"
echo -e "  Backend:   ${BOLD}http://localhost:5000/health${RESET}"
echo ""
echo -e "${YELLOW}Keep this terminal open. Press Ctrl+C to terminate all services.${RESET}"
echo ""

# Block terminal to keep services running and let the trap handle cleanup
while true; do
    sleep 1
done
