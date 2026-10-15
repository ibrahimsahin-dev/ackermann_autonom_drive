/*
  ==============================================================================
  LOGIX AMR - MG995 DİREKSİYON SERVOSU MERKEZLEME (0 DERECE KALİBRASYON) KODU
  ==============================================================================
  Kullanım Amacı:
  Servoyu elektriksel tam merkezine (90 derece = 0 derece direksiyon) sabitler.
  Servo bu konumda kilitliyken horn (servo kolu) ve rot kolu takılmalıdır.
  
  Bağlantı (Arduino Mega):
  - Sinyal Kablosu (Turuncu/Beyaz) -> Pin 3 (PWM)
  - Güç Kablosu (Kırmızı)           -> Harici 5V UBEC
  - Toprak Kablosu (Kahve/Siyah)   -> Ortak GND
  ==============================================================================
*/

#include <Servo.h>

#define SERVO_PIN 3

Servo steerServo;
int centerAngle = 90; // MG995'in 0 derece direksiyon (tam merkez) açısı

void setup() {
  Serial.begin(115200);
  delay(500);

  steerServo.attach(SERVO_PIN);
  steerServo.write(centerAngle);

  Serial.println("=================================================");
  Serial.println("🎯 MG995 SERVO MERKEZLEME (0 DERECE) AKTİF");
  Serial.println("=================================================");
  Serial.print("Mevcut Servo Açısı: ");
  Serial.print(centerAngle);
  Serial.println(" derece (DİREKSİYON 0 DERECE DÜZ)");
  Serial.println("-------------------------------------------------");
  Serial.println("Şimdi servo enerjili ve kilitliyken:");
  Serial.println("1. Servo kolunu (horn) tekerlekler TAM DÜZ bakacak şekilde vidalayın.");
  Serial.println("2. İnce ayar (trim) gerekirse Seri Monitörden yeni açı (örn. 88 veya 92) yazıp Enter'a basın.");
  Serial.println("=================================================");
}

void loop() {
  // Kullanıcı seri porttan ince ayar girmek isterse (örn: 89, 91 vb.)
  if (Serial.available() > 0) {
    int inputVal = Serial.parseInt();
    if (inputVal >= 50 && inputVal <= 130) {
      centerAngle = inputVal;
      steerServo.write(centerAngle);
      Serial.print("✅ Yeni Merkez Açısı Uygulandı: ");
      Serial.print(centerAngle);
      Serial.println(" derece");
    }
  }
  delay(100);
}
