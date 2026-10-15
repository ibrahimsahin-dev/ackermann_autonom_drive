#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
ALT SEVİYE DONANIM TESTİ 4: TF KOORDİNAT DÖNÜŞÜM AĞACI SAĞLIK TESTİ
==============================================================================
Nav2 ve SLAM'in çalışabilmesi için TF dönüşüm zincirinin kesintisiz olması gerekir:
    odom  --->  base_footprint  --->  base_link  --->  lidar_link

Bu araç, bu zincirdeki tüm TF bağlantılarını sorgular ve gecikmelerini ölçer.
==============================================================================
Kullanım:
    python3 test_04_tf_tree.py
==============================================================================
"""

import time
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
import tf2_ros

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

class TfSanityTester(Node):
    def __init__(self):
        super().__init__('tf_sanity_tester')
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        self.timer = self.create_timer(1.5, self.check_transforms)
        print(f"\n{BOLD}{CYAN}==================================================================")
        print(f"🔗 ALT SEVİYE TEST 4: TF (KOORDİNAT DÖNÜŞÜM) AĞACI DENETLEYİCİ")
        print(f"=================================================================={RESET}")
        print("TF ağacı taranıyor... (Çıkmak için Ctrl+C)\n")

    def check_transforms(self):
        links_to_test = [
            ("odom", "base_footprint", "Odometri Bağlantısı (Motor / Lazer Odometri)"),
            ("base_footprint", "base_link", "Araç Taban Şasisi (URDF / Robot State Publisher)"),
            ("base_link", "lidar_link", "LiDAR Sensör Montajı (URDF / Robot State Publisher)"),
            ("base_link", "laser", "LiDAR Sensör Gözü (urg_node 'laser' Frame)"),
            ("odom", "laser", "Uçtan Uca Tam Zincir (Nav2 & RF2O için Kritik)")
        ]

        print("\033[H\033[J", end="") # Ekranı temizle
        print(f"{BOLD}{CYAN}==================================================================")
        print(f"🔗 TF DÖNÜŞÜM AĞACI DURUM RAPORU")
        print(f"=================================================================={RESET}")

        all_ok = True
        for source, target, desc in links_to_test:
            try:
                # 0.5 saniye bekleme süresiyle dönüşümü ara
                t = self.tf_buffer.lookup_transform(
                    source,
                    target,
                    rclpy.time.Time(),
                    timeout=Duration(seconds=0.3)
                )
                
                pos = t.transform.translation
                print(f"• {BOLD}{source:14} ➔  {target:14}{RESET} : {GREEN}✔ AKTİF{RESET}")
                print(f"  └─ Konum: [{pos.x:+.3f}, {pos.y:+.3f}, {pos.z:+.3f}]  |  Açıklama: {desc}")
                
            except Exception as ex:
                all_ok = False
                print(f"• {BOLD}{source:14} ➔  {target:14}{RESET} : {RED}❌ KOPUK VEYA GECİKMELİ{RESET}")
                print(f"  └─ Hata: {str(ex)[:70]}... | İpucu: {desc}")

        print(f"------------------------------------------------------------------")
        if all_ok:
            print(f"{GREEN}{BOLD}🎉 TEBRİKLER: Tüm TF zinciri eksiksiz ve Nav2 için hazır!{RESET}")
        else:
            print(f"{YELLOW}{BOLD}⚠️  UYARI: Bazı TF zincirleri eksik. 'robot_state_publisher' veya odometri çalışıyor mu?{RESET}")
        print(f"==================================================================")


def main():
    rclpy.init()
    tester = TfSanityTester()
    try:
        rclpy.spin(tester)
    except KeyboardInterrupt:
        pass
    finally:
        tester.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
