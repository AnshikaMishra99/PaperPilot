@echo off
echo ========================================================
echo                 Starting PaperPilot Assistant
echo ========================================================
echo.
echo [1/2] Starting FastAPI Backend on http://localhost:8000...
start "PaperPilot Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo [2/2] Starting React + Vite Frontend on http://localhost:5173...
start "PaperPilot Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo PaperPilot is running:
echo   - Web UI:   http://localhost:5173
echo   - Backend:  http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.
echo Keep the opened windows running while using PaperPilot.
pause
