@echo off
:: Ensure standard Windows directories are in PATH
set PATH=%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%SystemRoot%\System32\WindowsPowerShell\v1.0\;%PATH%
chcp 65001 >nul
echo =======================================
echo   Travel Planner - Legacy Streamlit
echo =======================================
echo (Fallback UI - use run.bat for the Next.js version)
echo.

if not exist "venv\" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
set PYTHONPATH=%cd%

start "Travel Planner - Backend (:5000)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m backend.n8_orchestrator.app"
start "Travel Planner - Streamlit (:8501)" cmd /k "call venv\Scripts\activate.bat && set PYTHONPATH=%cd% && python -m streamlit run frontend\n7_legacy_streamlit_ui\app.py --server.port 8501"

echo.
echo [SUCCESS] Streamlit at http://localhost:8501
echo.
pause
