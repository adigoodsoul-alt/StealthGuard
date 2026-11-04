@echo off
setlocal
cd /d "%~dp0"

:: 1. Check if compiled standalone portable exe exists
if exist "%~dp0dist\StealthGuard\StealthGuard.exe" (
    start "" "%~dp0dist\StealthGuard\StealthGuard.exe" %*
    exit /b 0
)
if exist "%~dp0StealthGuard.exe" (
    start "" "%~dp0StealthGuard.exe" %*
    exit /b 0
)

:: 2. Fallback to Python
set "PYTHON_EXE=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    )
)

start "" "%PYTHON_EXE%" "%~dp0main.py" %*
