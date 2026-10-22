@echo off
title Vargani demo
cd /d "%~dp0"
echo.
echo  Starting the Vargani demo. The first time takes 5-15 minutes (it downloads about 1.5 GB).
echo.
docker version >nul 2>&1
if errorlevel 1 (
  echo  Docker Desktop is not running. Open Docker Desktop, wait until it says "Engine running",
  echo  then double-click START-DEMO again.
  pause
  exit /b 1
)
docker compose up -d --build
if errorlevel 1 (
  echo.
  echo  Something went wrong. Take a photo of this window and send it to Claude.
  pause
  exit /b 1
)
echo.
echo  Waiting for the demo to be ready...
:wait
timeout /t 5 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://localhost:8080/api/v1/health/ | findstr 200 >nul
if errorlevel 1 goto wait
docker compose wait demo-data >nul 2>&1
echo.
echo  ============================================================
echo   Vargani is running.
echo     Website:     http://localhost:8080
echo     Mobile app:  http://localhost:8081
echo.
echo   Committee login:  admin@demo.test      password DemoPass#2026
echo   Collector login:  collector@demo.test  password DemoPass#2026
echo   Super admin:      http://localhost:8080/django-admin/  superadmin@demo.test  password DemoPass#2026
echo   Member login:     Member tab, mobile 9822001122 (code fills in by itself)
echo  ============================================================
echo.
start "" http://localhost:8080
start "" http://localhost:8081
echo  You can close this window. To stop the demo, double-click STOP-DEMO.
pause
