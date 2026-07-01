@echo off
echo ==========================================
echo STARTING AURIC SENTINEL v6 TRADING SYSTEM
echo ==========================================
echo.

echo [1/2] Launching FastAPI Backend on port 8000...
start "Auric Sentinel Backend" cmd /k ".\venv\Scripts\python -m uvicorn backend.main:app --port 8000"

echo [2/2] Launching React Dev Server on http://localhost:5173...
start "Auric Sentinel Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ==========================================
echo Startup triggers complete.
echo - Backend documentation: http://127.0.0.1:8000/docs
echo - Frontend Dashboard: http://localhost:5173
echo ==========================================
pause
