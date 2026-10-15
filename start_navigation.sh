#!/usr/bin/env bash
# ==============================================================================
# LOGIX AMR — Normal Navigasyon Başlatıcı (Kayıtlı Harita ile AMCL)
# ==============================================================================
# Kullanım:
#   bash start_navigation.sh
#   bash start_navigation.sh /path/to/my_map.yaml   # Farklı harita
#
# Bu script sırasıyla şunları başlatır:
#   1. ROS 2 + workspace setup
#   2. real_bringup  → LiDAR + RF2O odometri + robot_state_publisher
#   3. arduino_mega_bridge → /cmd_vel → Arduino Mega seri köprüsü
#   4. Nav2 Bringup  → AMCL konum tespiti + planner + controller
#   5. Web SCADA     → http://<IP>:8080  (otonom navigasyon arayüzü)
# ==============================================================================

set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Harita dosyası: parametre verilmişse onu kullan, yoksa varsayılan
if [ -n "$1" ]; then
    MAP_FILE="$1"
else
    # Gerçek ortam haritasını tercih et; yoksa arena_map'e dön
    REAL_MAP="$WS/src/ackermann_car_sim/maps/real_room_map.yaml"
    ARENA_MAP="$WS/src/ackermann_car_sim/maps/arena_map.yaml"
    if   [ -f "$REAL_MAP"  ]; then MAP_FILE="$REAL_MAP"
    elif [ -f "$ARENA_MAP" ]; then MAP_FILE="$ARENA_MAP"
    else
        echo "❌ Kayıtlı harita bulunamadı!"
        echo "   Önce SLAM yapın: bash start_slam.sh"
        echo "   Sonra haritayı kaydedin:"
        echo "   ros2 run nav2_map_server map_saver_cli \\"
        echo "       -f ~/Navigation/src/ackermann_car_sim/maps/real_room_map"
        exit 1
    fi
fi

# ── ROS 2 kaynak yükle ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       LOGIX AMR  •  Otonom Navigasyon Modu (AMCL)           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  📂 Kullanılan Harita: $MAP_FILE"
echo ""

if   [ -f /opt/ros/jazzy/setup.bash ];  then source /opt/ros/jazzy/setup.bash
elif [ -f /opt/ros/humble/setup.bash ]; then source /opt/ros/humble/setup.bash
else echo "❌ ROS 2 kurulu değil!" && exit 1; fi

source "$WS/install/setup.bash"
echo "✅ [1/4] ROS 2 ve workspace yüklendi."

# ── Temizlik ─────────────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "🛑 [NAVİGASYON DURDURULUYOR] Tüm süreçler kapatılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    pkill -f "urg_node"            2>/dev/null || true
    pkill -f "rf2o_laser_odometry" 2>/dev/null || true
    pkill -f "arduino_mega_bridge" 2>/dev/null || true
    pkill -f "nav2"                2>/dev/null || true
    pkill -f "web/server.py"       2>/dev/null || true
    echo "✅ Tüm süreçler güvenle durduruldu."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── 1. LiDAR + RF2O Odometri ─────────────────────────────────────────────────
echo ""
echo "📡 [2/4] LiDAR ve RF2O Odometri başlatılıyor..."
ros2 launch ackermann_car_sim real_bringup.launch.py \
    use_rf2o:=true \
    > /tmp/bringup.log 2>&1 &
BRINGUP_PID=$!
sleep 4
echo "✅ LiDAR hazır. (log: /tmp/bringup.log)"

# ── 2. Arduino Mega Motor Köprüsü ───────────────────────────────────────────
echo ""
echo "🔌 [3/4] Arduino Mega seri köprüsü başlatılıyor..."
python3 "$WS/scripts/real_tests/arduino_mega_bridge.py" \
    > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
sleep 2
echo "✅ Motor köprüsü hazır. (log: /tmp/bridge.log)"

# ── 3. Nav2 — AMCL + Planner ─────────────────────────────────────────────────
echo ""
echo "🧭 [4/4] Nav2 navigasyon yığını başlatılıyor (AMCL)..."
ros2 launch ackermann_car_sim nav2.launch.py \
    map:="$MAP_FILE" \
    slam:=False \
    use_sim_time:=false \
    use_rviz:=false \
    > /tmp/nav2.log 2>&1 &
NAV2_PID=$!
sleep 5
echo "✅ Nav2 hazır. (log: /tmp/nav2.log)"

# ── 4. Web SCADA ─────────────────────────────────────────────────────────────
python3 "$WS/src/ackermann_car_sim/web/server.py" \
    > /tmp/web.log 2>&1 &
WEB_PID=$!
sleep 1

ROBOT_IP=$(hostname -I | awk '{print $1}')

clear
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║      🧭  LOGIX AMR  •  OTONOM NAVİGASYON AKTİF              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Web Arayüzü:                                                ║"
echo "║  ➡  http://$ROBOT_IP:8080                    ║"
echo "║                                                              ║"
echo "║  Kullanılan Harita:                                          ║"
echo "║  $MAP_FILE"
echo "║                                                              ║"
echo "║  İlk açılışta robot konumunu harita üzerinde                 ║"
echo "║  '2D Pose Estimate' ile manuel olarak gösterin!              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Loglar:  tail -f /tmp/nav2.log                              ║"
echo "║           tail -f /tmp/bringup.log                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Ctrl+C  →  Tüm süreçleri güvenle durdurur."
echo ""

wait
