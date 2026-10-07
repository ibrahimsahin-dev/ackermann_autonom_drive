#!/usr/bin/env bash
# ==============================================================================
# OTONOM ACKERMANN ARAC - HARITA KAYDEDICI
# ==============================================================================

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

source /opt/ros/humble/setup.bash
source "$WORKSPACE_DIR/install/setup.bash"

MAP_DIR="$WORKSPACE_DIR/src/ackermann_car_sim/maps"
mkdir -p "$MAP_DIR"

echo "💾 Çıkarılan 2D Harita '$MAP_DIR/arena_map' olarak kaydediliyor..."
ros2 run nav2_map_server map_saver_cli -f "$MAP_DIR/arena_map"

if [ -f "$MAP_DIR/arena_map.yaml" ]; then
    echo ""
    echo "🎉 HARİTA BAŞARIYLA KAYDEDİLDİ!"
    echo "Dosyalar:"
    echo "  - $MAP_DIR/arena_map.yaml"
    echo "  - $MAP_DIR/arena_map.pgm"
    echo ""
    echo "Artık './start_navigation.sh' betiğini çalıştırarak tam otonom sürüşe geçebilirsin!"
else
    echo "❌ HATA: Harita kaydedilemedi. SLAM Toolbox'ın çalıştığından emin ol."
fi
