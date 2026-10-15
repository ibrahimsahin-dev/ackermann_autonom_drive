#!/usr/bin/env bash
# ==============================================================================
# LOGIX AMR - GERÇEK ROBOT BAŞLATICI (HARDWARE + NAV2 + WEB SCADA)
# ==============================================================================

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

MAP_FILE="$WORKSPACE_DIR/src/ackermann_car_sim/maps/arena_map.yaml"
USE_SLAM="False"

if [[ "$1" == "slam" || "$1" == "--slam" || "$1" == "-s" ]]; then
    USE_SLAM="True"
elif [ ! -f "$MAP_FILE" ]; then
    echo "ℹ️ Kayıtlı harita bulunamadı ($MAP_FILE)."
    echo "Gerçek ortam CANLI HARİTALAMA (SLAM) modunda başlatılıyor..."
    USE_SLAM="True"
fi

echo "================================================================"
echo "🚀 1/3: ROS 2 ve Çalışma Alanı Yükleniyor..."
echo "================================================================"
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi
source "$WORKSPACE_DIR/install/setup.bash"

cleanup() {
    echo ""
    echo "🛑 [KAPATILIYOR] Gerçek robot donanım ve Nav2 süreçleri sonlandırılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    pkill -f "urg_node" 2>/dev/null || true
    pkill -f "rf2o_laser_odometry" 2>/dev/null || true
    pkill -f "arduino_mega_bridge.py" 2>/dev/null || true
    pkill -f "nav2" 2>/dev/null || true
    pkill -f "web/server.py" 2>/dev/null || true
    echo "✅ Robot güvenle durduruldu."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

export USE_SIM_TIME=false

echo "================================================================"
echo "📡 2/4: Gerçek Sensörler ve Odometri Başlatılıyor..."
echo "================================================================"
ros2 launch ackermann_car_sim real_bringup.launch.py > /dev/null 2>&1 &
BRINGUP_PID=$!

sleep 3

echo "================================================================"
echo "🔌 3/4: Arduino Mega ROS 2 Seri Köprüsü Başlatılıyor..."
echo "================================================================"
python3 "$WORKSPACE_DIR/scripts/real_tests/arduino_mega_bridge.py" > /dev/null 2>&1 &
BRIDGE_PID=$!

sleep 1

echo "================================================================"
echo "🌐 4/4: Web SCADA İstasyonu Başlatılıyor (Port 8080)..."
echo "================================================================"
python3 "$WORKSPACE_DIR/src/ackermann_car_sim/web/server.py" > /dev/null 2>&1 &
WEB_PID=$!
sleep 1

clear
echo "=================================================================="
echo "🎯 LOGIX AMR - GERÇEK ROBOT ÇALIŞMA ALANI AKTİF!"
echo "=================================================================="
echo "IP Adresiniz: $(hostname -I | cut -d' ' -f1):8080"
echo "Web Arayüzü : http://localhost:8080 veya http://<ROBOT_IP>:8080"
echo "=================================================================="

if [ "$USE_SLAM" == "True" ]; then
    ros2 launch ackermann_car_sim nav2.launch.py slam:=True use_sim_time:=False
else
    ros2 launch ackermann_car_sim nav2.launch.py map:="$MAP_FILE" slam:=False use_sim_time:=False
fi
