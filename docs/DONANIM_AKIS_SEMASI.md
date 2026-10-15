# 🔌 LOGIX AMR — Donanımsal Akış Şeması ve Sistem Mimarisi

Bu doküman, **LOGIX AMR (Ackermann Otonom Mobil Robot)** projesinin fiziksel donanım bileşenlerini, veri sinyal hatlarını, güç dağıtım mimarisini ve kontrol akışını detaylandırmaktadır.

---

## 📐 1. Donanım Akış Şeması (Mermaid Blok Diyagramı)

```mermaid
flowchart TB
    subgraph POWER_SYSTEM["⚡ GÜÇ VE ENERJİ DAĞITIM SİSTEMİ (PDU)"]
        BATTERY["🔋 Ana Batarya Paketi\n(LiPo / LiFePO4 11.1V - 14.8V / 24V)"]
        ESTOP["🛑 Acil Stop Butonu\n(E-Stop Switch & Ana Sigorta 15A)"]
        BUCK_5V["🔌 Buck Converter 1\n(12V/24V -> 5V 5A DC)"]
        BUCK_12V["🔌 Buck Converter 2 / Regülatör\n(12V DC Stabilize)"]
        
        BATTERY --> ESTOP
        ESTOP --> BUCK_5V
        ESTOP --> BUCK_12V
    end

    subgraph COMPUTATION["🧠 ANA İŞLEMCİ VE YAZILIM KATMANI"]
        RASPI["💻 Raspberry Pi 4 / 5\n(Ubuntu 24.04 LTS + ROS 2 Jazzy)"]
        ROS2_NAV["🧩 ROS 2 Navigation2 & SLAM\n(A* Planner, Costmap, AMCL)"]
        ROS2_RF2O["📐 RF2O Laser Odometry Node\n(Odometri Hesabı)"]
        WEB_SERVER["🌐 Web SCADA Sunucusu\n(Python Port 8080)"]

        RASPI --- ROS2_NAV
        RASPI --- ROS2_RF2O
        RASPI --- WEB_SERVER
    end

    subgraph SENSORS["📡 SENSÖR KATMANI (ALGILAMA)"]
        LIDAR["🚨 Hokuyo 2D LiDAR\n(270° FOV, 10Hz, USB/Ethernet)"]
        CAM["📷 Intel RealSense RGB-D Kamera\n(USB 3.0, Alçak Engel Algılama)"]
        ENCODER["🔄 Tekerlek Enkoderleri\n(Çekiş Hızı & Odometri Geri Besleme)"]
    end

    subgraph ACTUATORS["⚙️ ALT SEVİYE SÜRÜCÜ VE AKTÜATÖR KATMANI"]
        MCU["🎛️ Alt Seviye Mikrodenetleyici\n(Arduino / STM32 / ESP32)"]
        MOTOR_DRIVER["⚡ Çekiş Motor Sürücüsü\n(BTS7960 / Cytron DC Sürücü)"]
        TRACTION_MOTOR["🏎️ Çekiş Motoru (Arka Tekerlekler)\n(DC Redüktörlü Motor)"]
        STEER_SERVO["🎯 Direksiyon Servosu (Ön Tekerlekler)\n(High-Torque Ackermann Servo)"]
    end

    subgraph USER_INTERFACE["📱 OPERATÖR VE HAVA İLETİŞİM HATTI"]
        WIFI_ROUTER["📶 Wi-Fi Ağı / Access Point"]
        DASHBOARD["📱 Web SCADA Dashboard / Tablet / PC\n(W/A/S/D Manuel Sürüş & Hedef Gönderimi)"]
    end

    %% GÜÇ HATLARI (Kırmızı Düz Çizgi)
    BUCK_5V ==>|5V 5A DC Power| RASPI
    BUCK_5V ==>|5V DC Power| MCU
    BUCK_5V ==>|5V-6V Servo Power| STEER_SERVO
    BUCK_12V ==>|12V DC Power| LIDAR
    ESTOP ==>|12V-24V High Current Power| MOTOR_DRIVER

    %% VERİ İLETİŞİM HATLARI (Mavi / Yeşil Çizgiler)
    LIDAR -->|USB Seri /dev/ttyACM0 veya Ethernet| RASPI
    CAM -->|USB 3.0 PointCloud| RASPI
    ENCODER -->|AB Fazlı Quadrature Sinyali| MCU
    
    RASPI <==>|USB Seri /dev/ttyUSB0 @ 115200 Baud\nCMD_VEL & Telemetri| MCU
    
    MCU -->|PWM Hız + DIR Yön Sinyali| MOTOR_DRIVER
    MOTOR_DRIVER -->|Motor Güç Sinyali M+/M-| TRACTION_MOTOR
    MCU -->|PWM 50Hz Direksiyon Açısı| STEER_SERVO

    WIFI_ROUTER <==>|Wi-Fi 802.11ac| RASPI
    DASHBOARD <==>|HTTP / WebSockets (Port 8080)| WIFI_ROUTER
```

---

## 🗂️ 2. Donanım Bileşenleri ve Teknik Özellikleri

