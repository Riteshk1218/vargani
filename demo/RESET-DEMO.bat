@echo off
cd /d "%~dp0"
echo  This deletes everything you entered in the demo and starts fresh next time.
set /p ok=Type YES to continue: 
if /i not "%ok%"=="YES" exit /b 0
docker compose down -v
echo  Done. Double-click START-DEMO to begin again with fresh demo data.
pause
