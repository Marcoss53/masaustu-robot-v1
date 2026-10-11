# ESP32 firmware - gerekenler

- Arduino IDE 2.x
- Kart paketi: **esp32 by Espressif Systems** (3.x; 3.3.12 ile derlendi). 2.0.x de destekleniyor.
- Kart seçimi: **ESP32 Dev Module**
- Kütüphaneler (Araçlar > Kütüphaneleri Yönet):
  - ESP32Servo (Kevin Harrington / madhephaestus), 3.2.1 ile denendi
  - Adafruit ST7735 and ST7789 Library, 1.11.0 ile denendi (Adafruit GFX ve BusIO'yu kendisi ister, "Install all" de)
  - Adafruit GFX Library
  - Adafruit NeoPixel
- TFT_eSPI KULLANILMIYOR, User_Setup ayarı gerekmez.

Klasör: `robot_kodu/` (içinde `robot_kodu.ino` ve `eye_types.h`). İkisi aynı klasörde durmalı.

Ayarlar `robot_kodu.ino` dosyasının başında:
- `TFT_ROTATION` (görüntü baş aşağıysa 1 yerine 3)
- `TFT_INVERT` (renkler negatif görünüyorsa false)
- `SERVO_INVERT`, `PAN_TRIM_DEG` (servo yönü / orta ayarı)
