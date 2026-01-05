@echo off
REM ClearPerks Backend Launcher
REM This script activates the virtual environment and runs the FastAPI app

echo Checking for virtual environment...
if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call venv\Scripts\activate.bat
) else (
    echo Error: venv not found at venv\Scripts\activate.bat
    pause
    exit /b 1
)

echo.
echo Starting FastAPI application...
echo running: python -m uvicorn app.main:app --reload
echo.

python -m uvicorn app.main:app --reload

if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
