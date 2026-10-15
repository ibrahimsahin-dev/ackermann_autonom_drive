/*
  ==============================================================================
  LOGIX AMR - ARDUINO MEGA FIRMWARE  v3  (İSTEK-CEVAP TELEMETRİ)
  ==============================================================================
  Protokol:
   Pi → Arduino  :  "CMD,<linear_x>,<steer_deg>\n"
   Pi → Arduino  :  "TELEM_REQ\n"   → Arduino "TELEM,<pulses>\n" döner
   Pi → Arduino  :  "RESET_ENC\n"   → Enkoder sıfırla, "TELEM,0" döner

  Donanım:
   - Sol Motor : ENA=5 PWM, IN1=4, IN2=7
   - Sağ Motor : ENB=6 PWM, IN3=8, IN4=11
   - Servo     : Pin 3
   - Enkoder   : Pin 2 (INT0, RISING)
   - nRF24L01  : CE=48, CSN=49  (opsiyonel — yoksa devre dışı bırakılır)
  ==============================================================================
*/

#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>
#include <Servo.h>

// ── Pin Tanımları ─────────────────────────────────────────────────────────────
#define ENA_PIN     5
#define IN1_PIN     4
#define IN2_PIN     7
#define ENB_PIN     6
#define IN3_PIN     8
#define IN4_PIN     11
#define SERVO_PIN   3
#define NRF_CE_PIN  48
#define NRF_CSN_PIN 49
#define ENCODER_PIN 2

// ── Nesneler ──────────────────────────────────────────────────────────────────
RF24 alici(NRF_CE_PIN, NRF_CSN_PIN);
const uint64_t nrf_kanal = 1111;
bool nrf_ok = false;       // nRF24 başarıyla başladı mı?

Servo steerServo;
volatile long encoder_pulses = 0;
unsigned long last_cmd_time  = 0;

// ── Enkoder ISR ───────────────────────────────────────────────────────────────
void encoderISR() {
  encoder_pulses++;
}

// ── Motorları Durdur ──────────────────────────────────────────────────────────
void stopMotors() {
  analogWrite(ENA_PIN, 0);
  analogWrite(ENB_PIN, 0);
  digitalWrite(IN1_PIN, LOW); digitalWrite(IN2_PIN, LOW);
  digitalWrite(IN3_PIN, LOW); digitalWrite(IN4_PIN, LOW);
}

// ── Araç Kontrolü ─────────────────────────────────────────────────────────────
void applyVehicleControl(float linear_x, float steer_deg) {
  // Servo
  int servo_angle = constrain(90 + (int)steer_deg, 65, 115);
  steerServo.write(servo_angle);

  // PWM
  float speed_mag = abs(linear_x);
  int pwm_val = constrain((int)(speed_mag * 500.0), 0, 255);
  if (speed_mag >= 0.02 && pwm_val < 65) pwm_val = 65;
  if (speed_mag < 0.02) pwm_val = 0;

  // Yön
  if (linear_x > 0) {
    digitalWrite(IN1_PIN, HIGH); digitalWrite(IN2_PIN, LOW);
    digitalWrite(IN3_PIN, HIGH); digitalWrite(IN4_PIN, LOW);
  } else if (linear_x < 0) {
    digitalWrite(IN1_PIN, LOW);  digitalWrite(IN2_PIN, HIGH);
    digitalWrite(IN3_PIN, LOW);  digitalWrite(IN4_PIN, HIGH);
  } else {
    stopMotors();
  }

  analogWrite(ENA_PIN, pwm_val);
  analogWrite(ENB_PIN, pwm_val);

  last_cmd_time = millis();
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // Seri port açılana kadar bekle (Serial Monitor bağlanabilsin)
  // Maksimum 3 saniye bekle, sonra devam et (headless çalışmada takılmasın)
  unsigned long t0 = millis();
  while (!Serial && (millis() - t0) < 3000) { ; }

  Serial.println(F("================================================="));
  Serial.println(F("LOGIX AMR - ARDUINO MEGA FIRMWARE v3"));
  Serial.println(F("================================================="));

  // Motor pinleri
  pinMode(ENA_PIN, OUTPUT); pinMode(IN1_PIN, OUTPUT); pinMode(IN2_PIN, OUTPUT);
  pinMode(ENB_PIN, OUTPUT); pinMode(IN3_PIN, OUTPUT); pinMode(IN4_PIN, OUTPUT);
  stopMotors();
  Serial.println(F("[OK] Motor pinleri ayarlandi. Motorlar durduruldu."));

  // Servo
  steerServo.attach(SERVO_PIN);
  steerServo.write(90);
  Serial.println(F("[OK] Servo baslangic pozisyonuna alindi (90 derece)."));

  // Enkoder
  pinMode(ENCODER_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_PIN), encoderISR, RISING);
  Serial.println(F("[OK] Enkoder kesme (Pin 2, INT0) basladi."));

  // nRF24L01 — başarısız olursa devre dışı bırak
  Serial.println(F("[..] nRF24L01 baslatiliyor..."));
  if (alici.begin()) {
    alici.openReadingPipe(1, nrf_kanal);
    alici.setPALevel(RF24_PA_LOW);
    alici.setDataRate(RF24_250KBPS);
    alici.setChannel(76);
    alici.startListening();
    nrf_ok = true;
    Serial.println(F("[OK] nRF24L01 HAZIR. Kablosuz kumanda aktif."));
  } else {
    nrf_ok = false;
    Serial.println(F("[WARN] nRF24L01 BULUNAMADI veya bagli degil!"));
    Serial.println(F("       Kablosuz kumanda devre disi - sadece seri CMD kullanilacak."));
  }

  last_cmd_time = millis();

  Serial.println(F("================================================="));
  Serial.println(F("READY - Komut bekleniyor..."));
  Serial.println(F("  CMD,<v>,<aci>   -> Motor+Servo kontrolu"));
  Serial.println(F("  TELEM_REQ       -> Enkoder degeri al"));
  Serial.println(F("  RESET_ENC       -> Enkoder sifirla"));
  Serial.println(F("================================================="));
}

