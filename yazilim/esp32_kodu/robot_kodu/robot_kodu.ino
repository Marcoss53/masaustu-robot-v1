/*
 * Masaüstü Robot v1 - ESP32 firmware
 * ----------------------------------
 * PC beyin, ESP32 kas: PC'den USB seri port (921600 baud) üzerinden gelen
 * komutlarla servo (kafa), göz ekranı (ST7789), hoparlör (dahili DAC GPIO25 -> PAM8403 amfi)
 * ve LED çubuğu (WS2812B) yönetilir.
 *
 * Kart: ESP32 Dev Module (30 pin DevKit), ESP32 Arduino core 3.x (2.x de desteklenir)
 * Kütüphaneler: ESP32Servo, Adafruit GFX Library, Adafruit ST7735 and ST7789 Library,
 *               Adafruit NeoPixel
 *
 * ---- SERİ PROTOKOL (her komut bir satır, sonu '\n') ----
 *  PING                     -> "PONG DESKBOT v1"
 *  PAN:<derece>             kafa açısı, -90..+90 (0 = ileri). Yumuşak, hız sınırlı hareket.
 *  PANSPEED:<derece/sn>     en yüksek dönüş hızı (10..300, varsayılan 120)
 *  EYES:<mod>               idle|happy|angry|blink|talk|look_left|look_right|sleep
 *  LOOK:<x>[,<y>]           göz bebeği yönü, -100..100 (x: sol(-)/sağ(+), y: yukarı(-)/aşağı(+))
 *  LED:<r>,<g>,<b>,<parlaklık%>  parlaklık en fazla %20 ile sınırlı (USB güç bütçesi)
 *  VOL:<0..100>             hoparlör ses seviyesi (yazılımsal, varsayılan 60)
 *  BL:<0..100>              ekran arka ışığı
 *  BEEP:<hz>,<ms>           test sesi
 *  AUDIO:<n>:<toplam>       ardından TAM OLARAK n bayt ham PCM gelir (16 kHz, 16 bit, mono, little-endian)
 *                           n çift sayı ve <= 4096 olmalı. <toplam> = baytların toplamı mod 65536.
 *                           Cevap: "A:<boş_tampon_bayt>" (PC bu krediye göre akış kontrolü yapar)
 *                           Hata: "E:AUDIO_SUM" / "E:AUDIO_TIMEOUT" / "E:AUDIO_LEN"
 *  AUDIO_STOP               tampondaki sesi sil, sustur
 *  STATUS                   -> "S:pan=<..>,target=<..>,eyes=<..>,free=<..>,vol=<..>"
 *
 * Bant genişliği: 16000 örnek/sn * 2 bayt = 32 000 B/sn ses.
 * 921600 baud (8N1, 10 bit/bayt) = ~92 160 B/sn -> sesin ~2,9 katı, komutlar için bol pay.
 */

#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Adafruit_NeoPixel.h>
#include <ESP32Servo.h>
#include <freertos/FreeRTOS.h>
#include <freertos/stream_buffer.h>
#include "eye_types.h"

// Ses çıkışı: ESP32 dahili 8 bit DAC (GPIO25 = DAC1) -> PAM8403 L-IN.
// Core 3.x (IDF 5): dac_continuous sürücüsü (DMA). Core 2.x: eski I2S "built-in DAC" modu.
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  #include <driver/dac_continuous.h>
  #define USE_DAC_CONT 1
#else
  #include <driver/i2s.h>
  #define USE_DAC_CONT 0
#endif

// ===================== PINLER (MONTAJ_KILAVUZU.md 5.2 ile birebir) =====================
#define PIN_TFT_SCK   18
#define PIN_TFT_MOSI  23
#define PIN_TFT_CS     5
#define PIN_TFT_DC    16
#define PIN_TFT_RST   17
#define PIN_TFT_BL     4
#define PIN_SERVO     13
#define PIN_AUDIO_DAC 25          // DAC1 (sabit, değiştirilemez) -> PAM8403 L-IN
#define PIN_LED       27
#define LED_COUNT      8

