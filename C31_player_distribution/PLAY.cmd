@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0runtime\python\tools\python.exe" (
  echo Bundled Python is missing. Extract the entire ZIP, then open PLAY.cmd.
  pause
  exit /b 1
)
echo Starting C-3... Please wait. Your browser will open automatically.
"%~dp0runtime\python\tools\python.exe" -I -X utf8 "%~dp0launch.py"
set "C31_RESULT=%ERRORLEVEL%"
if not "%C31_RESULT%"=="0" (
  echo.
  echo Please keep this message or check logs\server.log.
  pause
)
exit /b %C31_RESULT%
