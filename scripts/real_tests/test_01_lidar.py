#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
ALT SEVİYE DONANIM TESTİ 1: LIDAR SİNYAL VE AÇI DOĞRULAMA (HOKUYO 270°)
==============================================================================
Bu araç, gerçek Hokuyo LiDAR'dan gelen '/scan' verisini canlı dinler.
- Frekansı (Hz) ölçer
- Açısını (derece cinsinden min, max ve toplam kapsama) hesaplar
- Robotun tam önündeki (0°), solundaki (+90°) ve sağındaki (-90°) mesafeleri
  canlı terminal panosunda gösterir.
==============================================================================
Kullanım:
    python3 test_01_lidar.py
==============================================================================
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

# Terminal renk kodları
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

class LidarSanityTester(Node):
    def __init__(self):
        super().__init__('lidar_sanity_tester')
        
        self.sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            10
        )
        
        self.last_msg_time = 0.0
        self.msg_count = 0
        self.start_time = time.time()
        self.rate_hz = 0.0
        
        # 1 Hz timer ile ekrana durum paneli yazdır
        self.timer = self.create_timer(1.0, self.render_dashboard)
        self.latest_scan = None
        
        print(f"\n{BOLD}{CYAN}================================================================")
        print(f"📡 ALT SEVİYE TEST 1: LIDAR (/scan) BAĞLANTI & SİNYAL TESTİ")
        print(f"================================================================{RESET}")
        print(f"'/scan' topic'i dinleniyor... (Çıkmak için Ctrl+C)\n")

    def scan_callback(self, msg: LaserScan):
        now = time.time()
        self.msg_count += 1
        elapsed = now - self.start_time
        if elapsed >= 1.0:
            self.rate_hz = self.msg_count / elapsed
            self.msg_count = 0
            self.start_time = now
            
        self.last_msg_time = now
        self.latest_scan = msg

    def render_dashboard(self):
        now = time.time()
        if self.latest_scan is None or (now - self.last_msg_time > 3.0):
            print(f"\r{RED}⚠️  HATA: Henüz '/scan' verisi gelmedi veya sinyal kesildi! (LiDAR kablosu veya sürücü kapalı){RESET}", end='', flush=True)
            return

        scan = self.latest_scan
        total_angle_deg = math.degrees(scan.angle_max - scan.angle_min)
        angle_min_deg = math.degrees(scan.angle_min)
        angle_max_deg = math.degrees(scan.angle_max)
        num_points = len(scan.ranges)

        # Ön (0°), Sol (+90°) ve Sağ (-90°) mesafelerini indeksle bul
        front_dist = self.get_distance_at_angle(scan, 0.0)
        left_dist = self.get_distance_at_angle(scan, math.pi / 2.0)
        right_dist = self.get_distance_at_angle(scan, -math.pi / 2.0)

        # 270 derece doğrulaması (yaklaşık 260°-280° aralığı)
        angle_status = f"{GREEN}DOĞRU (270°){RESET}" if 260 <= total_angle_deg <= 280 else f"{YELLOW}UYARI ({total_angle_deg:.1f}°){RESET}"
        hz_status = f"{GREEN}STABİL ({self.rate_hz:.1f} Hz){RESET}" if self.rate_hz >= 7.0 else f"{YELLOW}DÜŞÜK ({self.rate_hz:.1f} Hz){RESET}"

        # Canlı Pano Çıktısı
        print("\033[H\033[J", end="") # Ekranı temizle
        print(f"{BOLD}{CYAN}==================================================================")
        print(f"📡 HOKUYO LIDAR CANLI DONANIM TELEMETRİSİ")
        print(f"=================================================================={RESET}")
        print(f"• Bağlantı Durumu      : {GREEN}🟢 CANLI / BAĞLI{RESET}")
        print(f"• Frame ID              : {BOLD}{scan.header.frame_id}{RESET} (Beklenen: lidar_link)")
        print(f"• Tarama Frekansı       : {hz_status}")
        print(f"• Ölçüm Noktası Sayısı : {num_points} ışın / tur")
        print(f"• Tarama Açısı Kapsamı  : {angle_min_deg:.1f}°  ile  +{angle_max_deg:.1f}°  --> {angle_status}")
        print(f"• Ölçüm Menzili         : Min {scan.range_min:.2f} m  |  Max {scan.range_max:.2f} m")
        print(f"------------------------------------------------------------------")
        print(f"{BOLD}🎯 Canlı Engel Mesafeleri:{RESET}")
        print(f"  ⬆️  ÖN   (0°)   : {self.format_dist(front_dist)}")
        print(f"  ⬅️  SOL  (+90°) : {self.format_dist(left_dist)}")
        print(f"  ➡️  SAĞ  (-90°) : {self.format_dist(right_dist)}")
        print(f"------------------------------------------------------------------")
        print(f"💡 İPUCU: Elinizi LiDAR'ın önüne koyup 'ÖN' mesafesinin anlık değiştiğini teyit edin.")
        print(f"==================================================================")

    def get_distance_at_angle(self, scan: LaserScan, target_angle_rad: float) -> float:
        if target_angle_rad < scan.angle_min or target_angle_rad > scan.angle_max:
            return float('nan')
        
        idx = int(round((target_angle_rad - scan.angle_min) / scan.angle_increment))
        if 0 <= idx < len(scan.ranges):
            val = scan.ranges[idx]
            if scan.range_min <= val <= scan.range_max:
                return val
        return float('nan')

    def format_dist(self, dist: float) -> str:
        if math.isnan(dist) or math.isinf(dist):
            return f"{YELLOW}Menzil Dışı / Boşluk{RESET}"
        elif dist < 0.35:
            return f"{RED}{dist:.2f} m (🚨 ÇOK YAKIN! GÜVENLİK BÖLGESİ){RESET}"
        elif dist < 0.8:
            return f"{YELLOW}{dist:.2f} m (⚠️  YAKIN ENGEL){RESET}"
        else:
            return f"{GREEN}{dist:.2f} m (SERBEST){RESET}"


def main():
    rclpy.init()
    tester = LidarSanityTester()
    try:
        rclpy.spin(tester)
    except KeyboardInterrupt:
        print(f"\n{BOLD}Test kullanıcı tarafından sonlandırıldı.{RESET}")
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
