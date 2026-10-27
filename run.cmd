@echo off
rem Start John Bot with the project's own interpreter.
rem Plain "python" may be a different Python that has no discord.py installed.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found in %CD%
    echo Create it first:
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m johnbot
set "code=%ERRORLEVEL%"

if not "%code%"=="0" (
    echo.
    echo John Bot stopped with exit code %code%.
    pause
)
endlocal & exit /b %code%