// ── Ana Döngü ─────────────────────────────────────────────────────────────────
void loop() {

  // ─────────────────────────────────────────────────────────────────────────
  // 1. nRF24L01 KABLOSUZ KUMANDA (yalnızca modül başarıyla başladıysa)
  // ─────────────────────────────────────────────────────────────────────────
  if (nrf_ok && alici.available()) {
    int nrf_mesaj = 0;
    alici.read(&nrf_mesaj, sizeof(nrf_mesaj));

    // Geçersiz değerleri filtrele (0-5 dışında her şeyi yoksay)
    switch (nrf_mesaj) {
      case 1: applyVehicleControl( 0.35,  0.0); break; // w → İleri
      case 2: applyVehicleControl(-0.35,  0.0); break; // s → Geri
      case 3: applyVehicleControl( 0.25, 25.0); break; // d → Sağ
      case 4: applyVehicleControl( 0.25,-25.0); break; // a → Sol
      case 5: applyVehicleControl( 0.0,   0.0); break; // x → Dur
      default:
        // Bilinmeyen mesaj — yoksay, motor kontrolüne dokunma
        break;
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 2. SERİ PORT (Pi) — CMD / TELEM_REQ / RESET_ENC
  // ─────────────────────────────────────────────────────────────────────────
  if (Serial.available() > 0) {
    String inputStr = Serial.readStringUntil('\n');
    inputStr.trim();

    if (inputStr.length() == 0) {
      // Boş satır — yoksay
    }
    // ── Motor komutu
    else if (inputStr.startsWith("CMD,")) {
      int c1 = inputStr.indexOf(',');
      int c2 = inputStr.indexOf(',', c1 + 1);
      if (c1 != -1 && c2 != -1) {
        float linear_x  = inputStr.substring(c1 + 1, c2).toFloat();
        float steer_deg  = inputStr.substring(c2 + 1).toFloat();
        applyVehicleControl(linear_x, steer_deg);
      }
    }
    // ── Telemetri isteği
    else if (inputStr.startsWith("TELEM_REQ")) {
      noInterrupts();
      long snap = encoder_pulses;
      interrupts();
      Serial.print(F("TELEM,"));
      Serial.println(snap);
    }
    // ── Enkoder sıfırla
    else if (inputStr.startsWith("RESET_ENC")) {
      noInterrupts();
      encoder_pulses = 0;
      interrupts();
      Serial.println(F("TELEM,0"));
    }
    // ── Bilinmeyen komut
    else {
      Serial.print(F("[WARN] Bilinmeyen komut: "));
      Serial.println(inputStr);
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 3. GÜVENLİK WATCHDOG — 600ms komut gelmezse motorları durdur
  // ─────────────────────────────────────────────────────────────────────────
  if (millis() - last_cmd_time > 600) {
    stopMotors();
  }
}