// ===================== AYARLAR =====================
#define SERIAL_BAUD        921600
#define SAMPLE_RATE        16000
#define AUDIO_BUF_BYTES    32768      // ~1 sn ses tamponu
#define AUDIO_CHUNK_MAX    4096
#define AUDIO_TIMEOUT_MS   300        // paket ortasında veri kesilirse vazgeç
// DAC çıkış genliği: 128 ± DAC_SWING (0..127). PAM8403'ün kazancı yüksek (24 dB);
// GPIO25 doğrudan L-IN'e bağlıysa ~0,6 V tepe yeterli -> 48. Araya 10k/2,2k bölücü
// koyarsan (önerilir, daha az cızırtı) 120 yap.
#define DAC_SWING          48
#define LIMIT_THRESH       26000      // yazılımsal limitleyici eşiği (16 bit ölçek)

// Servo: kafa -90..+90 derece -> servo darbe genişliği
#define SERVO_CENTER_US    1500       // kafa ileri bakarken (MONTAJ: 90° = 1500 µs)
#define SERVO_US_PER_DEG   10.0f      // 90 derece = 900 µs -> 600..2400 µs
#define SERVO_INVERT       false      // kafa ters yöne dönüyorsa true yap
#define PAN_LIMIT_DEG      90.0f
#define PAN_TRIM_DEG       0.0f       // kafa tam ortada değilse küçük düzeltme (örn. -3)
#define SERVO_ACCEL        500.0f     // derece/sn^2 (yumuşak kalkış/duruş)
#define SERVO_DETACH_MS    3000       // hedefte bu kadar durunca sinyali kes (titreme/akım azalır)

// Ekran
#define TFT_ROTATION       1          // 1 = yatay 320x240. Görüntü baş aşağıysa 3 yap
#define TFT_INVERT         true       // renkler ters (negatif) görünüyorsa false yap
#define LED_MAX_BRIGHT_PCT 20         // USB güç bütçesi için sınır

// ===================== NESNELER =====================
Adafruit_ST7789 tft(PIN_TFT_CS, PIN_TFT_DC, PIN_TFT_RST);   // donanım SPI (VSPI: SCK18, MOSI23)
Adafruit_NeoPixel strip(LED_COUNT, PIN_LED, NEO_GRB + NEO_KHZ800);
Servo panServo;
#if USE_DAC_CONT
dac_continuous_handle_t dacHandle = nullptr;
#endif
StreamBufferHandle_t audioStream = nullptr;

// ===================== DURUM =====================
volatile int      volumePct     = 60;
volatile uint32_t lastAudioMs   = 0;     // en son gerçek ses çalınan an
volatile int      audioLevel    = 0;     // 0..32767, ağız/göz animasyonu için
volatile bool     audioFlush    = false;

float panTarget = 0, panCurrent = 0, panVel = 0, panMaxSpeed = 120;
bool  servoAttached = false;
uint32_t panSettledMs = 0, lastServoUpdate = 0;

uint32_t lastCmdMs = 0;          // en son komut zamanı (boşta animasyon için)
uint32_t lastLookCmdMs = 0;

// ===================== GÖZ ANİMASYONU =====================
enum EyeMode { EM_IDLE, EM_HAPPY, EM_ANGRY, EM_TALK, EM_SLEEP };
EyeMode eyeMode = EM_IDLE;
const char* eyeModeName(EyeMode m) {
  switch (m) { case EM_HAPPY: return "happy"; case EM_ANGRY: return "angry";
               case EM_TALK: return "talk"; case EM_SLEEP: return "sleep"; default: return "idle"; }
}

#define EYE_CW 150                // her göz için ayrı tuval (canvas) 150x150
#define EYE_CH 150
#define EYE_L_CX 88               // ekran üzerindeki göz merkezleri (320x240)
#define EYE_R_CX 232
#define EYE_CY 120
GFXcanvas16* cvL = nullptr;
GFXcanvas16* cvR = nullptr;

EyeParams eyeCur = {78, 100, 0, 0, 0, 0, 0}, eyeTgt = eyeCur;
float gazeX = 0, gazeY = 0;               // komutla gelen bakış (-1..1)
float blinkPhase = -1;                    // <0: göz kırpma yok; 0..1 kırpma ilerlemesi
uint32_t nextBlinkMs = 0, nextSaccadeMs = 0, lastFrameMs = 0;
bool eyesDirty = true;

static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
  return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3);
}
const uint16_t COL_IDLE  = rgb565(40, 220, 255);
const uint16_t COL_HAPPY = rgb565(80, 255, 140);
const uint16_t COL_ANGRY = rgb565(255, 60, 30);
const uint16_t COL_SLEEP = rgb565(30, 90, 120);

