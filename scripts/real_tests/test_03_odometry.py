#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
ALT SEVİYE DONANIM TESTİ 3: ODOMETRİ VE KİNEMATİK KALİBRASYON TESTİ
==============================================================================
Bu araç, robotun '/odom' verisinin fiziksel gerçeklikle uyuşup uyuşmadığını
test eder. Otonom sürüşün başarılı olması için bu testin geçilmesi şarttır!

Test 1 - Doğrusal Mesafe Doğrulaması (1 Metre Testi):
  - Yere 1 metrelik bir cetvel veya bant koyun.
  - Robotu başlangıç çizgisine koyup [Enter]'a basın.
  - Robotu çizgi boyunca tam 1.0 metre ilerletin.
  - [Enter]'a basın -> Odometrinin kaç santim ölçtüğünü ve hata payını görün.

Test 2 - Açısal Dönüş Doğrulaması (360° Tam Tur Testi):
  - Robotun yönünü bir referans çizgisine hizalayın.
  - [Enter]'a basın.
  - Robotu kendi etrafında tam bir tur (360°) döndürüp aynı çizgiye getirin.
  - [Enter]'a basın -> Odometrinin kaç derece döndüğünü hesaplasın.
==============================================================================
Kullanım:
    python3 test_03_odometry.py
