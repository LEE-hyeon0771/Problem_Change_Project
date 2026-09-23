@echo off
REM Double-click this file to start the app.
REM Korean messages are printed by dev.ps1 (UTF-8), so switch the console codepage first.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1" %*
if errorlevel 1 (
  echo.
  pause
)
endlocal