// Tek bir gözü tuvale çiz. mirror: sağ göz için açılı kesimleri aynala
void drawEye(GFXcanvas16* cv, const EyeParams& p, float blink, bool mirror) {
  cv->fillScreen(0);
  float h = p.h * (1.0f - blink);                       // göz kırpınca yükseklik azalır
  if (h < 6) h = 6;
  int w = (int)p.w;
  int cx = EYE_CW / 2 + (int)p.gx;
  int cy = EYE_CH / 2 + (int)p.gy;
  int x = cx - w / 2, y = cy - (int)h / 2;
  int r = min(w, (int)h) / 4; if (r < 2) r = 2;
  cv->fillRoundRect(x, y, w, (int)h, r, p.color);

  // Mutlu: alttan siyah bir daire ile "^" kemer şekli
  if (p.happy > 0.05f) {
    int cr = (int)(w * 0.75f);
    int cyc = y + (int)h + cr - (int)(h * 0.55f * p.happy);
    cv->fillCircle(cx, cyc, cr, 0);
  }
  // Kızgın: iç üst köşeden çapraz kesim (kaşlar çatık)
  if (p.angry > 0.05f) {
    int drop = (int)(h * 0.5f * p.angry);
    if (!mirror) cv->fillTriangle(x - 2, y - 2, x + w + 2, y - 2, x + w + 2, y + drop, 0);   // sol göz: iç taraf sağda
    else         cv->fillTriangle(x - 2, y - 2, x + w + 2, y - 2, x - 2, y + drop, 0);       // sağ göz: iç taraf solda
  }
}

void renderEyes() {
  if (!cvL || !cvR) return;
  float blink = 0;
  if (blinkPhase >= 0) blink = (blinkPhase < 0.5f) ? blinkPhase * 2 : (1 - blinkPhase) * 2;  // kapan-aç
  drawEye(cvL, eyeCur, blink, false);
  drawEye(cvR, eyeCur, blink, true);
  tft.drawRGBBitmap(EYE_L_CX - EYE_CW / 2, EYE_CY - EYE_CH / 2, cvL->getBuffer(), EYE_CW, EYE_CH);
  tft.drawRGBBitmap(EYE_R_CX - EYE_CW / 2, EYE_CY - EYE_CH / 2, cvR->getBuffer(), EYE_CW, EYE_CH);
}

void startBlink() { if (blinkPhase < 0) blinkPhase = 0; }

void setEyeMode(const String& m) {
  if      (m == "idle")       { eyeMode = EM_IDLE; }
  else if (m == "happy")      { eyeMode = EM_HAPPY; }
  else if (m == "angry")      { eyeMode = EM_ANGRY; }
  else if (m == "talk")       { eyeMode = EM_TALK; }
  else if (m == "sleep")      { eyeMode = EM_SLEEP; }
  else if (m == "blink")      { startBlink(); }
  else if (m == "look_left")  { gazeX = -1; gazeY = 0; lastLookCmdMs = millis(); }
  else if (m == "look_right") { gazeX =  1; gazeY = 0; lastLookCmdMs = millis(); }
  else { Serial.println("E:EYES_MODE"); return; }
  eyesDirty = true;
}

