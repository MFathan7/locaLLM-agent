@echo off
if exist "%~dp0.venv\Scripts\locallm.exe" (
    "%~dp0.venv\Scripts\locallm.exe" %*
) else if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m locallm %*
) else (
    py -m locallm %* 2>nul || python -m locallm %*
)
