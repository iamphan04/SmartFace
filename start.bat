@echo off
title He thong xac thuc SmartFace

echo Dang khoi dong SmartFace...
cd /d "%~dp0"

set "PYTHON=%~dp0.venv-smartface312\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo KHONG TIM THAY MOI TRUONG PYTHON:
    echo %PYTHON%
    echo Hay chay: install-python.bat
    pause
    exit /b 1
)

if not exist "frontend\dist-app\index.html" (
    echo Dang build frontend...
    call npm --prefix frontend run build
    if errorlevel 1 exit /b 1
)

start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"
"%PYTHON%" database_pdt\main.py

echo.
echo SmartFace da dung hoac gap loi.
pause