// Moda göre hedef göz parametrelerini hesapla, mevcut değerleri yumuşakça yaklaştır
void updateEyes(uint32_t now) {
  bool talking = (now - lastAudioMs) < 150;
  EyeMode m = eyeMode;
  if (talking && m != EM_ANGRY && m != EM_HAPPY) m = EM_TALK;   // ses çalarken otomatik konuşma gözü

  eyeTgt.w = 78; eyeTgt.h = 100; eyeTgt.happy = 0; eyeTgt.angry = 0; eyeTgt.color = COL_IDLE;
  switch (m) {
    case EM_HAPPY: eyeTgt.happy = 1; eyeTgt.color = COL_HAPPY; break;
    case EM_ANGRY: eyeTgt.angry = 1; eyeTgt.h = 90; eyeTgt.color = COL_ANGRY; break;
    case EM_TALK: {
      float lv = min(1.0f, audioLevel / 9000.0f);       // sesin şiddetiyle göz zıplar
      eyeTgt.h = 82 + 26 * lv; eyeTgt.w = 82 - 6 * lv;
      break; }
    case EM_SLEEP: eyeTgt.h = 8; eyeTgt.w = 84; eyeTgt.color = COL_SLEEP; break;
    default: break;
  }

  // Boşta: komut gelmiyorsa rastgele göz kırpma ve küçük bakış kaymaları
  if (m != EM_SLEEP) {
    if (now > nextBlinkMs) { startBlink(); nextBlinkMs = now + random(2000, 6000); }
    if (now - lastLookCmdMs > 4000 && now > nextSaccadeMs) {
      gazeX = random(-60, 61) / 100.0f; gazeY = random(-30, 31) / 100.0f;
      nextSaccadeMs = now + random(1500, 4500);
    }
  }
  eyeTgt.gx = gazeX * 28; eyeTgt.gy = gazeY * 18;

  // Yumuşak geçiş (üstel yaklaşım)
  const float k = 0.35f;
  float before = eyeCur.w + eyeCur.h + eyeCur.gx + eyeCur.gy + eyeCur.happy + eyeCur.angry;
  eyeCur.w += (eyeTgt.w - eyeCur.w) * k;
  eyeCur.h += (eyeTgt.h - eyeCur.h) * k;
  eyeCur.gx += (eyeTgt.gx - eyeCur.gx) * k;
  eyeCur.gy += (eyeTgt.gy - eyeCur.gy) * k;
  eyeCur.happy += (eyeTgt.happy - eyeCur.happy) * k;
  eyeCur.angry += (eyeTgt.angry - eyeCur.angry) * k;
  float after = eyeCur.w + eyeCur.h + eyeCur.gx + eyeCur.gy + eyeCur.happy + eyeCur.angry;
  if (eyeCur.color != eyeTgt.color) { eyeCur.color = eyeTgt.color; eyesDirty = true; }
  if (fabsf(after - before) > 0.05f) eyesDirty = true;

  if (blinkPhase >= 0) { blinkPhase += 0.16f; eyesDirty = true; if (blinkPhase >= 1) blinkPhase = -1; }
}

// ===================== SERVO =====================
void servoWriteDeg(float deg) {
  float d = deg + PAN_TRIM_DEG;
  if (SERVO_INVERT) d = -d;
  int us = (int)(SERVO_CENTER_US + d * SERVO_US_PER_DEG);
  us = constrain(us, 500, 2500);
  if (!servoAttached) { panServo.attach(PIN_SERVO, 500, 2500); servoAttached = true; }
  panServo.writeMicroseconds(us);
}

void updateServo(uint32_t now) {
  if (now - lastServoUpdate < 20) return;                 // 50 Hz
  float dt = (now - lastServoUpdate) / 1000.0f;
  lastServoUpdate = now;
  if (dt > 0.1f) dt = 0.1f;

  float err = panTarget - panCurrent;
  if (fabsf(err) < 0.3f && fabsf(panVel) < 5) {
    panVel = 0;
    if (panCurrent != panTarget) { panCurrent = panTarget; servoWriteDeg(panCurrent); }
    if (servoAttached && now - panSettledMs > SERVO_DETACH_MS) { panServo.detach(); servoAttached = false; }
    return;
  }
  panSettledMs = now;
  // Hız ve ivme sınırlı hareket (durma mesafesine göre yavaşla)
  float stopDist = panVel * panVel / (2 * SERVO_ACCEL);
  float dir = (err > 0) ? 1 : -1;
  float desired;
  if (fabsf(err) <= stopDist + 0.5f) desired = dir * sqrtf(2 * SERVO_ACCEL * fabsf(err));
  else desired = dir * panMaxSpeed;
  desired = constrain(desired, -panMaxSpeed, panMaxSpeed);
  float dv = desired - panVel, maxDv = SERVO_ACCEL * dt;
  panVel += constrain(dv, -maxDv, maxDv);
  float step = panVel * dt;
  if (fabsf(step) > fabsf(err)) step = err;
  panCurrent += step;
  servoWriteDeg(panCurrent);
}

// ===================== LED =====================
void setLed(int r, int g, int b, int brPct) {
  brPct = constrain(brPct, 0, LED_MAX_BRIGHT_PCT);
  strip.setBrightness((uint8_t)(brPct * 255 / 100));
  for (int i = 0; i < LED_COUNT; i++) strip.setPixelColor(i, strip.Color(constrain(r,0,255), constrain(g,0,255), constrain(b,0,255)));
  strip.show();
}

