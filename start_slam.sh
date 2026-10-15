#!/usr/bin/env bash
# ==============================================================================
# LOGIX AMR — SLAM (Harita Çıkarma) Başlatıcı
# ==============================================================================
# Kullanım:
#   bash start_slam.sh
#
# Bu script sırasıyla şunları başlatır:
#   1. ROS 2 + workspace setup
#   2. real_bringup  → LiDAR (urg_node) + RF2O odometri + robot_state_publisher
#   3. arduino_mega_bridge → /cmd_vel → Arduino Mega seri köprüsü
#   4. slam_toolbox  → Boş haritadan sıfır başlar, ekran açılmaz
#   5. Web SCADA     → http://<IP>:8080  (teleop + canlı harita)
#
# Haritayı kaydetmek için yeni bir terminalde:
#   ros2 run nav2_map_server map_saver_cli \
#       -f ~/Navigation/src/ackermann_car_sim/maps/real_room_map
# ==============================================================================

set -e
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── ROS 2 kaynak yükle ──────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       LOGIX AMR  •  SLAM (Harita Çıkarma) Modu              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if   [ -f /opt/ros/jazzy/setup.bash ];  then source /opt/ros/jazzy/setup.bash
elif [ -f /opt/ros/humble/setup.bash ]; then source /opt/ros/humble/setup.bash
else echo "❌ ROS 2 kurulu değil!" && exit 1; fi

source "$WS/install/setup.bash"
echo "✅ [1/4] ROS 2 ve workspace yüklendi."

# ── Temizlik fonksiyonu ──────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "🛑 [SLAM DURDURULUYOR] Tüm süreçler kapatılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    pkill -f "urg_node"              2>/dev/null || true
    pkill -f "rf2o_laser_odometry"   2>/dev/null || true
    pkill -f "async_slam_toolbox"    2>/dev/null || true
    pkill -f "arduino_mega_bridge"   2>/dev/null || true
    pkill -f "web/server.py"         2>/dev/null || true
    echo "✅ Tüm süreçler durduruldu."
    echo "💾 Haritayı kaydetmek için:"
    echo "   ros2 run nav2_map_server map_saver_cli \\"
    echo "       -f ~/Navigation/src/ackermann_car_sim/maps/real_room_map"
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

# ── 3. SLAM Toolbox — Boş harita, headless ──────────────────────────────────
echo ""
echo "🗺️  [4/4] SLAM Toolbox başlatılıyor (boş harita, ekran yok)..."
ros2 launch ackermann_car_sim slam.launch.py \
    use_sim_time:=false \
    use_rviz:=false \
    > /tmp/slam.log 2>&1 &
SLAM_PID=$!
sleep 3
echo "✅ SLAM hazır. (log: /tmp/slam.log)"

# ── 4. Web SCADA ─────────────────────────────────────────────────────────────
python3 "$WS/src/ackermann_car_sim/web/server.py" \
    > /tmp/web.log 2>&1 &
WEB_PID=$!
sleep 1

ROBOT_IP=$(hostname -I | awk '{print $1}')

clear
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        🗺️   LOGIX AMR  •  SLAM MODU AKTİF                   ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Web Arayüzü (Teleop + Canlı Harita):                       ║"
echo "║  ➡  http://$ROBOT_IP:8080/mapping.html        ║"
echo "║                                                              ║"
echo "║  Haritayı Kaydetmek İçin (Yeni terminalde):                  ║"
echo "║  ros2 run nav2_map_server map_saver_cli \\                    ║"
echo "║      -f ~/Navigation/src/ackermann_car_sim/maps/real_room_map║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Loglar:  tail -f /tmp/slam.log                              ║"
echo "║           tail -f /tmp/bringup.log                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Ctrl+C  →  Tüm süreçleri güvenle durdurur."
echo ""

# Tüm arka plan süreçlerinin bitmesini bekle
wait
