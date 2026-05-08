@echo off
echo =======================================
echo     Travel Planner Setup ^& Launcher
echo =======================================

:: 1. Setup Virtual Environment
if not exist "venv\" (
    echo [INFO] Creating Virtual Environment...
    python -m venv venv
)

echo [INFO] Activating Virtual Environment...
call venv\Scripts\activate.bat

:: 2. Install Requirements
echo =======================================
echo 1. Installing/Verifying Requirements
echo =======================================
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: Set python path so backend modules can find each other
set PYTHONPATH=%cd%

:: 3. Start Services
echo =======================================
echo 2. Starting Backend API (Port 5000)
echo =======================================
start "Travel Planner - Backend" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m backend.n8_api.app"

@echo off
echo =======================================
echo 3. Starting Streamlit UIs
echo =======================================

:: Start original N7 UI (Port 8501)
start "Travel Planner - Frontend" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m streamlit run frontend\n7_ui\app.py --server.port 8501"

:: Start Alt N7 UI (Port 8502)
start "Travel Planner - Alt Frontend" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m streamlit run frontend\alt_n7_ui\app.py --server.port 8502"

echo.
echo [SUCCESS] Both servers are starting up in separate windows!
echo You can close this window now.
pause
