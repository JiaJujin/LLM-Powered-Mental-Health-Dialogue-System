#Requires -Version 5.1
# MindJournal AI - Development Environment Launcher (Windows PowerShell)
# Usage: .\scripts\start_dev.ps1

param(
    [switch]$NoFrontend   # Skip frontend (only start backend)
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path
$BackendDir = "$ProjectRoot\backend"
$FrontendDir = "$ProjectRoot\frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MindJournal AI - Dev Environment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Working directory: $ProjectRoot" -ForegroundColor DarkGray
Write-Host ""

# ── Backend ──────────────────────────────────────────────────────────────────

Write-Host "[1/2] Preparing backend..." -ForegroundColor Yellow

if (-not (Test-Path "$BackendDir\.venv")) {
    Write-Host "    Creating virtual environment..." -ForegroundColor DarkGray
    python -m venv "$BackendDir\.venv"
}

$VenvPython = "$BackendDir\.venv\Scripts\python.exe"
$VenvActivate = "$BackendDir\.venv\Scripts\Activate.ps1"

if (-not (Test-Path $VenvActivate)) {
    Write-Host "    [WARN] Activate.ps1 not found. Trying Activate.bat..." -ForegroundColor DarkYellow
    $VenvActivate = "$BackendDir\.venv\Scripts\activate.bat"
}

# Install dependencies if needed
& $VenvPython -m pip show fastapi > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "    Installing Python dependencies..." -ForegroundColor DarkGray
    & $VenvPython -m pip install -r "$BackendDir\requirements.txt"
}

Write-Host "    Starting backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
# Start backend in background (hidden window, stdout piped to null)
$BackendJob = Start-Process `
    -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000", "--host", "127.0.0.1" `
    -WorkingDirectory $BackendDir `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput "$env:TEMP\mindjournal_backend.log" `
    -RedirectStandardError "$env:TEMP\mindjournal_backend.err"

Write-Host "    Backend PID: $($BackendJob.Id)" -ForegroundColor DarkGray
Write-Host ""

# ── Frontend ─────────────────────────────────────────────────────────────────

if (-not $NoFrontend) {
    Write-Host "[2/2] Preparing frontend..." -ForegroundColor Yellow

    if (-not (Test-Path "$FrontendDir\node_modules")) {
        Write-Host "    Installing npm dependencies (first run)..." -ForegroundColor DarkGray
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }

    Write-Host "    Starting frontend on http://127.0.0.1:5173 ..." -ForegroundColor Green
    $FrontendJob = Start-Process `
        -FilePath "npm" `
        -ArgumentList "run", "dev" `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Normal `
        -PassThru

    Write-Host "    Frontend PID: $($FrontendJob.Id)" -ForegroundColor DarkGray
    Write-Host ""
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API & docs :  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend UI        :  http://localhost:5173/" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C or close this window to stop all services." -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Wait for backend job; clean up on Ctrl+C
try {
    $BackendJob | Wait-Process -ErrorAction SilentlyContinue
} finally {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    if ($BackendJob -and -not $BackendJob.HasExited) { Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue }
    if ($FrontendJob -and -not $FrontendJob.HasExited) { Stop-Process -Id $FrontendJob.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "Done." -ForegroundColor Green
}
