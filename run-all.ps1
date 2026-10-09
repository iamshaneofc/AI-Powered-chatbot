# One-click PowerShell launcher for both Backend and Frontend
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Launching AI-Powered Document & Multimedia Chatbot   " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Start Backend in separate window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Backend...' -ForegroundColor Cyan; Set-Location -Path '$PSScriptRoot\backend'; & '.\venv\Scripts\python.exe' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# 2. Start Frontend in separate window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting Frontend...' -ForegroundColor Green; `$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User'); Set-Location -Path '$PSScriptRoot\frontend'; npm run dev -- --host"

Write-Host "`nBoth servers have been launched in separate windows!" -ForegroundColor Green
Write-Host "• Backend:  http://localhost:8000 (Swagger docs: http://localhost:8000/docs)" -ForegroundColor Yellow
Write-Host "• Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host "`nIMPORTANT: Keep both server windows OPEN while using the app." -ForegroundColor White
