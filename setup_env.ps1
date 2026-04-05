# ============================================================
#  MedPredict — PowerShell Environment Setup
#  Run from project root:  .\setup_env.ps1
#  Or:  powershell -ExecutionPolicy Bypass -File setup_env.ps1
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  MedPredict — Python 3.11 Environment Setup" -ForegroundColor Cyan
Write-Host "  Solving: Python 3.13 incompatibility with ML libraries" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check conda is available
if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: conda not found. Install Miniconda from https://docs.conda.io" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Removing old environment if it exists..." -ForegroundColor Green
conda env remove -n medpredict -y 2>$null

Write-Host "[2/5] Creating fresh Python 3.11 environment..." -ForegroundColor Green
conda create -n medpredict python=3.11 -y
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create conda environment" -ForegroundColor Red
    exit 1
}

Write-Host "[3/5] Activating environment and installing dependencies..." -ForegroundColor Green
# Use conda run to avoid activation issues in scripts
Set-Location backend

Write-Host "  Installing core ML stack..." -ForegroundColor Yellow
conda run -n medpredict pip install numpy==1.26.4 scipy==1.13.0 scikit-learn==1.4.2 --no-cache-dir

Write-Host "  Installing all requirements..." -ForegroundColor Yellow
conda run -n medpredict pip install -r requirements.txt --no-cache-dir

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pip install failed. Check requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host "[4/5] Setting up .env..." -ForegroundColor Green
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  .env created from template" -ForegroundColor Yellow
    Write-Host "  Edit backend\.env to set your DATABASE_URL if using PostgreSQL" -ForegroundColor Yellow
} else {
    Write-Host "  .env already exists" -ForegroundColor Gray
}

Set-Location ..

Write-Host "[5/5] Installing frontend dependencies..." -ForegroundColor Green
Set-Location frontend
npm install --legacy-peer-deps
Set-Location ..

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Terminal 1 - Backend:" -ForegroundColor White
Write-Host "    conda activate medpredict" -ForegroundColor Gray
Write-Host "    cd backend" -ForegroundColor Gray
Write-Host "    python scripts/train_all.py      # first time only, ~3-10 min" -ForegroundColor Gray
Write-Host "    uvicorn app.main:app --reload --port 8000" -ForegroundColor Gray
Write-Host ""
Write-Host "  Terminal 2 - Frontend:" -ForegroundColor White
Write-Host "    cd frontend" -ForegroundColor Gray
Write-Host "    npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "  Then open: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Login:     admin / admin123" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
