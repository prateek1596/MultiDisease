@echo off
REM ============================================================
REM  MedPredict — Environment Setup for Windows (Python 3.11)
REM  Run this from the project root:  setup_env.bat
REM ============================================================

echo.
echo ============================================================
echo  MedPredict Environment Setup
echo  Creating Python 3.11 conda environment (ML-compatible)
echo ============================================================
echo.

REM Create fresh environment with Python 3.11
echo [1/4] Creating conda environment with Python 3.11...
conda create -n medpredict python=3.11 -y
if errorlevel 1 (
    echo ERROR: Failed to create conda environment
    pause
    exit /b 1
)

echo.
echo [2/4] Activating environment...
call conda activate medpredict

echo.
echo [3/4] Installing ML dependencies via pip...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed
    pause
    exit /b 1
)

echo.
echo [4/4] Creating .env file from template...
if not exist .env (
    copy .env.example .env
    echo .env created from template
) else (
    echo .env already exists - skipping
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  To start the backend:
echo    conda activate medpredict
echo    cd backend
echo    python scripts/train_all.py          (first time only)
echo    uvicorn app.main:app --reload --port 8000
echo.
echo  To start the frontend (new terminal):
echo    cd frontend
echo    npm install
echo    npm run dev
echo ============================================================
echo.
pause
