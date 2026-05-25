@echo off
:: Ensure standard Windows directories are in PATH
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%SystemRoot%\System32\WindowsPowerShell\v1.0\;%PATH%
chcp 65001 >nul
setlocal EnableDelayedExpansion
echo =======================================
echo    Travel Planner - Backend + Next.js
echo =======================================

:: 1. Python venv
if not exist "venv\" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)
echo [INFO] Activating venv...
call venv\Scripts\activate.bat

:: 2. Python requirements (skip if marker is fresher than requirements.txt)
echo =======================================
echo 1/3  Verifying Python requirements
echo =======================================
set REQ_MARKER=venv\.requirements-installed
set NEED_PIP=1
if exist "%REQ_MARKER%" (
    for /f %%i in ('python -c "import os; print(1 if os.path.exists(\"venv/.requirements-installed\") and os.path.getmtime(\"venv/.requirements-installed\") >= os.path.getmtime(\"requirements.txt\") else 0)"') do set PIP_STATE=%%i
    if "!PIP_STATE!"=="1" set NEED_PIP=0
)

if "%NEED_PIP%"=="1" (
    python -m pip install --upgrade pip >nul
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [WARN] pip install failed. Backend may not start, but continuing
        echo        to launch frontend anyway. Fix deps then re-run.
        echo.
    ) else (
        type nul > "%REQ_MARKER%"
    )
) else (
    echo [OK] Python requirements up-to-date (delete %REQ_MARKER% to force reinstall)
)

:: Sanity check: flask must be importable inside the venv
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [WARN] Flask not in venv. Forcing direct install...
    python -m pip install flask flask-cors
)

set PYTHONPATH=%cd%

:: 3. Node deps (one-time install)
echo =======================================
echo 2/3  Verifying frontend dependencies
echo =======================================
if not exist "frontend\n16_web_ui\node_modules" (
    echo [INFO] Installing Next.js dependencies ^(1-2 min, one-time^)...
    pushd "frontend\n16_web_ui"
    call npm install
    popd
) else (
    echo [OK] frontend\n16_web_ui\node_modules ready
)

:: 4. Detect running services and launch only what's missing
echo =======================================
echo 3/3  Launching services
echo =======================================

set BACKEND_RUNNING=0
set FRONTEND_RUNNING=0
python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5); s.connect(('127.0.0.1', 5000))" >nul 2>&1 && set BACKEND_RUNNING=1
python -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5); s.connect(('127.0.0.1', 3000))" >nul 2>&1 && set FRONTEND_RUNNING=1

if "%BACKEND_RUNNING%"=="1" (
    echo [OK] Backend already on :5000 - skip launching
) else (
    echo [INFO] Launching backend on :5000...
    start "Travel Planner - Backend (:5000)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m backend.n8_orchestrator.app"
)

if "%FRONTEND_RUNNING%"=="1" (
    echo [OK] Frontend already on :3000 - skip launching
) else (
    echo [INFO] Launching frontend on :3000...
    start "Travel Planner - Frontend (:3000)" /D "%cd%\frontend\n16_web_ui" cmd /k "npm run dev"
)

echo.
echo [INFO] Waiting for frontend to be ready (max 60s)...
set WAIT=0
:WAIT_LOOP
set /a WAIT+=1
if !WAIT! gtr 30 (
    echo [WARN] Frontend slow to start - opening browser anyway
    goto OPEN_BROWSER
)
python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000', timeout=1)" >nul 2>&1
if errorlevel 1 (
    python -c "import time; time.sleep(2)"
    goto WAIT_LOOP
)
echo [OK] Frontend ready after ~!WAIT! polls
:OPEN_BROWSER
start "" http://localhost:3000

echo.
echo [SUCCESS] Services:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:5000/health
echo.
echo Legacy Streamlit fallback: legacy_run.bat
echo.
pause
endlocal
