#!/usr/bin/env bash
# ==============================================================================
# OTONOM ACKERMANN ARAC - TEK TUSLA HARITALAMA (SLAM) BASLATICI
# ==============================================================================

# Scriptin bulunduğu dizine git
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$WORKSPACE_DIR"

echo "================================================================"
echo "🚀 1/3: ROS 2 Humble ve Çalışma Alanı Yükleniyor..."
echo "================================================================"
source /opt/ros/humble/setup.bash
source "$WORKSPACE_DIR/install/setup.bash"

# Çıkışta (Ctrl+C) arka plandaki tüm simülasyon ve SLAM süreçlerini temizleyen fonksiyon
cleanup() {
    echo ""
    echo "🛑 [KAPATILIYOR] Tüm simülasyon, RViz ve SLAM süreçleri sonlandırılıyor..."
    kill $(jobs -p) 2>/dev/null || true
    # Gazebo ve ros_gz_bridge kalan süreçlerini zorla temizle
    pkill -f "gz sim" 2>/dev/null || true
    pkill -f "gz_sim" 2>/dev/null || true
    pkill -f "ign gazebo" 2>/dev/null || true
    pkill -f "parameter_bridge" 2>/dev/null || true
    pkill -f "rf2o_laser_odometry" 2>/dev/null || true
    pkill -f "async_slam_toolbox_node" 2>/dev/null || true
    pkill -f "robot_state_publisher" 2>/dev/null || true
    echo "✅ Sistem başarıyla kapatıldı ve temizlendi."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "================================================================"
echo "🌍 2/3: Gazebo Simülasyonu ve Arabamız Başlatılıyor..."
echo "================================================================"
ros2 launch ackermann_car_sim sim.launch.py > /dev/null 2>&1 &
SIM_PID=$!

echo "⏳ Gazebo ve fizik motorunun oturması bekleniyor (6 saniye)..."
sleep 6

echo "================================================================"
echo "🗺️ 3/3: SLAM Toolbox (Haritalama) ve RViz2 Açılıyor..."
echo "================================================================"
ros2 launch ackermann_car_sim slam.launch.py > /dev/null 2>&1 &
SLAM_PID=$!

sleep 3

clear
echo "=================================================================="
echo "🎮 ARABA KLAVYE SÜRÜŞ KONSOLU AKTİF!"
echo "=================================================================="
echo "Araba ve SLAM arka planda çalışıyor. RViz ve Gazebo pencerelerini"
echo "ekranında görebilirsin. Şimdi bu terminalde kalarak arabayı sür:"
echo ""
echo "           [ i ] İLERİ DÜZ"
echo "  [ u ] İLERİ SOL     [ o ] İLERİ SAĞ"
echo "  [ j ] SOLA DÖN      [ l ] SAĞA DÖN"
echo "           [ k ] DUR (FREN!)"
echo "  [ m ] GERİ SOL      [ . ] GERİ SAĞ"
echo "           [ , ] GERİ DÜZ"
echo ""
echo "  Hız Ayarları:"
echo "    [ w ] / [ x ] : İleri-Geri hızını artır / azalt"
echo "    [ e ] / [ c ] : Direksiyon dönüş açısını artır / azalt"
echo ""
echo "⚠️  ÖNEMLİ: Bu terminal penceresi seçiliyken tuşlara basmalısın!"
echo "Çıkmak için istediğin an [Ctrl + C] tuşuna basabilirsin."
echo "=================================================================="
echo ""

# Klavyeden sürüş düğümünü ön planda çalıştır
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args --remap cmd_vel:=/cmd_vel
