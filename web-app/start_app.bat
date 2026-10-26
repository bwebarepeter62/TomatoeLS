@echo off
setlocal enabledelayedexpansion
title Tomato Leaf Scan — Local Web Server
cd /d "%~dp0"

echo ==========================================================
echo Starting Tomato Leaf Scan Web Application
echo ==========================================================

:: Optional: run `start_app.bat --fresh` to wipe the database (farms, scans, photos) on startup.
:: A timestamped backup is saved in database\ first. Normal launches keep your data.
if /i "%~1"=="--fresh" (
    set LEAFSCAN_RESET_DB=1
    echo [FRESH MODE] Database will be reset on startup.
)

:: 1. Detect Python executable
set PYTHON_CMD=

:: Check local or parent virtual environments first
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=".venv\Scripts\python.exe"
    echo Using local virtual environment: .venv
) else if exist "..\.venv\Scripts\python.exe" (
    set PYTHON_CMD="..\.venv\Scripts\python.exe"
    echo Using project virtual environment: ..\.venv
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    echo Using Python 3.11 from LocalAppData
) else if exist "%ProgramFiles%\Python311\python.exe" (
    set PYTHON_CMD="%ProgramFiles%\Python311\python.exe"
    echo Using Python 3.11 from Program Files
) else (
    :: Check Windows py launcher for Python 3.11
    py -3.11 --version >nul 2>nul
    if not errorlevel 1 (
        set PYTHON_CMD=py -3.11
        echo Using Python 3.11 via py launcher
    ) else (
        :: Check system PATH
        where python >nul 2>nul
        if not errorlevel 1 (
            set PYTHON_CMD=python
            echo Using Python from system PATH
        )
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python was not found on your computer.
    echo Please install Python 3.11 from https://www.python.org/downloads/windows/
    echo Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Verify or install dependencies
echo Checking dependencies from requirements.txt...
%PYTHON_CMD% -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies could not be installed automatically. Attempting to start server...
)

:: 3. Launch browser in background
where curl >nul 2>nul
if not errorlevel 1 (
    start "" http://127.0.0.1:5000
)

:: 4. Start Flask server
echo.
echo ==========================================================
echo Serving Tomato Leaf Scan at http://127.0.0.1:5000
echo Press CTRL+C to stop the server.
echo ==========================================================
echo.
%PYTHON_CMD% backend\app.py

if errorlevel 1 (
    echo.
    echo [ERROR] The server stopped unexpectedly with error code %ERRORLEVEL%.
)
echo.
pause
