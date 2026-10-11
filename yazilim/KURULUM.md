# Masaüstü Robot v1 - Yazılım Kurulumu

İki parça var:
- **esp32_kodu/**: ESP32'ye bir kez yüklenir (servo, göz ekranı, hoparlör, LED).
- **pc_panel/**: PC'de çalışan beyin (yüz takibi, dinleme, Grok ile konuşma).

---

## Adım 1 - ESP32 firmware'ini yükle

1. **Arduino IDE 2** indir ve kur: https://www.arduino.cc/en/software
2. **ESP32 kart paketi:** Dosya > Tercihler > "Ek kart yöneticisi URL'leri" kutusuna şunu yapıştır:
   `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   Sonra Araçlar > Kart > Kart Yöneticisi > **esp32** (Espressif Systems) > Yükle.
3. **Kütüphaneler:** Araçlar > Kütüphaneleri Yönet, şunları ara ve yükle:
   - `ESP32Servo`
   - `Adafruit ST7735 and ST7789 Library` (sorarsa "Install all" de, GFX ve BusIO da gelir)
   - `Adafruit NeoPixel`
   (TFT_eSPI kullanılmıyor, User_Setup ayarı yok.)
4. `esp32_kodu/robot_kodu/robot_kodu.ino` dosyasını aç (aynı klasördeki `eye_types.h` de otomatik açılır).
5. Araçlar menüsü: **Kart: ESP32 Dev Module**, **Port:** robot takılıyken çıkan COM portu.
   - Port görünmüyorsa USB sürücüsü eksik: kartın üstündeki çipe göre **CP210x** (Silicon Labs) ya da **CH340** sürücüsünü kur.
6. **Yükle** (sağ ok) butonuna bas. "Connecting...." yazısında takılırsa ESP32 üzerindeki **BOOT** tuşuna 2 saniye basılı tut.
7. Yüklenince ekranda iki mavi göz çıkmalı ve ara sıra göz kırpmalı.
   - Görüntü baş aşağıysa: `.ino` başında `TFT_ROTATION 1` yerine `3` yap, tekrar yükle.
   - Renkler negatif görünüyorsa (gözler mavi değil turuncu/garip): `TFT_INVERT true` yerine `false`.

> Firmware bir kere yüklenir. Sonra Arduino IDE'yi kapat (portu meşgul etmesin), yoksa PC programı robota bağlanamaz.

---

## Adım 2 - Python 3.11 kur

1. https://www.python.org/downloads/release/python-3119/ adresinden **Windows installer (64-bit)** indir.
2. Kurulumun ilk ekranında **"Add python.exe to PATH"** kutusunu işaretle, "Install Now".
3. (Python 3.12 de çalışır; 3.13 KULLANMA, MediaPipe desteklemiyor.)

---

## Adım 3 - xAI API anahtarı al ve kaydet

1. https://console.x.ai adresine gir, hesap aç, **API Keys** bölümünden yeni anahtar oluştur (`xai-...` ile başlar).
2. Konsolda bakiye/kredi yükle (API kullanımı ücretli, aşağıda maliyet notu var).
3. Anahtarı Windows'a kaydet: Başlat'a **cmd** yaz, aç ve şunu yaz (kendi anahtarınla):
   ```
   setx XAI_API_KEY "xai-BURAYA-ANAHTARIN"
   ```
4. Açık olan cmd/baslat pencerelerini **kapatıp yeniden aç** (yeni değişken ancak yeni pencerede görünür).

Anahtarı kimseyle paylaşma, config.yaml'a da yazma.

---

## Adım 4 - Programı çalıştır

1. Robotu PC'nin **mavi USB 3 portuna** tak.
2. `pc_panel` klasöründe **`baslat.bat`**'a çift tıkla.
   - İlk seferde sanal ortam kurar ve paketleri indirir (5-10 dk sürebilir). Sonraki açılışlar hızlıdır.
3. Önce test yap: `pc_panel` klasöründe adres çubuğuna `cmd` yazıp Enter, sonra:
   ```
   baslat.bat --test
   ```
   Test şunları kontrol eder: API anahtarı, kamera, yüz bulucu, mikrofon, ESP32 bağlantısı, servo taraması (orta-sol-sağ-orta), göz ifadeleri, LED renkleri, hoparlör bipi ve Türkçe konuşma sesi. Ayrıca kullanılabilir xAI seslerini listeler.
4. Test tamamsa normal çalıştır: `baslat.bat`. Karşısına geç, seni bulup kafasını çevirecek. Konuş, cevap verecek.
5. Mikrofonsuz denemek için: `baslat.bat --yazi` (klavyeden yazarsın, robot sesli cevap verir).

### LED renkleri
mavi = boşta, yeşil = dinliyor, mor = düşünüyor, turkuaz = konuşuyor, kırmızı = hata.

### Windows açılınca otomatik başlasın
`pc_panel\otomatik_baslat_kur.bat`'a bir kez çift tıkla. Kaldırmak için ekranda yazan dosyayı sil.

---

## Kontrol paneli (önerilen)

`pc_panel` klasöründe **`panel_baslat.bat`**'a çift tıkla. İlk seferde eksik paketleri kurar (birkaç dakika), sonra siyah pencere olmadan panel açılır. Masaüstüne kısayol istersen `panel_baslat.bat`'a sağ tık > Gönder > Masaüstü (kısayol oluştur).

| Sekme | Ne var |
|---|---|
| **Durum** | Robotu Başlat/Durdur, robotun şu anki hali (dinliyor / düşünüyor / konuşuyor), ESP32 portu, kamera, mikrofon ve internet/Grok durumu, yüz kutulu küçük kamera önizlemesi, olay kaydı. "Windows açılınca paneli başlat" anahtarı (açılınca robot da kendiliğinden başlar). |
| **Kişilik** | Karakter metni, model, ses motoru (xai/edge), ses, hoparlör (robot/pc). **Kaydet** config.yaml'a yazar ve robotu kapatmadan hemen geçerli olur. |
| **Hafıza** | `notlar.txt` notları: ekle, seçip düzelt, sil. "Sohbet hafızasını temizle" sadece son konuşmaları unutturur, notlar kalır. |
| **Sohbet** | Konuşma geçmişi (sen / robot). Alttaki kutuya yazıp robotla konuşabilirsin; "Sesli cevap ver" kapalıysa sadece yazıyla cevap verir. |
| **Test** | Kafa (-60° / orta / +60° ve kaydırıcı), göz ifadeleri, LED renkleri ve parlaklık, bip, test cümlesi, ses seviyesi. Test sırasında yüz takibi otomatik duraklar; bitince "Takibi duraklat"ı kapat. |

- İnternet (telefon hotspot'u) koparsa panelde **İnternet yok** yazar, robot kapanmaz; internet gelince kendiliğinden devam eder. Bağlantı kontrolü 2 dakikada bir yapılır, kotayı yemez.
- Panel ve `baslat.bat` aynı anda açılmaz (ikisi de robota bağlanmaya çalışır). Birini kullan.
- Eski `otomatik_baslat_kur.bat` ile kurduysan, panelde otomatik başlatmayı açınca eskisini kaldırmayı sorar.
- Panel hiç açılmazsa `pc_panel\panel_hata.txt` dosyasına bak.

---

## Ayarlar (pc_panel/config.yaml)

Not Defteri ile aç, değiştir, programı yeniden başlat. (Karakter, model, ses ve ses seviyesi panelden de değişir.)

| Ayar | Ne işe yarar |
|---|---|
| `persona` | Robotun karakteri. Küfür dozu, tarzı, kime nasıl laf sokacağı burada. |
| `voice.output` | `robot` = robotun hoparlörü, `pc` = bilgisayarın hoparlörü |
| `voice.tts_engine` | `xai` = Grok sesi (ücretli, daha doğal), `edge` = Microsoft Türkçe ses (ücretsiz) |
| `voice.xai_voice` | Grok sesi (`rex`, `eve`, `ara`...; tam liste `--test` çıktısında) |
| `voice.robot_volume` | Robot hoparlör sesi (0-100). Robot resetleniyorsa düşür. |
| `xai.model` | Varsayılan hızlı/ucuz model. Daha zeki ama daha yavaş: `grok-4.7` |
| `xai.web_search` | `xai` = Grok'un kendi web araması, `ddg` = DuckDuckGo, `off` = kapalı |
| `conversation.require_wake_word` | `true` = sadece "Şakir" deyince cevap verir |
| `conversation.only_when_face_visible` | Kimse görünmüyorsa (ve ismi geçmiyorsa) cevap vermez, boşa API harcamaz |
| `tracking.pan_invert` | Kafa senden **uzağa** dönüyorsa `true` yap |
| `tracking.kp`, `deadband_deg` | Takip hızı / titreme önleme |
| `serial.port`, `camera.index` | Otomatik bulamazsa elle yaz (`COM5`, `1` gibi) |

Robot "bunu unutma" dediğin şeyleri `pc_panel/notlar.txt` dosyasına yazar; her konuşmada hatırlar. Sohbet hafızası son 8 konuşmadır.

---

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| "Robot (ESP32) bulunamadı" | Arduino IDE açıksa kapat. Aygıt Yöneticisi > Bağlantı noktaları'nda COM görünüyor mu bak; görünmüyorsa CP210x/CH340 sürücüsü kur. Hâlâ olmazsa config'te `port: "COM5"` gibi elle yaz. |
| Kamera açılmıyor / yanlış kamera (laptop kamerası) | `camera.index` değerini 0, 1, 2 dene. Kamerayı başka program (Zoom, Discord) kullanıyorsa kapat. |
| Kafa yüzden uzağa dönüyor | `tracking.pan_invert: true` |
| Kafa sağa sola titriyor | `kp` küçült (0.3), `deadband_deg` büyüt (6) |
| Kafa ortada değil | firmware'de `PAN_TRIM_DEG` ile düzelt (örn. -5) |
| Konuşurken kamera kopuyor / ESP32 resetleniyor | Güç yetmiyor: `robot_volume` düşür, LED parlaklığını düşür; ESP32 kablosunu PC'nin USB 3 portuna tak (bu sürümde harici 5V girişi yok). |
| Hiç duymuyor | `--test` mikrofon seviyesine bak. Windows Ses ayarlarında C270 mikrofonu açık mı? Gürültülü ortamda `vad_aggressiveness: 3`. |
| Kendi kendine konuşuyor / her şeye cevap veriyor | `require_wake_word: true` yap. |
| Cevap yok, "401" hatası | API anahtarı yanlış ya da `setx` sonrası pencere yeniden açılmadı. |
| "429" ya da kredi hatası | console.x.ai'den bakiye yükle. |
| Robot hoparlöründen ses cızırtılı | `voice.output: pc` yapıp PC hoparlörünü dene; amfi kablolarını (GPIO25 → PAM8403 L-IN, GND → ⊥, VIN → 5V+) kontrol et. Ses bozuk/çok yüksekse firmware'de `DAC_SWING` değerini düşür (doğrudan bağlantıda 48, 10k/2,2k bölücüyle 120). |
| Paket kurulumu bozuldu | `pc_panel\.venv` klasörünü sil, `baslat.bat`'ı yeniden çalıştır. |

Kayıtlar `pc_panel/robot.log` dosyasına da yazılır.

---

## Maliyet (yaklaşık, xAI resmi fiyat sayfasından, 10.10.2026)

Kaynak: https://docs.x.ai/docs/models
- Konuşma modeli `grok-4.20-0309-non-reasoning`: 1M giriş token'ı 1,25 $, 1M çıkış token'ı 2,50 $
- Sesi yazıya çevirme (STT): saati 0,10 $
- Yazıyı sese çevirme (TTS): 1M karakter 15 $

Bir soru-cevap kabaca: ~1.500 giriş + ~80 çıkış token'ı (~0,002 $) + ~150 karakter ses (~0,002 $) + 5 sn dinleme (~0,0001 $) ≈ **0,005 $**. Yani 100 konuşma yaklaşık **0,5 $**. Web araması kullanılan cevaplar ayrıca ücretlendirilebilir; harcamayı console.x.ai'den takip et.
Para harcamamak için: `tts_engine: edge` (ücretsiz ses), `only_when_face_visible: true`, `require_wake_word: true`.

---

## Seri protokol (meraklısına)

PC ile ESP32 arasında 921600 baud, satır tabanlı komutlar: `PAN:-30`, `PANSPEED:90`, `EYES:happy`, `LOOK:40,0`, `LED:0,60,160,12`, `VOL:60`, `BEEP:880,200`, `AUDIO_STOP`, `STATUS`, `PING`.
Ses: `AUDIO:<bayt>:<toplam>` satırından sonra ham 16 kHz 16 bit mono PCM gelir; ESP32 her paketten sonra `A:<boş tampon>` cevabı verir, PC buna göre hız ayarlar (ses 32 KB/sn, hat ~92 KB/sn). Ayrıntılar `robot_kodu.ino` başındaki açıklamada.
