@echo off
setlocal
cd /d "%~dp0"

:: 1. Check if compiled standalone portable exe exists
if exist "%~dp0dist\StealthGuard\StealthGuard.exe" (
    start "" "%~dp0dist\StealthGuard\StealthGuard.exe" --stealth %*
    exit /b 0
)
if exist "%~dp0StealthGuard.exe" (
    start "" "%~dp0StealthGuard.exe" --stealth %*
    exit /b 0
)

:: 2. Fallback to Pythonw (windowless)
set "PYTHONW_EXE=pythonw"
where pythonw >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe" (
        set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"
    )
)

start "" "%PYTHONW_EXE%" "%~dp0main.py" --stealth %*
