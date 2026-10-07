# 🚀 LOGIX AMR — Raspberry Pi (Ubuntu 24.04) Gerçek Hayata Geçiş Rehberi

Bu rehber, simülasyon ortamında test edilen ve doğrulanan Ackermann AMR sisteminin **fiziksel Raspberry Pi ve gerçek sensörler** üzerine adım adım aktarılması için hazırlanmıştır.

---

## 📌 1. Ubuntu 24.04 ve ROS 2 Dağıtım Seçimi

Raspberry Pi'nize **Ubuntu 24.04 LTS (Noble Numbat)** kurduğunuz için ROS 2 ekosisteminde iki seçeneğiniz vardır:

### ✅ Seçenek A (En Çok Önerilen — Doğrudan & Yüksek Performanslı): ROS 2 Jazzy Jalisco
Ubuntu 24.04'ün resmi ve en güncel LTS sürümü **ROS 2 Jazzy**'dir (2029'a kadar desteklenir). Geliştirdiğimiz tüm Nav2 parametreleri, A* algoritması, Web Dashboard ve URDF modelleri Jazzy ile **%100 uyumludur**.

Raspberry Pi terminalinde şu komutlarla kurun:
```bash
# 1. Depoları ve anahtarları ekleyin
sudo apt update && sudo apt install -y locales curl gnupg lsb-release
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(source /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 2. ROS 2 Jazzy Base ve Paketleri Yükleyin
sudo apt update
sudo apt install -y ros-jazzy-ros-base \
                    ros-jazzy-navigation2 \
                    ros-jazzy-nav2-bringup \
                    ros-jazzy-slam-toolbox \
                    ros-jazzy-robot-state-publisher \
                    ros-jazzy-joint-state-publisher \
                    ros-jazzy-xacro \
                    ros-jazzy-tf2-ros \
                    ros-jazzy-urg-node \
                    python3-colcon-common-extensions \
                    python3-pip

# 3. rf2o_laser_odometry yükleyin (depoda yoksa src içine derlenir)
sudo apt install -y ros-jazzy-rf2o-laser-odometry || true
```

---

## 🔌 2. Donanım İzinleri & USB Seri Port Yetkilendirmesi

LiDAR ve Motor Sürücü / Mikrodenetleyici (Arduino/STM32) USB üzerinden takıldığında Linux varsayılan olarak normal kullanıcıya okuma/yazma izni vermez.

Pi terminalinde şu komutu çalıştırın:
```bash
# Kullanıcıyı dialout grubuna ekleyin
sudo usermod -a -G dialout $USER

# Değişikliğin aktif olması için oturumu yenileyin veya yeniden başlatın:
sudo reboot
```

USB portlarını kontrol etmek için:
```bash
ls -la /dev/ttyACM* /dev/ttyUSB*
```
*(Genellikle Hokuyo LiDAR `/dev/ttyACM0`, motor sürücüsü `/dev/ttyUSB0` olarak görünür).*

---

## 🧪 3. Alt Seviye Donanım & Sinyal Testleri (Sırayla Yapılacak)

Nav2 otonom sürüşü çalıştırmadan önce donanımın tek tek doğru sinyal ürettiğinden emin olmalıyız. Projenizde `scripts/real_tests/` klasöründe hazır test araçları oluşturulmuştur:

```bash
cd ~/Desktop/Navigation
```

### 📡 Test 1: Hokuyo LiDAR Sinyal & 270° Açı Testi
LiDAR'ı USB'ye takın, sürücüsünü başlatın ve ardından test aracını çalıştırın:
```bash
python3 scripts/real_tests/test_01_lidar.py
```
- **Neleri Göreceksiniz?**
  - Frekans (10 Hz civarı olmalı),
  - Açı kapsamı (270° - min -135° ile max +135°),
  - Ön, sol ve sağdaki engele olan anlık metre cinsinden mesafe.
- **Doğrulama:** Elinizi LiDAR'ın önüne koyduğunuzda `ÖN` mesafesinin santim santim düştüğünü teyit edin.

---

### ⚙️ Test 2: Motor Sürücü & Direksiyon Darbe Testi
> ⚠️ **ÖNEMLİ:** Robotun tekerlekleri yere basmamalı, robot bir takoz/kutu üzerinde olmalıdır!

```bash
python3 scripts/real_tests/test_02_motors_actuators.py
```
- Menüden `1` tuşuna basarak 2 saniyelik ileri sürüş darbesi verin -> Çekiş motorunun ileri döndüğünü görün.
- Menüden `3` ve `4` tuşlarına basarak direksiyon servolarının tam sola ve tam sağa doğru açılarda döndüğünü teyit edin.
- `5` ile direksiyonun tam merkeze sıfırlandığını doğrulayın.

---

### 📐 Test 3: Odometri Doğruluk & Kalibrasyon Testi
Robotu yere indirin ve çalıştırın:
```bash
python3 scripts/real_tests/test_03_odometry.py
```
- **1 Metre Testi:** Yere 1 metrelik bant çekin. Robotu başlangıçta onaylayın, tam 1.0 metre ilerletip tekrar onaylayın.
  - Ölçülen değer 97-103 cm arasındaysa odometri mükemmeldir.
  - Değer çok farklıysa script size düzeltme katsayısını söyleyecektir.
- **360° Dönüş Testi:** Robotu tam bir tur döndürün; açı hatasının <10° olduğunu doğrulayın.

---

### 🔗 Test 4: TF Koordinat Ağacı Denetimi
```bash
python3 scripts/real_tests/test_04_tf_tree.py
```
- `odom -> base_footprint -> base_link -> lidar_link` zincirindeki 4 ana bağın yeşil `✔ AKTİF` olduğunu doğrulayın.

---

## 🗺️ 4. Gerçek Ortamı Tarama (SLAM ile Harita Çıkarma)

Donanım testleri tamamlandıktan sonra fabrikanızı/ofisinizi taramak için tek komut yeterlidir:

```bash
./start_real_robot.sh slam
```

1. Telefonunuzdan veya bilgisayarınızdan `http://<RASPI_IP>:8080` adresine gidin.
2. Web arayüzündeki klavye sürüşü (W/A/S/D) ile robotu ortamda yavaşça gezdirin.
3. Duvarlar ve koridorlar ekranda netleştikten sonra haritayı kaydedin:
   ```bash
   ./save_map.sh
   ```
   *(Harita otomatik olarak `src/ackermann_car_sim/maps/arena_map.yaml` konumuna kaydedilecektir).*

---

## 🎯 5. Tam Otonom Navigasyon

Harita bir kez kaydedildikten sonra artık haritalamaya gerek yoktur. Günlük otonom sevkiyat için:

```bash
./start_real_robot.sh
```

- Web arayüzünden hedef noktaya tıklayın veya sol paneldeki istasyon butonuna basın.
- Robot gerçek ortamda A* algoritması ve engellerden kaçınma güvenliği ile otonom sevk edilecektir!
