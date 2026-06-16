@echo off
setlocal
title SmartFace
cd /d "%~dp0"

set "PYTHON="
set "PYTHON_ARGS="

call :try_python "%~dp0.venv-smartface312\Scripts\python.exe"
if defined PYTHON goto run_smartface

call :try_python "%~dp0.venv-smartface-new\Scripts\python.exe"
if defined PYTHON goto run_smartface

call :try_python "%~dp0.python\python.exe"
if defined PYTHON goto run_smartface

call :try_python "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined PYTHON goto run_smartface

where py.exe >nul 2>&1
if not errorlevel 1 (
    py.exe -3.12 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=py.exe"
        set "PYTHON_ARGS=-3.12"
        goto run_smartface
    )
)

where python.exe >nul 2>&1
if not errorlevel 1 (
    python.exe --version >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON=python.exe"
        goto run_smartface
    )
)

:install_python
echo Chua co Python phu hop. Dang cai dat lan dau...
call "%~dp0install-python.bat" /auto
if errorlevel 1 goto python_error

call :try_python "%~dp0.venv-smartface-new\Scripts\python.exe"
if not defined PYTHON goto python_error

:run_smartface
"%PYTHON%" %PYTHON_ARGS% "%~dp0scripts\start_smartface.py"
if errorlevel 1 (
    echo.
    echo SmartFace gap loi khi khoi dong.
    pause
    exit /b 1
)
exit /b 0

:try_python
if not exist "%~1" exit /b 0
"%~1" --version >nul 2>&1
if errorlevel 1 exit /b 0
set "PYTHON=%~1"
exit /b 0

:python_error
echo.
echo Khong tim thay Python 3.12 de khoi dong SmartFace.
echo Hay cai Python 3.12 x64, sau do chay lai start.bat.
pause
exit /b 1