==============================================================================
"""

import sys
import math
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def quaternion_to_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class OdometryCalibrator(Node):
    def __init__(self):
        super().__init__('odometry_calibrator')
        self.sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.current_pose = None
        self.last_msg_time = 0.0

    def odom_cb(self, msg: Odometry):
        self.current_pose = msg.pose.pose
        self.last_msg_time = time.time()

    def wait_for_odom(self):
        print(f"⏳ '/odom' verisi bekleniyor...")
        while rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.2)
            if self.current_pose is not None and (time.time() - self.last_msg_time < 2.0):
                print(f"{GREEN}✔ Odometri sinyali aktif!{RESET}\n")
                return True
            time.sleep(0.1)
        return False

def run_linear_test(node: OdometryCalibrator):
    print(f"\n{BOLD}{CYAN}--- [TEST 1: 1 METRE DOĞRUSAL SÜRÜŞ TESTİ] ---{RESET}")
    print("1. Robotu yere koyun ve ön teker hizasına bir başlangıç bandı yapıştırın.")
    print("2. Başlangıç noktasından tam 1.00 metre ileriye ikinci hedef bandı yapıştırın.")
    input(f"{BOLD}Hazır olduğunuzda [ENTER] tuşuna basın...{RESET}")

    rclpy.spin_once(node, timeout_sec=0.2)
    start_x = node.current_pose.position.x
    start_y = node.current_pose.position.y

    print(f"{YELLOW}▶ Başlangıç koordinatı kaydedildi: X={start_x:.3f}, Y={start_y:.3f}{RESET}")
    print("Şimdi robotu (manuel sürerek veya elle iterek) tam 1.0 metre ilerideki banda getirin.")
    input(f"{BOLD}Robot 1.0 metre hedefe vardığında [ENTER] tuşuna basın...{RESET}")

    rclpy.spin_once(node, timeout_sec=0.2)
    end_x = node.current_pose.position.x
    end_y = node.current_pose.position.y

    measured_dist = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)
    expected_dist = 1.0
    error_cm = (measured_dist - expected_dist) * 100.0
    error_percent = ((measured_dist - expected_dist) / expected_dist) * 100.0

    print(f"\n{BOLD}📊 TEST 1 SONUÇLARI:{RESET}")
    print(f"• Fiziksel Gerçek Mesafe : {expected_dist:.3f} m (100.0 cm)")
    print(f"• Odometri Ölçülen Mesafe: {measured_dist:.3f} m ({measured_dist * 100.0:.1f} cm)")
    print(f"• Fark / Sapma           : {error_cm:+.1f} cm (%{error_percent:+.2f})")

    if abs(error_cm) <= 3.0:
        print(f"\n{GREEN}{BOLD}🎉 TEBRİKLER: Odometri son derece hassas! (Hata payı <%3){RESET}")
    elif abs(error_cm) <= 8.0:
        print(f"\n{YELLOW}{BOLD}⚠️  KABUL EDİLEBİLİR: Hata %{abs(error_percent):.1f}. AMCL bu farkı kapatabilir.{RESET}")
    else:
        print(f"\n{RED}{BOLD}❌ HATA YÜKSEK: Tekerlek çapı veya enkoder çarpanınızı kalibre etmeniz gerekir!{RESET}")
        scale_correction = expected_dist / measured_dist
        print(f"💡 Düzeltme Katsayısı: Mevcut tekerlek yarıçapınızı x {scale_correction:.4f} ile çarpın.")

def run_angular_test(node: OdometryCalibrator):
    print(f"\n{BOLD}{CYAN}--- [TEST 2: 360° TAM TUR DÖNÜŞ TESTİ] ---{RESET}")
    print("1. Robotun baktığı yönü yerde bir çizgiyle işaretleyin.")
    input(f"{BOLD}Hazır olduğunuzda [ENTER] tuşuna basın...{RESET}")

    rclpy.spin_once(node, timeout_sec=0.2)
    start_yaw = quaternion_to_yaw(node.current_pose.orientation)

    print(f"{YELLOW}▶ Başlangıç açısı kaydedildi: {math.degrees(start_yaw):.1f}°{RESET}")
    print("Şimdi robotu kendi etrafında tam 1 tur (360°) döndürüp tekrar aynı çizgiye hizalayın.")
    input(f"{BOLD}Robot 360° dönüp aynı yöne baktığında [ENTER] tuşuna basın...{RESET}")

    rclpy.spin_once(node, timeout_sec=0.2)
    end_yaw = quaternion_to_yaw(node.current_pose.orientation)

    diff_yaw = end_yaw - start_yaw
    # normalize between -pi and pi
    diff_yaw = math.atan2(math.sin(diff_yaw), math.cos(diff_yaw))
    diff_deg = math.degrees(diff_yaw)

    print(f"\n{BOLD}📊 TEST 2 SONUÇLARI:{RESET}")
    print(f"• Beklenen Son Açı Farkı : 0.0° (Tam 360° tur tamamlandığında)")
    print(f"• Ölçülen Açı Hatası     : {diff_deg:+.1f}°")

    if abs(diff_deg) <= 5.0:
        print(f"{GREEN}{BOLD}🎉 MÜKEMMEL: Dönüş odometrisi son derece kararlı!{RESET}")
    elif abs(diff_deg) <= 15.0:
        print(f"{YELLOW}{BOLD}⚠️  KABUL EDİLEBİLİR: Açı hatası {abs(diff_deg):.1f}°. SLAM ve AMCL tolere edebilir.{RESET}")
    else:
        print(f"{RED}{BOLD}❌ DÖNÜŞ HATASI YÜKSEK: Teker iz genişliği (wheel_track) veya gyro kalibrasyonunu kontrol edin!{RESET}")

def main():
    rclpy.init()
    node = OdometryCalibrator()

    if not node.wait_for_odom():
        node.destroy_node()
        rclpy.shutdown()
        return

    while rclpy.ok():
        print(f"\n{BOLD}{CYAN}==================================================================")
        print(f"📐 ODOMETRİ KALİBRASYON VE DOĞRULAMA MENÜSÜ")
        print(f"=================================================================={RESET}")
        print(f" [ 1 ]  1 Metre Doğrusal İlerleme Testi")
        print(f" [ 2 ]  360° Tam Tur Dönüş Testi")
        print(f" [ q ]  Çıkış")
        print(f"==================================================================")
        
        choice = input(f"{BOLD}Seçiminiz (1/2/q): {RESET}").strip()
        if choice == '1':
            run_linear_test(node)
        elif choice == '2':
            run_angular_test(node)
        elif choice.lower() == 'q':
            break

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
