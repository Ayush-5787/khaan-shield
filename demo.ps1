# demo.ps1 - one-click KHAAN-SHIELD demo launcher
# Usage: .\demo.ps1   (from project root)

$ErrorActionPreference = "Stop"

# 0. Sanity check: must run from project root
if (-not (Test-Path "src") -or -not (Test-Path "web_preview.py")) {
    Write-Host "Run this from the project root (folder with src\ and web_preview.py)" -ForegroundColor Red
    exit 1
}

# 1. Fresh log for a clean demo
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
if (Test-Path "logs\khaan.log") { Clear-Content "logs\khaan.log" }

# 2. Dashboard in its own window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python web_preview.py"
Start-Sleep -Seconds 2

# 3. Simulation in its own window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m src.main"

# 4. Open the browser on the dashboard
Start-Sleep -Seconds 2
Start-Process "http://localhost:5000"

Write-Host "Demo launched -> dashboard at http://localhost:5000" -ForegroundColor Green