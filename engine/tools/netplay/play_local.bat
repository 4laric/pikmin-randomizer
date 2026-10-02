@echo off
REM Local two-window netplay test wrapper (issue #887): runs play_local.ps1
REM with -ExecutionPolicy Bypass. Pass through all arguments, e.g.:
REM   tools\netplay\play_local.bat -Exe build\bin\nectar.exe
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0play_local.ps1" %*