// ===================== SES (dahili DAC) =====================
void dacSetup() {
#if USE_DAC_CONT
  dac_continuous_config_t cfg = {};
  cfg.chan_mask = DAC_CHANNEL_MASK_CH0;          // CH0 = GPIO25
  cfg.desc_num  = 6;
  cfg.buf_size  = 512;
  cfg.freq_hz   = SAMPLE_RATE;
  cfg.offset    = 0;
  cfg.clk_src   = DAC_DIGI_CLK_SRC_APLL;          // 16 kHz için APLL (varsayılan saat ~20 kHz altına inemez)
  cfg.chan_mode = DAC_CHANNEL_MODE_SIMUL;
  if (dac_continuous_new_channels(&cfg, &dacHandle) != ESP_OK || dac_continuous_enable(dacHandle) != ESP_OK) {
    Serial.println("E:DAC_INIT"); dacHandle = nullptr;
  }
#else
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_DAC_BUILT_IN);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_MSB;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = 256;
  cfg.tx_desc_auto_clear = true;
  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, NULL);
  i2s_set_dac_mode(I2S_DAC_CHANNEL_RIGHT_EN);     // sağ kanal = GPIO25
#endif
}

// 8 bit işaretsiz örnekleri DAC'a yaz (128 = sessizlik)
void dacWrite(const uint8_t* data, size_t n) {
#if USE_DAC_CONT
  if (!dacHandle) { vTaskDelay(pdMS_TO_TICKS(n * 1000 / SAMPLE_RATE + 1)); return; }
  size_t loaded = 0;
  dac_continuous_write(dacHandle, (uint8_t*)data, n, &loaded, -1);
#else
  static uint16_t fr[2 * 256];                    // stereo çerçeve, DAC üst 8 biti kullanır
  size_t done = 0;
  while (done < n) {
    size_t k = min(n - done, (size_t)256);
    for (size_t i = 0; i < k; i++) { uint16_t v = (uint16_t)data[done + i] << 8; fr[2 * i] = v; fr[2 * i + 1] = v; }
    size_t w; i2s_write(I2S_NUM_0, fr, k * 4, &w, portMAX_DELAY);
    done += k;
  }
#endif
}

// Açılışta/kapanışta "pat" sesini önlemek için 0 -> 128 (orta seviye) yumuşak geçiş
void dacRamp(bool up) {
  uint8_t r[256];
  for (int blk = 0; blk < 4; blk++) {
    for (int i = 0; i < 256; i++) { int k = blk * 256 + i; int v = k * 128 / 1024; r[i] = (uint8_t)(up ? v : 128 - v); }
    dacWrite(r, 256);
  }
}

// Ses görevi (çekirdek 0): tampondan oku, ses seviyesi + limitleyici uygula, 8 bit DAC'a yaz.
// Veri yoksa orta seviye (128) yaz: DMA eski sesi tekrar etmez, hoparlör sessiz kalır.
void audioTask(void*) {
  static int16_t buf[256];
  static uint8_t out[256];
  static uint8_t silence[128];
  memset(silence, 128, sizeof(silence));
  float limGain = 1.0f;                           // limitleyici kazancı (aşırı sürüş/kırpma koruması)
  uint32_t lfsr = 0xACE1u;                        // küçük titreşim (dither) için
  dacRamp(true);
  for (;;) {
    if (audioFlush) { xStreamBufferReset(audioStream); audioFlush = false; }
    size_t got = xStreamBufferReceive(audioStream, buf, sizeof(buf), pdMS_TO_TICKS(10));
    if (got >= 2) {
      size_t n = got / 2;           // PC her zaman çift bayt gönderir
      int peak = 0;
      float vol = volumePct / 100.0f;
      for (size_t i = 0; i < n; i++) {
        float s = buf[i] * vol * limGain;
        float a = fabsf(s);
        if (a > LIMIT_THRESH) { limGain *= LIMIT_THRESH / a; s = s * LIMIT_THRESH / a; }   // anında kıs
        else if (limGain < 1.0f) { limGain += 0.00005f; if (limGain > 1.0f) limGain = 1.0f; } // ~1 sn'de geri aç
        if (a > peak) peak = (int)a;
        lfsr ^= lfsr << 13; lfsr ^= lfsr >> 17; lfsr ^= lfsr << 5;
        float d = ((int)(lfsr & 0xFF) - 128) / 256.0f;                // ±0,5 LSB dither
        int v = 128 + (int)lroundf(s * DAC_SWING / 32768.0f + d);
        out[i] = (uint8_t)constrain(v, 128 - DAC_SWING, 128 + DAC_SWING);   // sert sınır
      }
      audioLevel = (audioLevel * 3 + min(peak, 32767)) / 4;
      lastAudioMs = millis();
      dacWrite(out, n);
    } else {
      audioLevel = audioLevel * 3 / 4;
      dacWrite(silence, sizeof(silence));
    }
  }
}

