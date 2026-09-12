@echo off
setlocal
rem Pikmin Randomizer entry point. Drag a seed.json onto this file, or run it directly.
rem Uses the bundled runtime when present, otherwise a system Python 3.12 or newer.
set "ROOT=%~dp0"
set "PY="

if exist "%ROOT%runtime\python.exe" (
    set "PY=%ROOT%runtime\python.exe"
    goto :run
)

py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3.12"
    goto :run
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY=python"
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
%PY% "%ROOT%launcher\launcher.py" --pause-on-exit %*
exit /b %errorlevel%
