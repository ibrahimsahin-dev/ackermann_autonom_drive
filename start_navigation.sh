#!/usr/bin/env bash
# ==============================================================================
# LOGIX AMR - OTONOM SEVKİYAT & HARİTA TARAMA (NAV2 & SLAM) BAŞLATICI
# ==============================================================================

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

MAP_FILE="$WORKSPACE_DIR/src/ackermann_car_sim/maps/arena_map.yaml"

# SLAM modunu argümanlardan veya haritanın varlığına göre belirle
# Kullanım: ./start_navigation.sh         -> Statik harita + AMCL otonom sevk
#          ./start_navigation.sh slam    -> Canlı harita tarama (SLAM) + Nav2
USE_SLAM="False"

if [[ "$1" == "slam" || "$1" == "--slam" || "$1" == "-s" ]]; then
    USE_SLAM="True"
elif [ ! -f "$MAP_FILE" ]; then
    echo "ℹ️ Henüz kayıtlı harita bulunamadı ($MAP_FILE)."
    echo "Otomatik olarak CANLI HARİTALAMA (SLAM) modunda başlatılıyor..."
    USE_SLAM="True"
fi

echo "================================================================"
echo "🚀 1/3: ROS 2 Humble ve Çalışma Alanı Yükleniyor..."
echo "================================================================"
source /opt/ros/humble/setup.bash
source "$WORKSPACE_DIR/install/setup.bash"

cleanup() {
    echo ""
    echo "🛑 [KAPATILIYOR] Tüm Nav2, SLAM, Gazebo ve Web Sunucusu süreçleri sonlandırılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    pkill -f "gz sim" 2>/dev/null || true
    pkill -f "gz_sim" 2>/dev/null || true
    pkill -f "ign gazebo" 2>/dev/null || true
    pkill -f "parameter_bridge" 2>/dev/null || true
    pkill -f "rf2o_laser_odometry" 2>/dev/null || true
    pkill -f "async_slam_toolbox_node" 2>/dev/null || true
    pkill -f "nav2" 2>/dev/null || true
    pkill -f "rviz2" 2>/dev/null || true
    pkill -f "web/server.py" 2>/dev/null || true
    echo "✅ Sistem temiz bir şekilde kapatıldı."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "================================================================"
echo "🌍 2/3: Gazebo Simülasyonu Başlatılıyor..."
echo "================================================================"
ros2 launch ackermann_car_sim sim.launch.py > /dev/null 2>&1 &
SIM_PID=$!

echo "⏳ Gazebo ve sensörlerin oturması bekleniyor (7 saniye)..."
sleep 7

echo "================================================================"
echo "🌐 3/3: Nexus Autonomous Web Server Başlatılıyor (Port 8080)..."
echo "================================================================"
python3 "$WORKSPACE_DIR/src/ackermann_car_sim/web/server.py" > /dev/null 2>&1 &
WEB_PID=$!
sleep 1

clear
echo "=================================================================="
echo "🎯 LOGIX AMR - ENDÜSTRİYEL OTONOM FİLO YÖNETİM İSTASYONU AKTİF!"
echo "=================================================================="
if [ "$USE_SLAM" == "True" ]; then
    echo "🗺️  ÇALIŞMA MODU: CANLI HARİTA TARAMA (SLAM TOOLBOX + NAV2)"
    echo "   Robot gezdikçe harita anlık büyüyecek ve duvarlar taranacaktır."
    echo "   İşiniz bittiğinde web'den 'Haritayı Kaydet'e basabilir veya"
    echo "   yan sekmeden './save_map.sh' çalıştırabilirsiniz."
else
    echo "📍  ÇALIŞMA MODU: STATİK HARİTA OTONOM SEVKİYAT (AMCL + NAV2)"
    echo "   Kayıtlı Harita: $MAP_FILE"
    echo "   (Canlı haritalama yapmak isterseniz: './start_navigation.sh slam')"
fi
echo "=================================================================="
echo ""
echo "🌐 ENDÜSTRİYEL WEB KONTROL ARAYÜZÜ (SCADA Fleet Station):"
echo "👉 http://localhost:8080"
echo "   - Canlı 2D CAD Mimari Harita & Dinamik SLAM Akışı"
echo "   - Tek Tıkla Sefer Sevk (Nav2 Goal)"
echo "   - ISO 3691-4 Manuel Teleop Sürüş (W/A/S/D)"
echo "   - Intel RealSense Canlı Ön Kamera (FPV PiP)"
echo "   - Gerçek Zamanlı E-STOP Butonu"
echo "=================================================================="
echo ""

if [ "$USE_SLAM" == "True" ]; then
    ros2 launch ackermann_car_sim nav2.launch.py slam:=True
else
    ros2 launch ackermann_car_sim nav2.launch.py map:="$MAP_FILE" slam:=False
fi
