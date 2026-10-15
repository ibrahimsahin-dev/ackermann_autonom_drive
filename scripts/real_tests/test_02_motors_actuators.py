#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
ALT SEVİYE DONANIM TESTİ 2: MOTOR & DİREKSİYON AKTÜATÖR DARBE TESTİ
==============================================================================
Bu araç, robotun motor sürücüsüne ve direksiyon servolarına kontrollü
'/cmd_vel' sinyalleri göndererek dönüş yönlerini ve açı limitlerini test eder.

⚠️  GÜVENLİK UYARISI:
Bu testi yaparken robotun tekerleklerinin YERLE TEMAS ETMEDİĞİNDEN
(robotun güvenli bir takoz / sehpa üzerine alındığından) EMİN OLUN!
==============================================================================
Kullanım:
    python3 test_02_motors_actuators.py
==============================================================================
"""

import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

class ActuatorTester(Node):
    def __init__(self):
        super().__init__('actuator_tester')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.get_logger().info("Motor & Aktüatör Test Node Hazır.")

    def stop_robot(self):
        try:
            if rclpy.ok():
                msg = Twist()
                for _ in range(3):
                    self.pub.publish(msg)
                    time.sleep(0.03)
        except Exception:
            pass

    def send_pulse(self, linear_x: float, angular_z: float, duration: float, desc: str):
        print(f"\n{BOLD}{YELLOW}▶ Komut Gönderiliyor:{RESET} {desc}")
        print(f"  Linear.x = {linear_x:.2f} m/s  |  Angular.z = {angular_z:.2f} rad/s  |  Süre: {duration:.1f} sn")
        
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)

        start = time.time()
        while (time.time() - start) < duration and rclpy.ok():
            self.pub.publish(msg)
            time.sleep(0.08)

        self.stop_robot()
        print(f"{GREEN}✔ Tamamlandı. Motorlar durduruldu.{RESET}")


def print_menu():
    print(f"\n{BOLD}{CYAN}==================================================================")
    print(f"⚙️  ALT SEVİYE TEST 2: MOTOR SÜRÜCÜ & DİREKSİYON AKTÜATÖR TESTİ")
    print(f"=================================================================={RESET}")
    print(f"{RED}⚠️  DİKKAT: Robotun tekerlekleri havada (takoz üzerinde) olmalıdır!{RESET}")
    print(f"------------------------------------------------------------------")
    print(f" [ 1 ]  İleri Dönüş Testi    (0.2 m/s, 2 sn)")
    print(f" [ 2 ]  Geri Dönüş Testi     (-0.2 m/s, 2 sn)")
    print(f" [ 3 ]  Direksiyon SOLA      (Hız=0, Direksiyon Sola Çevrilir, 2.5 sn)")
    print(f" [ 4 ]  Direksiyon SAĞA      (Hız=0, Direksiyon Sağa Çevrilir, 2.5 sn)")
    print(f" [ 5 ]  Direksiyon MERKEZ    (Direksiyon Düz Konuma Alınır)")
    print(f" [ 6 ]  Kombine İleri+Sol    (Dönerek İlerleme Testi, 2.5 sn)")
    print(f" [ 7 ]  Acil Fren (Tüm Sinyalleri Sıfırla)")
    print(f" [ q ]  Çıkış")
    print(f"==================================================================")


def main():
    rclpy.init()
    tester = ActuatorTester()

    try:
        while rclpy.ok():
            print_menu()
            choice = input(f"{BOLD}Lütfen bir test seçin (1-7 / q): {RESET}").strip()

            if choice == '1':
                tester.send_pulse(linear_x=0.2, angular_z=0.0, duration=2.0, desc="İleri Düz Sürüş (Çekiş tekerlekleri ileri dönmeli)")
            elif choice == '2':
                tester.send_pulse(linear_x=-0.2, angular_z=0.0, duration=2.0, desc="Geri Sürüş (Çekiş tekerlekleri geri dönmeli)")
            elif choice == '3':
                tester.send_pulse(linear_x=0.0, angular_z=1.0, duration=2.5, desc="Direksiyon Sola Açılanma (Ön tekerler SOLA bakmalı)")
            elif choice == '4':
                tester.send_pulse(linear_x=0.0, angular_z=-1.0, duration=2.5, desc="Direksiyon Sağa Açılanma (Ön tekerler SAĞA bakmalı)")
            elif choice == '5':
                tester.send_pulse(linear_x=0.0, angular_z=0.0, duration=1.0, desc="Direksiyon Sıfırlama (Ön tekerler TAM DÜZ olmalı)")
            elif choice == '6':
                tester.send_pulse(linear_x=0.2, angular_z=0.8, duration=2.5, desc="Kombine İleri + Sol Dönüş (Gözle Görülür Dönüş)")
            elif choice == '7':
                tester.stop_robot()
                print(f"{GREEN}Fren uygulandı.{RESET}")
            elif choice.lower() == 'q':
                break
            else:
                print(f"{RED}Geçersiz seçim.{RESET}")

    except KeyboardInterrupt:
        pass
    finally:
        tester.stop_robot()
        tester.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        print(f"\n{BOLD}Test sonlandırıldı. Motorlar güvenle kapatıldı.{RESET}")

if __name__ == '__main__':
    main()
