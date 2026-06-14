@echo off
setlocal
cd /d "%~dp0"

set "BASE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
set "VENV=%~dp0.venv-smartface312"

if not exist "%BASE_PYTHON%" (
    echo Khong tim thay CPython 3.12:
    echo %BASE_PYTHON%
    echo Cai Python 3.12 x64 tu python.org truoc.
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
    echo Dang tao virtual environment...
    "%BASE_PYTHON%" -m venv "%VENV%"
    if errorlevel 1 exit /b 1
)

echo Dang cap nhat pip...
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo Dang cai thu vien SmartFace...
"%VENV%\Scripts\python.exe" -m pip install -r database_pdt\requirements.txt
if errorlevel 1 exit /b 1

echo.
echo Cai dat hoan tat.
"%VENV%\Scripts\python.exe" -c "import cv2, mediapipe, pyzbar, fastapi, uvicorn; print('SmartFace dependencies OK')"
pause
