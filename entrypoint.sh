#!/bin/bash
set -e

echo "=== Starting YouTube Copyright Remover & Autonomous Shorts Pipeline ==="

# 1. Start BotGuard PO-Token Server on port 4416
if [ -f /opt/bgutil/server/build/main.js ]; then
    echo "[PO-Token] Starting BotGuard server on 127.0.0.1:4416..."
    node /opt/bgutil/server/build/main.js --port 4416 &
fi

# 2. Setup & Start Cloudflare WARP userspace proxy (port 40000 SOCKS5, port 40001 HTTP)
mkdir -p /opt/warp
cd /opt/warp

if [ ! -f /opt/warp/wgcf-profile.conf ]; then
    echo "[WARP] Registering new Cloudflare WARP account..."
    wgcf register --accept-tos || true
    wgcf generate || true
fi

if [ -f /opt/warp/wgcf-profile.conf ]; then
    echo "[WARP] Configuring wireproxy daemon..."
    cat << 'EOF' > /opt/warp/wireproxy.conf
WGConfig = /opt/warp/wgcf-profile.conf

[http]
BindAddress = 127.0.0.1:40001

[Socks5]
BindAddress = 127.0.0.1:40000
EOF

    echo "[WARP] Starting wireproxy tunnel daemon..."
    wireproxy -c /opt/warp/wireproxy.conf &
    sleep 2

    # Quick verification
    echo "[WARP] Verifying Cloudflare residential IP routing..."
    curl -s --connect-timeout 5 -x http://127.0.0.1:40001 https://cloudflare.com/cdn-cgi/trace | grep -E "warp|ip|colo" || echo "[WARP] WARP daemon initializing in background"
else
    echo "[WARP] Note: wgcf-profile.conf not generated, continuing with native direct routing"
fi

cd /app

# 3. Start FastAPI Uvicorn Server
echo "[Uvicorn] Starting FastAPI application on port ${PORT:-8080}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
