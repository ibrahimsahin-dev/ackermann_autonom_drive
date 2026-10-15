#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
SLAM TANI ARACI - RF2O Odometri + TF + /scan Sağlık Kontrolü
==============================================================================
Kullanım:
    python3 scripts/real_tests/test_slam_diagnosis.py
    (real_bringup.launch.py çalışıyor olmalı!)
==============================================================================
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
import tf2_ros

GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
CYAN   = '\033[96m'
BOLD   = '\033[1m'
RESET  = '\033[0m'


class SlamDiagnosis(Node):
    def __init__(self):
        super().__init__('slam_diagnosis')

        # /odom
        self.odom_received = False
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_time = 0.0
        self.odom_hz = 0.0
        self._odom_count = 0
        self._odom_t0 = time.time()
        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)

        # /scan
        self.scan_received = False
        self.scan_hz = 0.0
        self._scan_count = 0
        self._scan_t0 = time.time()
        self.create_subscription(LaserScan, '/scan', self._scan_cb, 10)

        # TF
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.create_timer(1.0, self._render)

        print(f"\n{BOLD}{CYAN}{'='*68}")
        print(f"🔬 SLAM TANI ARACI — RF2O Odometri + TF + LiDAR Sağlık Testi")
        print(f"{'='*68}{RESET}")
        print(f"(Çıkmak için Ctrl+C)\n")

    # ---- Callbacks -------------------------------------------------------

    def _odom_cb(self, msg: Odometry):
        self.odom_received = True
        self.odom_x = msg.pose.pose.position.x
        self.odom_y = msg.pose.pose.position.y
        self.odom_time = time.time()
        self._odom_count += 1
        dt = time.time() - self._odom_t0
        if dt >= 2.0:
            self.odom_hz = self._odom_count / dt
            self._odom_count = 0
            self._odom_t0 = time.time()

    def _scan_cb(self, msg: LaserScan):
        self.scan_received = True
        self.scan_time = time.time()
        self._scan_count += 1
        dt = time.time() - self._scan_t0
        if dt >= 2.0:
            self.scan_hz = self._scan_count / dt
            self._scan_count = 0
            self._scan_t0 = time.time()

    # ---- Dashboard -------------------------------------------------------

    def _ok(self, condition: bool, ok_msg: str, fail_msg: str) -> str:
        return f"{GREEN}✅ {ok_msg}{RESET}" if condition else f"{RED}❌ {fail_msg}{RESET}"

    def _render(self):
        now = time.time()
        print("\033[H\033[J", end="")  # Ekranı temizle
        print(f"{BOLD}{CYAN}{'='*68}")
        print(f"🔬 SLAM TANI ARACI")
        print(f"{'='*68}{RESET}")

        # --- /scan
        scan_fresh = hasattr(self, 'scan_time') and (now - self.scan_time < 2.0)
        print(f"\n📡 LiDAR (/scan):")
        print(f"  {self._ok(scan_fresh, f'Veri geliyor — {self.scan_hz:.1f} Hz', 'VERİ YOK! LiDAR veya urg_node kapalı')}")

        # --- /odom
        odom_fresh = self.odom_received and (now - self.odom_time < 2.0)
        print(f"\n🔢 Odometri (/odom — RF2O):")
        if odom_fresh:
            print(f"  {GREEN}✅ Veri geliyor — {self.odom_hz:.1f} Hz{RESET}")
            print(f"     Konum: x={self.odom_x:+.4f} m  |  y={self.odom_y:+.4f} m")
            moved = math.sqrt(self.odom_x**2 + self.odom_y**2)
            if moved > 0.02:
                print(f"     {GREEN}🚗 Robot {moved:.3f} m hareket etmiş — odometri çalışıyor!{RESET}")
            else:
                print(f"     {YELLOW}⏸️  Robot henüz hareket etmedi (0.0 m) — normal{RESET}")
        else:
            print(f"  {RED}❌ /odom verisi YOK!{RESET}")
            print(f"     {YELLOW}→ Neden? RF2O lazer odometrisi başlamış mı?{RESET}")
            print(f"     {YELLOW}→ 'ros2 topic list | grep odom' komutunu kontrol edin{RESET}")

        # --- TF: odom → base_footprint
        print(f"\n🌐 TF Ağacı Kontrolleri:")
        tf_checks = [
            ('odom',         'base_footprint'),
            ('map',          'odom'),
            ('base_footprint','lidar_link'),
        ]
        for parent, child in tf_checks:
            try:
                t = self.tf_buffer.lookup_transform(parent, child,
                                                     rclpy.time.Time(),
                                                     timeout=rclpy.duration.Duration(seconds=0.3))
                age = (self.get_clock().now() - t.header.stamp).nanoseconds / 1e9
                if age < 1.0:
                    print(f"  {GREEN}✅ {parent} → {child} — yaş: {age:.2f}s{RESET}")
                else:
                    print(f"  {YELLOW}⚠️  {parent} → {child} — ESKIMIŞ: {age:.1f}s{RESET}")
            except Exception as e:
                errmsg = str(e)[:60]
                if 'map' in parent:
                    print(f"  {YELLOW}⚠️  {parent} → {child} — SLAM başlamadıysa normal{RESET}")
                else:
                    print(f"  {RED}❌ {parent} → {child} BULUNAMADI: {errmsg}{RESET}")

        # --- Sonuç
        print(f"\n{BOLD}{'─'*68}")
        all_ok = scan_fresh and odom_fresh
        if all_ok:
            print(f"{'='*68}")
            print(f"{GREEN}{BOLD}🟢 SİSTEM HAZIR! SLAM başlatabilirsiniz.{RESET}")
            print(f"   ros2 launch ackermann_car_sim slam.launch.py use_sim_time:=false")
        else:
            print(f"{RED}{BOLD}🔴 SORUN VAR — Yukarıdaki hataları giderin, sonra SLAM başlatın!{RESET}")
        print(f"{'='*68}{RESET}\n")


def main():
    rclpy.init()
    node = SlamDiagnosis()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
