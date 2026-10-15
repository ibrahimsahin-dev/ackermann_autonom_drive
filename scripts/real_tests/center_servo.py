#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
LOGIX AMR - DİREKSİYON SERVOSU MERKEZLEME (0 DERECE TUTMA) ARACI
==============================================================================
Bu script servoyu elektriksel 0 derece düz konuma kilitler ve siz kolu (horn)
vidalar iken sabit tutar.
==============================================================================
Kullanım:
    python3 center_servo.py
==============================================================================
"""

import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

def main():
    rclpy.init()
    node = Node('servo_center_tool')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    print("==================================================================")
    print("🎯 DİREKSİYON SERVOSU 0 DERECE MERKEZ KONUMUNA KİLİTLENİYOR")
    print("==================================================================")
    print("Servo şu an 0° merkez açısında tutuluyor.")
    print("Tekerlekleri tam düz konuma getirip servo kolunu (horn) vidalayabilirsiniz.")
    print("İşiniz bittiğinde Ctrl+C ile çıkabilirsiniz.")
    print("==================================================================")

    msg = Twist()
    msg.linear.x = 0.0
    msg.angular.z = 0.0

    try:
        while rclpy.ok():
            pub.publish(msg)
            time.sleep(0.1) # Watchdog'u besleyerek servoyu merkezde kilitli tutar
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        print("\n✅ Merkezleme tamamlandı.")

if __name__ == '__main__':
    main()
