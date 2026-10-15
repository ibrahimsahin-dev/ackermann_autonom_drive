#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
LOGIX AMR - ARDUINO MEGA ROS 2 SERIAL BRIDGE NODE
==============================================================================
Bu düğüm Raspberry Pi 5 üzerinde çalışarak:
 1. ROS 2 '/cmd_vel' (geometry_msgs/Twist) konusunu dinler.
 2. Çizgisel hız (linear.x) ve açısal hızdan (angular.z) Ackermann direksiyon açısını hesaplar.
 3. Seri port (/dev/ttyACM0) üzerinden Arduino Mega'ya "CMD,v,angle\n" komutu gönderir.
 4. Arduino Mega'dan gelen enkoder telemetrisini okur.
==============================================================================
"""

import os
import sys
import math
import time
import serial
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

def is_hokuyo_device(port_path: str) -> bool:
    """Belirtilen seri portun Hokuyo LiDAR'a ait olup olmadığını kontrol eder."""
    by_id_dir = '/dev/serial/by-id'
    if os.path.exists(by_id_dir):
        try:
            real_target = os.path.realpath(port_path)
            for entry in os.listdir(by_id_dir):
                full_path = os.path.join(by_id_dir, entry)
                if os.path.realpath(full_path) == real_target:
                    if any(k in entry.lower() for k in ['hokuyo', 'urg', 'laser']):
                        return True
        except Exception:
            pass
    return False

def find_arduino_ports(preferred_port: str):
    """Arduino Mega'ya ait port adaylarını sıralar, Hokuyo LiDAR portunu eler."""
    by_id_dir = '/dev/serial/by-id'
    candidates = []

    # 1. Öncelik: /dev/serial/by-id/ içinde 'Arduino' veya 'Mega' geçen aygıtlar
    if os.path.exists(by_id_dir):
        for entry in os.listdir(by_id_dir):
            low = entry.lower()
            if any(k in low for k in ['arduino', 'mega', 'ch340', 'ftdi', 'cp210']):
                real_p = os.path.realpath(os.path.join(by_id_dir, entry))
                candidates.append(real_p)

    # 2. Standart portlar (Hokuyo olanlar filtrelenecek, ACM1 öncelikli)
    raw_ports = [
        '/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_95038303031351604231-if00',
        '/dev/ttyACM1',
        preferred_port,
        '/dev/ttyACM0',
        '/dev/ttyUSB0',
        '/dev/ttyUSB1'
    ]
    for p in raw_ports:
        if os.path.exists(p) and not is_hokuyo_device(p):
            candidates.append(p)

    # Yinelenenleri kaldır
    return list(dict.fromkeys(candidates))


class ArduinoMegaBridgeNode(Node):
    def __init__(self):
        super().__init__('arduino_mega_bridge')

        # Parametreler (Arduino Mega için varsayılan /dev/ttyACM1)
        self.declare_parameter('port', '/dev/ttyACM1')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('wheelbase', 0.15) # 15 cm aks mesafesi

        self.port_name = self.get_parameter('port').get_parameter_value().string_value
        self.baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
        self.wheelbase = self.get_parameter('wheelbase').get_parameter_value().double_value

        # Akıllı Seri Port Seçimi (LiDAR ile çakışmayı önler)
        self.ser = None
        ports_to_try = find_arduino_ports(self.port_name)

        self.get_logger().info(f"🔍 Arduino Mega için taranan portlar: {ports_to_try}")

        for p in ports_to_try:
            if is_hokuyo_device(p):
                self.get_logger().warn(f"⏭️ {p} portu HOKUYO LiDAR olarak tespit edildi, atlanıyor...")
                continue
            try:
                self.ser = serial.Serial(p, self.baudrate, timeout=0.1)
                self.port_name = p
                self.get_logger().info(f"✅ Arduino Mega Seri Portuna Bağlanıldı: {p} @ {self.baudrate}")
                break
            except Exception as e:
                self.get_logger().warn(f"Port açılamadı ({p}): {e}")
                continue

        if not self.ser or not self.ser.is_open:
            self.get_logger().error(f"❌ Arduino Mega Seri Portu Açılamadı! Denenen portlar: {ports_to_try}")

        # Son enkoder değeri
        self.last_encoder_pulses = 0

        # Subscriptions
        self.sub_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)

        # Timer: 100ms'de bir TELEM_REQ gönder, yanıtı oku
        self.create_timer(0.1, self.request_telemetry)

    def cmd_vel_callback(self, msg: Twist):
        vx = msg.linear.x
        wz = msg.angular.z

        # Ackermann Steering Angle Calculation (rad to deg)
        steer_deg = 0.0
        if abs(vx) > 0.01:
            # Geri viteste atan2'nin 180 dereceye fırlamaması için abs(vx) kullanılır
            steer_rad = math.atan2(self.wheelbase * wz, abs(vx))
            steer_deg = math.degrees(steer_rad)
        elif abs(wz) > 0.01:
            # Araç dururken veya yerinde direksiyon testi (güvenli açı: +/-20 derece)
            steer_deg = 20.0 if wz > 0 else -20.0

        # Mekanik koruma: direksiyon açısını maks -22 / +22 derece ile sınırla
        steer_deg = max(-22.0, min(22.0, steer_deg))

        cmd_str = f"CMD,{vx:.2f},{steer_deg:.1f}\n"

        if self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd_str.encode('utf-8'))
                if abs(vx) > 0.01 or abs(steer_deg) > 0.5:
                    self.get_logger().info(f"📤 Arduino'ya Gönderildi: v={vx:.2f} m/s | steer={steer_deg:+.1f}° -> {cmd_str.strip()}")
            except Exception as e:
                self.get_logger().error(f"Seri port yazma hatası: {e}")

    def request_telemetry(self):
        """Arduino'ya TELEM_REQ gönderir, gelen TELEM yanıtını okur.
        Firmware artık kendi kendine telemetri GÖNDERMEZ — yalnızca istek üzerine yanıt verir.
        """
        if not self.ser or not self.ser.is_open:
            return
        try:
            # 1. İstek gönder
            self.ser.write(b"TELEM_REQ\n")
            # 2. Yanıtı bekle (timeout=0.1s port'ta zaten ayarlı)
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("TELEM,"):
                parts = line.split(',')
                if len(parts) >= 2:
                    self.last_encoder_pulses = int(parts[1])
                    self.get_logger().debug(
                        f"📥 Enkoder: {self.last_encoder_pulses} pal"
                    )
        except Exception as e:
            self.get_logger().warn(f"Telemetri okuma hatası: {e}")

    def destroy_node(self):
        if self.ser and self.ser.is_open:
            # Stop motors on shutdown
            try:
                self.ser.write(b"CMD,0.00,0.0\n")
                self.ser.close()
            except Exception:
                pass
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = ArduinoMegaBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
