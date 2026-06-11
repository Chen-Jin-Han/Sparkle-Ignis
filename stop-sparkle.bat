@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\stop-sparkle.ps1"
endlocal
