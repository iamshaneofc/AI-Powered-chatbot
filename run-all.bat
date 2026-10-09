@echo off
title AI Powered Chatbot Launcher
echo ========================================================
echo   Launching AI-Powered Document & Multimedia Chatbot
echo ========================================================
echo.
echo Starting Backend in a new window...
start "AI Q&A Backend (Port 8000)" cmd /k "cd /d "%~dp0backend" && .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend in a new window...
start "AI Q&A Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host"

echo.
echo Both servers have been launched!
echo - Backend:  http://localhost:8000  (Docs: http://localhost:8000/docs)
echo - Frontend: http://localhost:5173
echo.
echo NOTE: Keep both opened terminal windows running while using the chatbot.
pause