// Kısa test sesi üret (kare dalga yerine yumuşak sinüs)
void beep(int hz, int ms) {
  hz = constrain(hz, 100, 8000); ms = constrain(ms, 10, 3000);
  int total = SAMPLE_RATE * ms / 1000;
  int16_t blk[128];
  int idx = 0;
  while (idx < total) {
    int n = min(128, total - idx);
    for (int i = 0; i < n; i++) blk[i] = (int16_t)(9000 * sinf(2 * PI * hz * (idx + i) / SAMPLE_RATE));
    size_t sent = 0;
    while (sent < (size_t)n * 2) sent += xStreamBufferSend(audioStream, ((uint8_t*)blk) + sent, n * 2 - sent, pdMS_TO_TICKS(50));
    idx += n;
  }
}

// ===================== SERİ KOMUT AYRIŞTIRMA =====================
String line;
bool     binMode = false;
size_t   binExpected = 0, binGot = 0;
uint16_t binSum = 0;
uint32_t binLastByteMs = 0;
static uint8_t chunkBuf[AUDIO_CHUNK_MAX];

void handleLine(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;
  lastCmdMs = millis();
  int colon = cmd.indexOf(':');
  String key = (colon < 0) ? cmd : cmd.substring(0, colon);
  String arg = (colon < 0) ? "" : cmd.substring(colon + 1);
  key.toUpperCase();

  if (key == "PING") { Serial.println("PONG DESKBOT v1"); }
  else if (key == "PAN") {
    panTarget = constrain(arg.toFloat(), -PAN_LIMIT_DEG, PAN_LIMIT_DEG);
    panSettledMs = millis();
  }
  else if (key == "PANSPEED") { panMaxSpeed = constrain(arg.toFloat(), 10.0f, 300.0f); }
  else if (key == "EYES") { arg.toLowerCase(); arg.trim(); setEyeMode(arg); }
  else if (key == "LOOK") {
    int c = arg.indexOf(',');
    gazeX = constrain(arg.toFloat(), -100.0f, 100.0f) / 100.0f;
    gazeY = (c >= 0) ? constrain(arg.substring(c + 1).toFloat(), -100.0f, 100.0f) / 100.0f : 0;
    lastLookCmdMs = millis();
  }
  else if (key == "LED") {
    int v[4] = {0, 0, 0, 10}; int i = 0, start = 0;
    while (i < 4 && start <= (int)arg.length()) {
      int c = arg.indexOf(',', start); if (c < 0) c = arg.length();
      v[i++] = arg.substring(start, c).toInt(); start = c + 1;
    }
    setLed(v[0], v[1], v[2], v[3]);
  }
  else if (key == "VOL") { volumePct = constrain(arg.toInt(), 0, 100); }
  else if (key == "BL")  { analogWrite(PIN_TFT_BL, constrain(arg.toInt(), 0, 100) * 255 / 100); }
  else if (key == "BEEP") {
    int c = arg.indexOf(',');
    beep(arg.toInt(), c >= 0 ? arg.substring(c + 1).toInt() : 200);
  }
  else if (key == "AUDIO") {
    int c = arg.indexOf(':');
    long n = arg.toInt();
    if (n <= 0 || n > AUDIO_CHUNK_MAX || (n & 1)) { Serial.println("E:AUDIO_LEN"); return; }
    binExpected = n; binGot = 0;
    binSum = (c >= 0) ? (uint16_t)arg.substring(c + 1).toInt() : 0;
    binMode = true; binLastByteMs = millis();
  }
  else if (key == "AUDIO_STOP") { audioFlush = true; }
  else if (key == "STATUS") {
    Serial.printf("S:pan=%.1f,target=%.1f,eyes=%s,free=%u,vol=%d\n", panCurrent, panTarget,
                  eyeModeName(eyeMode), (unsigned)xStreamBufferSpacesAvailable(audioStream), volumePct);
  }
  else { Serial.print("E:UNKNOWN "); Serial.println(key); }
}

