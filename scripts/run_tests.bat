@echo off
cd /d "%~dp0\.."

echo ==========================================================
echo Running Tomato Leaf Scan Automated Regression Test Suite
echo ==========================================================
echo.

python web-app\tests\test_app.py

echo.
pause
