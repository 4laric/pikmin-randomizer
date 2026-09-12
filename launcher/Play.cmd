@echo off
setlocal
rem Pikipelago entry point. Double-click, or drag a seed.json onto this file.
rem Opens the launcher window. Uses the bundled runtime when present, otherwise a system Python 3.12+.
rem "Play.cmd --console [seed.json]" runs the text launcher instead.
set "ROOT=%~dp0"
set "PY="
set "PYW="

if exist "%ROOT%runtime\python.exe" (
    set "PY=%ROOT%runtime\python.exe"
    if exist "%ROOT%runtime\pythonw.exe" set "PYW=%ROOT%runtime\pythonw.exe"
    goto :run
)

py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3.12"
    set "PYW=pyw -3.12"
    goto :run
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
    set "PYW=pythonw"
    goto :run
)

echo.
echo Python 3.12 or newer was not found.
echo Install it from https://www.python.org/downloads/windows/ (tick "Add python.exe to PATH"),
echo or use a release zip that includes the runtime folder.
echo.
pause
exit /b 1

:run
if /I "%~1"=="--console" (
    %PY% "%ROOT%launcher\launcher.py" --pause-on-exit %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %errorlevel%
)
if "%PYW%"=="" set "PYW=%PY%"
rem The window keeps its own log. If it cannot open, the console launcher takes over.
%PYW% "%ROOT%launcher\gui.py" %*
if errorlevel 1 (
    %PY% "%ROOT%launcher\launcher.py" --pause-on-exit %*
)
exit /b %errorlevel%
