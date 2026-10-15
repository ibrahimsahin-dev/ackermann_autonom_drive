# 🔌 LOGIX AMR — Tam Donanım Bağlantı Şeması ve Pin Haritası

Bu doküman; **Raspberry Pi 5, Arduino Mega 2560, L298N Motor Sürücü, MG995 Servo, LM393 Optik Enkoder, MPU6050 IMU Sensörü, LiDAR ve Güç Dağıtım Sisteminin** pin pin, voltaj voltaj eksiksiz bağlantı haritasını içerir.

---

## ⚡ BÖLÜM 1: GÜÇ VE VOLTAJ HATTI (Kritik İlk Aşama)

> ⚠️ **UYARI:** Her şeyden önce **Ortak GND (Toprak)** kuralını uygulayın. Tüm cihazların eksi (-) siyah kabloları tek bir hatta birleşmelidir.

### 1. Batarya Hatları (3S 11.1V LiPo / 18650 Paket):
* Batarya **Kırmızı Kablo (+11.1V)** $\rightarrow$ **L298N `12V (VMS)` Klemensi** ve **Buck Converter `IN+` Girişi**
* Batarya **Siyah Kablo (GND)** $\rightarrow$ **L298N `GND` Klemensi** ve **Buck Converter `IN-` Girişi**

### 2. 5V 5A UBEC / Buck Converter Çıkışı (Temiz 5.1V Güç):
* Buck Converter **`OUT+` (Tam 5.1V Ayarlı Çıkış)**:
  * $\rightarrow$ **Raspberry Pi 5** (Type-C Güç Portu veya GPIO Pin 2)
  * $\rightarrow$ **MG995 Servo Kırmızı Kablo (+5V)** *(Sakın Arduino'ya takmayın!)*
* Buck Converter **`OUT-` (GND Çıkışı)**:
  * $\rightarrow$ **Raspberry Pi 5** GPIO Pin 6 (GND)
  * $\rightarrow$ **MG995 Servo Kahverengi/Siyah Kablo (GND)**
  * $\rightarrow$ **Arduino Mega `GND` Pini** *(Ortak GND Bağlantısı)*

---

## 🧠 BÖLÜM 2: ARDUINO MEGA 2560 PİN BAĞLANTILARI

### 1. L298N Motor Sürücü $\leftrightarrow$ Arduino Mega
*(ÖNEMLİ: L298N `ENA` üzerindeki siyah plastik jumper şapkasını çıkartın!)*

| L298N Sürücü Pini | Arduino Mega Pini | Kablo Voltajı / Görevi |
| :--- | :--- | :--- |
| **`ENA` (Sol Hız)** | **Pin 5** | 5V PWM Sinyali (Sol Motor Hızı: 0-255) |
| **`IN1` (Sol Yön 1)** | **Pin 4** | 5V Dijital Çıkış (Sol Motor Yönü 1) |
| **`IN2` (Sol Yön 2)** | **Pin 7** | 5V Dijital Çıkış (Sol Motor Yönü 2) |
| **`ENB` (Sağ Hız)** | **Pin 6** | 5V PWM Sinyali (Sağ Motor Hızı: 0-255) |
| **`IN3` (Sağ Yön 1)** | **Pin 8** | 5V Dijital Çıkış (Sağ Motor Yönü 1) |
| **`IN4` (Sağ Yön 2)** | **Pin 11** | 5V Dijital Çıkış (Sağ Motor Yönü 2) |
| **`GND`** | **GND Pini** | Mantık Topraklaması |
| **`OUT1` ve `OUT2`** | Sol Arka DC Motor | Sol Motor Güç Kabloları ($M+$ ve $M-$) |
| **`OUT3` ve `OUT4`** | Sağ Arka DC Motor | Sağ Motor Güç Kabloları ($M+$ ve $M-$) |

---

### 2. MG995 Direksiyon Servosu $\leftrightarrow$ Arduino Mega & Güç

| Servo Kablo Rengi | Bağlanacağı Yer & Pin | Voltaj / Sinyal |
| :--- | :--- | :--- |
| **Turuncu / Sarı (Sinyal)** | **Arduino Mega Pin 3** | 5V 50Hz PWM Açı Sinyali (Güncellendi: Pin 3) |
| **Kırmızı (VCC)** | **Buck Converter `OUT+`** | **5V / 2A Yüksek Akım Gücü** *(Arduino'ya takmayın)* |
| **Kahverengi / Siyah** | **Ortak GND Hattı** | Toprak Bağlantısı |

---

### 3. MPU6050 IMU Sensörü $\leftrightarrow$ Arduino Mega

| MPU6050 Sensör Pini | Arduino Mega Pini | Voltaj / Sinyal |
| :--- | :--- | :--- |
| **`VCC`** | **Arduino Mega 5V Pini** | 5V Mantık Beslemesi |
| **`GND`** | **Arduino Mega GND Pini** | Toprak Bağlantısı |
| **`SDA`** | **Arduino Mega Pin 20 (SDA)** | I2C Veri Hattı |
| **`SCL`** | **Arduino Mega Pin 21 (SCL)** | I2C Saat Hattı |

---

### 4. LM393 / HC-020K Optik Enkoder $\leftrightarrow$ Arduino Mega

| Enkoder Sensör Pini | Arduino Mega Pini | Voltaj / Sinyal |
| :--- | :--- | :--- |
| **`VCC`** | **Arduino Mega 5V Pini** | 5V Mantık Beslemesi |
| **`GND`** | **Arduino Mega GND Pini** | Toprak Bağlantısı |
| **`OUT` / `D0`** | **Arduino Mega Pin 2 (INT0)** | 5V Kare Dalga Pal Sinyali (Donanımsal Kesme) |

---

## 💻 BÖLÜM 3: RASPBERRY PI 5 USB İLETİŞİM BAĞLANTILARI

| Raspberry Pi 5 Portu | Bağlanacak Cihaz | Sinyal / Görevi |
| :--- | :--- | :--- |
| **USB Port 1** | **Arduino Mega** (USB Type-B Kablosu) | `/dev/ttyACM0` Seri Port (115200 Baud ROS 2 İletişimi) |
| **USB Port 2** | **2D LiDAR** (USB Kablosu) | `/dev/ttyUSB0` Canlı 270° Lazer Taraması (`/scan`) |
| **USB 3.0 Port 3**| **USB Web Kamera / RealSense** | FPV Canlı Video Akışı |

---

## 📋 MONTAJ SONRASI HIZLI KONTROL LİSTESİ

1. ✅ **GND Kontrolü:** Multimetre ile Arduino GND, Buck Converter OUT-, Servo GND ve L298N GND pinlerinin birbiriyle bağlı (kısa devre) olduğunu teyit edin.
2. ✅ **Voltaj Kontrolü:** Pi 5 ve Servoya giden hattın **tam 5.1 Volt** olduğunu ölçün.
3. ✅ **L298N Jumper:** L298N `ENA` pinindeki siyah plastik jumper'ı çıkardığınızdan ve Arduino Pin 5'i buraya taktığınızdan emin olun.
