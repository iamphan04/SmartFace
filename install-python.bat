@echo off
setlocal
cd /d "%~dp0"

set "BASE_PYTHON=%~dp0.python\python.exe"
set "VENV=%~dp0.venv-smartface-new"
set "INSTALLER="

if not exist "%BASE_PYTHON%" (
    for %%I in ("%~dp0python-*-amd64.exe") do if exist "%%~fI" set "INSTALLER=%%~fI"
    if not defined INSTALLER (
        for %%I in ("D:\cuasu\python-*-amd64.exe") do if exist "%%~fI" set "INSTALLER=%%~fI"
    )

    if not defined INSTALLER (
        echo KHONG TIM THAY BO CAI PYTHON.
        echo Dat file python-*-amd64.exe canh install-python.bat.
        if /i not "%~1"=="/auto" pause
        exit /b 1
    )

    echo Dang cai Python local...
    "%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_launcher=0 TargetDir="%~dp0.python"
    if not exist "%BASE_PYTHON%" (
        "%INSTALLER%" /repair /quiet
    )
    if not exist "%BASE_PYTHON%" (
        echo Cai Python that bai.
        if /i not "%~1"=="/auto" pause
        exit /b 1
    )
)

set "REBUILD_VENV=0"
if not exist "%VENV%\Scripts\python.exe" set "REBUILD_VENV=1"
if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" --version >nul 2>&1
    if errorlevel 1 set "REBUILD_VENV=1"
)

if "%REBUILD_VENV%"=="1" (
    echo Dang tao moi truong Python...
    "%BASE_PYTHON%" -m venv --clear "%VENV%"
    if errorlevel 1 (
        if /i not "%~1"=="/auto" pause
        exit /b 1
    )
)

echo Moi truong Python da san sang.
if /i not "%~1"=="/auto" pause