void finishAudioChunk() {
  uint32_t s = 0;
  for (size_t i = 0; i < binExpected; i++) s += chunkBuf[i];
  if ((uint16_t)(s & 0xFFFF) != binSum) {
    Serial.println("E:AUDIO_SUM");           // bozuk paket atlanır, akış bozulmaz
  } else {
    size_t sent = 0;
    uint32_t t0 = millis();
    // PC kredi kontrolü yaptığı için normalde hemen sığar; sığmazsa en fazla 200 ms bekle
    while (sent < binExpected && millis() - t0 < 200)
      sent += xStreamBufferSend(audioStream, chunkBuf + sent, binExpected - sent, pdMS_TO_TICKS(20));
  }
  Serial.printf("A:%u\n", (unsigned)xStreamBufferSpacesAvailable(audioStream));
  binMode = false;
}

void pollSerial() {
  // İkili (ses) modunda: bekleyen baytları topluca oku
  while (Serial.available() > 0) {
    if (binMode) {
      size_t want = binExpected - binGot;
      size_t got = Serial.readBytes(chunkBuf + binGot, min(want, (size_t)Serial.available()));
      binGot += got;
      binLastByteMs = millis();
      if (binGot >= binExpected) finishAudioChunk();
    } else {
      char ch = (char)Serial.read();
      if (ch == '\n') { handleLine(line); line = ""; }
      else if (ch != '\r') { if (line.length() < 120) line += ch; else line = ""; }
    }
  }
  if (binMode && millis() - binLastByteMs > AUDIO_TIMEOUT_MS) {
    binMode = false;                          // eksik paket: satır moduna geri dön (senkron kurtarma)
    Serial.println("E:AUDIO_TIMEOUT");
  }
}

// ===================== KURULUM / DÖNGÜ =====================
void setup() {
  Serial.setRxBufferSize(16384);              // begin()'den ÖNCE olmalı
  Serial.begin(SERIAL_BAUD);
  Serial.setTimeout(5);

  // Ekran
  pinMode(PIN_TFT_BL, OUTPUT);
  analogWrite(PIN_TFT_BL, 255);
  tft.init(240, 320);
  tft.setSPISpeed(40000000);
  tft.setRotation(TFT_ROTATION);
  tft.invertDisplay(TFT_INVERT);
  tft.fillScreen(ST77XX_BLACK);
  cvL = new GFXcanvas16(EYE_CW, EYE_CH);
  cvR = new GFXcanvas16(EYE_CW, EYE_CH);
  if (!cvL->getBuffer() || !cvR->getBuffer()) Serial.println("E:NO_MEM_CANVAS");

  // LED
  strip.begin();
  setLed(0, 40, 80, 10);

  // Servo: ortala
  ESP32PWM::allocateTimer(0);
  panServo.setPeriodHertz(50);
  servoWriteDeg(0);
  panSettledMs = millis();

  // Ses
  audioStream = xStreamBufferCreate(AUDIO_BUF_BYTES, 1);
  dacSetup();
  xTaskCreatePinnedToCore(audioTask, "audio", 4096, nullptr, 3, nullptr, 0);

  randomSeed(esp_random());
  nextBlinkMs = millis() + 1500;
  lastCmdMs = millis();
  Serial.println("READY DESKBOT v1");
}

void loop() {
  uint32_t now = millis();
  pollSerial();
  updateServo(now);

  // 10 dakika hiç komut gelmezse (PC kapalı / program kapalı) uyku gözü
  static bool autoSleep = false;
  if (!autoSleep && now - lastCmdMs > 600000UL) { autoSleep = true; eyeMode = EM_SLEEP; setLed(0, 0, 0, 0); }
  if (autoSleep && now - lastCmdMs < 1000) { autoSleep = false; if (eyeMode == EM_SLEEP) eyeMode = EM_IDLE; }

  if (now - lastFrameMs >= 33) {             // ~30 fps
    lastFrameMs = now;
    updateEyes(now);
    if (eyesDirty) { renderEyes(); eyesDirty = false; }
  }
}
