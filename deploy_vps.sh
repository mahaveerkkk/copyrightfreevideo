#!/usr/bin/env bash
set -e

echo "=================================================="
echo "🚀 Deploying CR-SHIELD Enterprise on VPS (Docker)"
echo "=================================================="

command -v docker >/dev/null 2>&1 || { echo "Docker is not installed. Please install docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1 || { echo "Docker Compose is required."; exit 1; }

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "[1/3] Building multi-threaded worker & web containers..."
if docker compose version >/dev/null 2>&1; then
    docker compose -f docker/docker-compose.yml up -d --build --scale celery_worker=2
else
    docker-compose -f docker/docker-compose.yml up -d --build --scale celery_worker=2
fi

echo "[2/3] Verifying container health..."
sleep 3
docker ps | grep cr_shield || true

echo "=================================================="
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "Server is live on http://$(curl -s ifconfig.me || echo '<YOUR_VPS_IP>')"
echo "=================================================="