| Bileşen Grubu | Donanım Modeli | Bağlantı Arayüzü | Çalışma Gerilimi / Güç | Sorumluluğu / Görevi |
| :--- | :--- | :--- | :--- | :--- |
| **Ana İşlemci** | Raspberry Pi 4 / 5 (4GB/8GB) | Type-C USB-PD | 5V DC (3A - 5A) | ROS 2 Jazzy, Nav2, SLAM Toolbox, Web SCADA Sunucusu |
| **LiDAR Sensör** | Hokuyo UTM-30LX / URG Series | USB (`/dev/ttyACM0`) / Ethernet | 12V DC | 270° Lazer tarama (`/scan`), Haritalama ve Engelden Kaçınma |
| **Derinlik Kamerası** | Intel RealSense D435 / D435i | USB 3.0 | 5V DC (USB Powered) | Kör nokta ve alçak engelleri algılama (Pointcloud) |
| **Mikrodenetleyici** | STM32F4 / Arduino Mega | USB Seri (`/dev/ttyUSB0`) | 5V DC | ROS `/cmd_vel` mesajlarını okuma, PWM üretimi, Enkoder okuma |
| **Motor Sürücü** | BTS7960 43A High Power Driver | PWM + DIR Pins | 12V - 24V DC | Arka çekiş DC motorunun yön ve hız kontrolü |
| **Çekiş Motoru** | Redüktörlü DC Motor (Encoderlı) | Motor Çıkış Klemensi | 12V - 24V DC | Robotun ileri/geri hareketini sağlama |
| **Direksiyon Aktüatörü** | High-Torque Dijital Servo (30kg/cm) | PWM (50 Hz / 1-2 ms) | 6V - 7.4V DC | Ackermann mekanizması ile ön tekerleklerin yönlenmesi |
| **Güç Kaynağı** | 3S / 4S LiPo veya LiFePO4 Batarya | XT60 / T-Plug | 11.1V - 14.8V | Tüm robot sisteminin ana enerjisini sağlama |
| **Gerilim Düzenleyici** | Dual DC-DC Step-Down Buck | Terminal Blok | Giriş: 12V-24V / Çıkış: 5V 5A | Pi, MCU ve Sensörler için kararlı 5V DC üretimi |
| **Güvenlik** | Acil Stop (E-Stop) & 15A Sigorta | Seri Bağlantı | 12V - 24V Ana Hat | Tehlike anında tüm motor gücünü fiziksel olarak kesme |

---

## 🔄 3. Veri Akışı ve Kontrol Döngüsü (Control Loop Architecture)

Donanım üzerindeki veri ve kontrol akışı 4 ana döngüde gerçekleşir:

```
[1. Algılama Döngüsü]
Hokuyo LiDAR & RealSense  ---> USB/Serial ---> ROS 2 Drivers (/scan, /camera)

[2. Konumlandırma & Yol Planlama]
/scan ---> rf2o_laser_odometry ---> /odom TF ---> Nav2 Planner/Controller (A* & DWA)

[3. Komut İletimi]
Nav2 Controller ---> /cmd_vel (Linear.x, Angular.z) ---> Serial Node ---> MCU (Arduino/STM32)

[4. Fiziksel Aktüasyon]
MCU PWM Output ---> BTS7960 Driver ---> Rear DC Motor Speed
MCU Servo Pulse ---> Ackermann Steering Servo Angle
```

1. **Algılama (Sensing)**:
   - Hokuyo 2D LiDAR 270° açıda saniyede 10 kez ortam taraması yapar ve `/scan` konusunu besler.
   - Intel RealSense kamera ön tampon üstünden 15° aşağı eğimle alçak engelleri tarar.

2. **Odometri ve Konum Tespiti (Odometry & Localization)**:
   - `rf2o_laser_odometry` düğümü `/scan` verisindeki bağıntılı hareketi hesaplayarak yüksek hassasiyetli `/odom` koordinatını üretir.
   - SLAM Toolbox veya AMCL harita ile odometri arasındaki `map -> odom` TF dönüşümünü günceller.

3. **Yol Planlama ve Karar (Nav2 Planning & Control)**:
   - Global Planner A* algoritması ile en kısa engelsiz rotayı çizer.
   - Local Planner (DWB / TEB) anlık engellerden kaçınmak için hız (`linear.x`) ve dönme açısı (`angular.z`) üretir.

4. **Alt Seviye Aktüasyon (Low-Level Execution)**:
   - Raspberry Pi `/cmd_vel` hız ve açı değerlerini Seri Port (UART 115200 Baud) üzerinden mikrodenetleyiciye (MCU) paketler halinde gönderir.
   - MCU Ackermann kinematiği hesaplayarak:
     - `linear.x` -> DC motor sürücüsüne PWM ve DIR sinyali olarak uygular.
     - `angular.z` -> Direksiyon servolarına PWM darbe genişliği (0.78 rad / 45° limitli) olarak aktarır.

---

## ⚡ 4. Güç Dağıtımı ve Güvenlik Hatları

1. **Güç Katmanlaşması (Isolated Power Domains)**:
   - **Mantık ve İşlemci Gücü (Logic Power)**: DC-DC Buck converter ile 5V 5A seviyesine düşürülür. Raspberry Pi, LiDAR mantık devresi ve MCU bu yoldan beslenir. Motor parazitlerinden etkilenmemesi için filtrelenmiştir.
   - **Güç/Aktüatör Gücü (Power Domain)**: Bataryadan doğrudan E-Stop ve Sigorta üzerinden BTS7960 motor sürücüsüne verilir.

2. **Güvenlik ve Acil Stop (Hardware Interlocks)**:
   - Mantıksal E-Stop: Web SCADA arayüzünden gelen acil durdurma komutu `/cmd_vel`'i anında `(0,0)` yapar.
   - Fiziksel E-Stop: Robot üzerindeki mantar buton basıldığında motor sürücüsünün `12V/24V` ana besleme hattı fiziksel olarak kesilir, Raspberry Pi ve LiDAR çalışmaya devam ederek telemetriyi korur.
