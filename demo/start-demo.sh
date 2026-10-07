#!/bin/sh
# Mac / Linux: start the Vargani demo (needs Docker Desktop running).
cd "$(dirname "$0")" || exit 1
docker compose up -d --build || exit 1
echo "Waiting for the demo to be ready..."
until curl -sf http://localhost:8080/api/v1/health/ >/dev/null; do sleep 5; done
docker compose wait demo-data >/dev/null 2>&1
echo "Website:    http://localhost:8080   (admin@demo.test / DemoPass#2026)"
echo "Mobile app: http://localhost:8081   (collector@demo.test / DemoPass#2026, or Member tab with 9822001122)"
(open http://localhost:8080 || xdg-open http://localhost:8080) >/dev/null 2>&1
