# Run frontend dev server
Write-Host "Starting Vite React Frontend on http://localhost:5173..." -ForegroundColor Green
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
Set-Location -Path "$PSScriptRoot\frontend"
npm run dev -- --host
