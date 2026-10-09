# Run backend server
Write-Host "Starting AI Q&A Backend on http://localhost:8000..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\backend"
& ".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
