#!/usr/bin/env bash
# ==============================================================================
# NEXUS AUTONOMOUS - AMR WEB FLEET CONTROL SERVER BASLATICI
# ==============================================================================

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

echo "================================================================"
echo "🚀 NEXUS AUTONOMOUS | Fleet Control Web Server Başlatılıyor..."
echo "================================================================"

source /opt/ros/humble/setup.bash
source "$WORKSPACE_DIR/install/setup.bash"

# Port 8080 kullanan eski bir süreç varsa temizle
fuser -k 8080/tcp 2>/dev/null || true

cleanup() {
    echo ""
    echo "🛑 Web sunucusu kapatılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    pkill -f "web/server.py" 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Tarayıcıyı 2 saniye sonra otomatik aç
(
    sleep 2
    if which xdg-open > /dev/null 2>&1; then
        xdg-open "http://localhost:8080" > /dev/null 2>&1
    elif which google-chrome > /dev/null 2>&1; then
        google-chrome "http://localhost:8080" > /dev/null 2>&1
    fi
) &

python3 "$WORKSPACE_DIR/src/ackermann_car_sim/web/server.py"
