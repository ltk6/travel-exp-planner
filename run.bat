@echo off
chcp 65001 >nul
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

:: 2. Python requirements
echo =======================================
echo 1/3  Verifying Python requirements
echo =======================================
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] pip install failed. Backend will not start.
    echo Fix the dependency error above, then re-run this script.
    echo.
    pause
    exit /b 1
)

:: Sanity check: flask must be importable inside the venv
python -c "import flask" 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] Flask not installed in venv. Forcing direct install...
    python -m pip install flask flask-cors
)

set PYTHONPATH=%cd%

:: 3. Node deps (one-time install)
echo =======================================
echo 2/3  Verifying frontend dependencies
echo =======================================
if not exist "frontend\web\node_modules" (
    echo [INFO] Installing Next.js dependencies ^(1-2 min, one-time^)...
    pushd "frontend\web"
    call npm install
    popd
) else (
    echo [OK] frontend\web\node_modules ready
)

:: 4. Launch services
echo =======================================
echo 3/3  Launching services
echo =======================================

start "Travel Planner - Backend (:5000)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m backend.n8_orchestrator.app"

start "Travel Planner - Frontend (:3000)" /D "%cd%\frontend\web" cmd /k "npm run dev"

echo.
echo [SUCCESS] Two windows are starting up:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:5000/health
echo.
echo Waiting ~12 seconds for Next.js to compile before opening browser...
timeout /t 12 /nobreak >nul
start "" http://localhost:3000

echo.
echo Note: If port 3000 or 5000 is already in use, close existing servers first.
echo Legacy Streamlit fallback: run-legacy.bat
echo.
pause
