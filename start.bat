@echo off
setlocal
title SmartFace
cd /d "%~dp0"

set "PYTHON=%~dp0.venv-smartface-new\Scripts\python.exe"

if exist "%PYTHON%" (
    "%PYTHON%" --version >nul 2>&1
)

if not exist "%PYTHON%" goto install_python
if errorlevel 1 goto install_python
goto run_smartface

:install_python
    echo Chua co moi truong SmartFace. Dang cai dat lan dau...
    call "%~dp0install-python.bat" /auto
    if errorlevel 1 (
        echo.
        echo Cai dat Python that bai.
        pause
        exit /b 1
    )

:run_smartface
"%PYTHON%" "%~dp0scripts\start_smartface.py"
if errorlevel 1 (
    echo.
    echo SmartFace gap loi khi khoi dong.
    pause
)
