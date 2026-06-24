@echo off
echo Starting HandwritingEval...
start "HandwritingEval Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn main:app --port 8032 --reload"
timeout /t 3 /nobreak >nul
start "HandwritingEval Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 4 /nobreak >nul
echo.
echo Backend:  http://127.0.0.1:8032
echo Frontend: http://localhost:5182
echo.
start http://localhost:5182
