@echo off
title He thong xac thuc SmartFace

echo Dang khoi dong SmartFace...
cd /d "%~dp0"

if not exist "C:\msys64\ucrt64\bin\python.exe" (
    echo KHONG TIM THAY PYTHON:
    echo C:\msys64\ucrt64\bin\python.exe
    pause
    exit /b 1
)

if not exist "frontend\dist-app\index.html" (
    echo Dang build frontend...
    call npm --prefix frontend run build
    if errorlevel 1 exit /b 1
)

start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"
"C:\msys64\ucrt64\bin\python.exe" database_pdt\main.py

echo.
echo SmartFace da dung hoac gap loi.
pause
