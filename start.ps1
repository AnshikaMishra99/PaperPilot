$base = $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "             Starting PaperPilot Assistant" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Launching FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$base\backend`" && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

Write-Host "[2/2] Launching React + Vite Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$base\frontend`" && npm run dev"

Write-Host "`nPaperPilot is running:" -ForegroundColor Cyan
Write-Host "  - Web UI:   http://localhost:5173" -ForegroundColor Yellow
Write-Host "  - Backend:  http://localhost:8000" -ForegroundColor Yellow
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "`nKeep the backend and frontend terminal windows open while using PaperPilot." -ForegroundColor Gray
