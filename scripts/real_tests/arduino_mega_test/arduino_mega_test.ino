/*
  ==============================================================================
  LOGIX AMR - ARDUINO MEGA TÜM DONANIMLAR BİRİM TEST KODU
  ==============================================================================
  Test Edilen Donanımlar:
   1. L298N Motor Sürücü ve Arka Çekiş Motoru (Pin 5 PWM, Pin 4 IN1, Pin 7 IN2)
   2. MG995 Direksiyon Servosu (Pin 9 PWM)
   3. LM393 Optik Enkoder (Pin 2 INT0)
   4. MPU6050 IMU Sensörü (Pin 20 SDA, Pin 21 SCL)
  ==============================================================================
*/

#include <Servo.h>
#include <Wire.h>

// 1. Pin Tanımlamaları
#define ENA_PIN 5   // Sol Motor Hız PWM
#define IN1_PIN 4   // Sol Motor Yön 1
#define IN2_PIN 7   // Sol Motor Yön 2

#define ENB_PIN 6   // Sağ Motor Hız PWM
#define IN3_PIN 8   // Sağ Motor Yön 1
#define IN4_PIN 11  // Sağ Motor Yön 2 (Güncellendi: Pin 11)

#define SERVO_PIN 3 // MG995 Servo Pin (Güncellendi: Pin 3)

#define MPU6050_ADDR 0x68 // MPU6050 I2C Adresi

Servo steerServo;
volatile long encoder_pulses = 0;

// Enkoder Kesme Fonksiyonu
void encoderISR() {
  encoder_pulses++;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; } // Seri port hazır olana kadar bekle
  
  Serial.println("=================================================");
  Serial.println("🚀 LOGIX AMR - ARDUINO MEGA DONANIM TESTİ BAŞLADI");
  Serial.println("=================================================");

  // L298N Sol ve Sağ Motor Pin Ayarları
  pinMode(ENA_PIN, OUTPUT);
  pinMode(IN1_PIN, OUTPUT);
  pinMode(IN2_PIN, OUTPUT);

  pinMode(ENB_PIN, OUTPUT);
  pinMode(IN3_PIN, OUTPUT);
  pinMode(IN4_PIN, OUTPUT);

  // Servo Ayarı
  steerServo.attach(SERVO_PIN);
  steerServo.write(90); // Direksiyonu Merkeze Al

  // Enkoder Kesme Ayarı (Pin 2 INT0)
  pinMode(2, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(2), encoderISR, RISING);

  // MPU6050 I2C Başlatma
  Wire.begin();
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // Power Management Register
  Wire.write(0);    // MPU6050'yi Uykudan Uyandır
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.println("✅ MPU6050 IMU Sensörü BAŞARIYLA Bulundu!");
  } else {
    Serial.println("❌ HATA: MPU6050 Bulunamadı! (Pin 20 SDA, Pin 21 SCL Kontrol Edin)");
  }

  delay(1000);
}

void loop() {
  Serial.println("\n-------------------------------------------------");
  
  // -------------------------------------------------------------
  // TEST 1: DİREKSİYON SERVOSU TESTİ
  // -------------------------------------------------------------
  Serial.println("1️⃣ TEST: Direksiyon SOLA Dönüyor (60 derece)...");
  steerServo.write(60);
  delay(1500);

  Serial.println("1️⃣ TEST: Direksiyon SAĞA Dönüyor (120 derece)...");
  steerServo.write(120);
  delay(1500);

  Serial.println("1️⃣ TEST: Direksiyon MERKEZE Alındı (90 derece)...");
  steerServo.write(90);
  delay(1000);

  // -------------------------------------------------------------
  // TEST 2: L298N VE ÇİFT MOTOR İLERİ / GERİ SÜRÜŞ TESTİ
  // -------------------------------------------------------------
  Serial.println("2️⃣ TEST: Çift Motor İLERİ Dönüyor (PWM 180, 2 Saniye)...");
  // Sol Motor İleri
  digitalWrite(IN1_PIN, HIGH);
  digitalWrite(IN2_PIN, LOW);
  analogWrite(ENA_PIN, 180);
  // Sağ Motor İleri
  digitalWrite(IN3_PIN, HIGH);
  digitalWrite(IN4_PIN, LOW);
  analogWrite(ENB_PIN, 180);
  delay(2000);

  Serial.println("🛑 Motorlar Durduruldu.");
  analogWrite(ENA_PIN, 0);
  analogWrite(ENB_PIN, 0);
  delay(1000);

  Serial.println("2️⃣ TEST: Çift Motor GERİ Dönüyor (PWM 180, 2 Saniye)...");
  // Sol Motor Geri
  digitalWrite(IN1_PIN, LOW);
  digitalWrite(IN2_PIN, HIGH);
  analogWrite(ENA_PIN, 180);
  // Sağ Motor Geri
  digitalWrite(IN3_PIN, LOW);
  digitalWrite(IN4_PIN, HIGH);
  analogWrite(ENB_PIN, 180);
  delay(2000);

  Serial.println("🛑 Motorlar Durduruldu.");
  analogWrite(ENA_PIN, 0);
  analogWrite(ENB_PIN, 0);
  delay(1000);

  // -------------------------------------------------------------
  // TEST 3 & 4: ENKODER VE MPU6050 OKUMA TESTİ
  // -------------------------------------------------------------
  Serial.print("3️⃣ TEST: Okunan Enkoder Pal Sayısı: ");
  Serial.println(encoder_pulses);

  // MPU6050 İvme Verisi Okuma
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B); // Accel X, Y, Z Register başlangıcı
  Wire.endTransmission(false);
  Wire.requestFrom(MPU6050_ADDR, 6, true);

  if (Wire.available() == 6) {
    int16_t AccX = Wire.read() << 8 | Wire.read();
    int16_t AccY = Wire.read() << 8 | Wire.read();
    int16_t AccZ = Wire.read() << 8 | Wire.read();
    Serial.print("4️⃣ TEST: MPU6050 Ham İvme (X, Y, Z): ");
    Serial.print(AccX); Serial.print(" | ");
    Serial.print(AccY); Serial.print(" | ");
    Serial.println(AccZ);
  }

  Serial.println("-------------------------------------------------");
  Serial.println("⏳ 3 Saniye Sonra Test Tekrarlanacak...\n");
  delay(3000);
}
