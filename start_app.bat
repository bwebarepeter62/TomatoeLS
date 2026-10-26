@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo Tomato Leaf Scan — Master Launcher
echo ==========================================================
echo Launching web application from web-app directory...
echo.

if exist "web-app\start_app.bat" (
    call "web-app\start_app.bat" %*
) else (
    echo [ERROR] web-app\start_app.bat was not found.
    pause
    exit /b 1
)
