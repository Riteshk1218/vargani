@echo off
cd /d "%~dp0"
docker compose stop
echo  The demo is stopped. Your demo data is kept for next time.
pause
