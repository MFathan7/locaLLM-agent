@echo off
setlocal
cd /d "%~dp0"

echo [locaLLM] Starting Windows Installation...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% NEQ 0 (
    echo.
    echo [ERROR] Installation failed with exit code %EXIT_CODE%.
    echo %cmdcmdline% | find /i "%~0" >nul && pause
    exit /b %EXIT_CODE%
)

echo %cmdcmdline% | find /i "%~0" >nul && pause
endlocal
