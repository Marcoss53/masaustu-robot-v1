# Montaj Kılavuzu - Masaüstü Robot v1

Sabit duran, sadece kafası sağa-sola (±90°) dönen, PC'ye **2 ayrı USB kablo** ile bağlanan masaüstü robot.
Beyin Windows PC; robotun içinde kamera+mikrofon (C270), ESP32 (ekran, servo, hoparlör amfisi, LED) var. **USB hub yok:** kaidenin arkasından iki kablo çıkar, biri kamera (C270), biri ESP32; ikisi PC'de iki ayrı USB portuna takılır.

Ölçüler (montajlı): yükseklik ~160 mm (+ayaklar), kaide Ø114 mm, kafa 109 mm (kulaklarla) x 82 mm derinlik, gövde 88x74 mm.

## 1. Baskı ayarları (Bambu Lab A2L)

Genel: PLA, 0,4 nozül, 0,2 mm katman, 3 duvar, üst/alt 5 katman, %15 gyroid dolgu. M3 vidaların gireceği kılavuz delikler (Ø2,6) için duvar sayısı 4 daha iyi olur.

| Dosya (3d_parcalar/) | Renk | Tablaya yatış (dosyada hazır) | Destek | Not |
|---|---|---|---|---|
| 5_kafa_on.stl (v2) | Beyaz | Bölme yüzü (düz kesit) tablada, yüz yukarı | **Gerekli: ağaç (tree) destek, sadece tabladan (build plate only)** | Kubbenin iç tavanı için. Destekler içten çıkar. |
| 6_kafa_arka.stl | Beyaz | Bölme yüzü tablada | **Gerekli: ağaç destek, içe** | Aynı sebep. Arkadaki havalandırma yarıkları desteksiz. |
| 3_govde.stl | Beyaz | Ters (tavan tablada) | Yok | Üst kenar 45° pahlı, desteksiz basılır. |
| 2_kaide.stl | Beyaz | Ters (güverte tablada) | Yok | LED yarığı yatay köprü, sorun olmaz. Arkadaki 2 kablo çentiği alttan açık, baskıda üstte kalır, desteksiz. |
| 1_taban_plakasi.stl | Gri/herhangi | Düz | Yok | Bileşen tablası + ağırlık kabı + 2 kablo ankrajı. |
| 4_boyun.stl | Gri/beyaz | Üst yüz tablada | Yok | Servo kolu cebi yukarı bakar. |
| 9_vizor_siyah.stl | **Siyah** | Düz | Yok | %100 dolgu. Parlak siyah PLA veya smoke PETG daha şık durur. |
| 7_ekran_braketi.stl | Gri | Arka yüz tablada | Yok (gerekirse "sadece tabla") | |
| 8_kamera_braketi.stl | Gri | Arka yüz tablada | Yok (gerekirse "sadece tabla") | |

`tum_parcalar.3mf` tüm parçaları tek dosyada yan yana içerir (toplu bakış için). En temiz sonuç için beyaz parçaları bir plakada, siyah vizörü ayrı bastır.

Boyutlar (baskı yönünde, mm):
2_kaide 114x114x16 · 1_taban_plakasi 110x110x26,4 · 3_govde 88x74x58,4 · 4_boyun 52x52x10 · 5_kafa_on 109x77x38 · 6_kafa_arka 109x77x44 · 9_vizor_siyah 61,4x35,4x1,6 · 7_ekran_braketi 76x38x10,5 · 8_kamera_braketi 31x67,7x8,5

## 2. Hazırlık

1. **M3 kılavuz delikleri (insert yok):** Pirinç insert kullanılmıyor. 3_govde (4 kolon altı), 4_boyun (üstte 4) ve 5_kafa_on (bölme yüzünde 4, arka kapak) delikleri Ø2,6 mm; M3 vidayı doğrudan deliğe yavaşça vidala, fazla sıkma; çok sökülürse yalama olur. Geçiş delikleri (diğer tarafta) ~Ø3,4 mm, değişmedi.
2. **C270'i sök:** ön kapağı kaldır, vidaları sök, kartı çıkar. Mikrofon kartın üzerinde, onu koru. Kablosu **kesilmez**, kendi USB fişiyle PC'ye gider. Not: kasayı açınca garanti biter.
3. **Servoyu ortala:** ESP32'ye bağlayıp 90°'ye (1500 µs) getir. Kolu bu konumda takacağız; yazılımda açı 0..180 yerine **0..180 (merkez 90) ve kafa için ±90** ile sınırla.

## 3. Vida ölçüleri (M3 self-tap / geçiş)

| Yer | Vida | Not |
|---|---|---|
| Taban → gövde kolonları | 4× M3×18 (veya M3×20) | Alttan, Ø2,6 kılavuz |
| Kafa ön → 4_boyun | 4× M3×8 (M3×10 da olur) | İçeriden, Ø2,6 kılavuz |
| Kafa arka kapak → ön | 4× M3×12 | Dışarıdan geçiş + ön kılavuz |
| Ekran braketi (v2) | 2× M3×10 | Arkadan, braket kulağından ön duvardaki kolonlara self-tap |
| Kamera braketi → kafa | 2× M3×18 | Braket tarafı zaten self-tap |

## 4. Montaj sırası

1. **Servo:** Gövde ters dururken servoyu alttan tavandaki deliğe sok (mil yukarı, gövdesi arkaya doğru). Tabları 2 servo vidası (M2) ile tavandaki ayaklara vida.
2. **Göbek:** Çift kollu servo kolunu (horn) 4_boyun parçasının alttaki cebine yerleştir, kutudan çıkan küçük vidalarla alttan göbeğe sabitle. Göbek+kolu milin üstüne kafa önü (kablo deliği) öne bakacak şekilde bas, ortadaki Ø7 delikten servo merkez vidasını sık.
3. **Kafa ön yarısı:** Ekran ve kamera kablolarını göbekteki kablo deliğinden ve gövde tavanındaki yay şeklindeki kanaldan aşağı sarkıt. 5_kafa_on parçasını göbeğe **içeriden 4x M3x8** ile vida (kamera braketini takmadan önce, yoksa vidalara ulaşılmaz).
4. **Vizör + ekran:** Siyah vizörü önden cebine yapıştır (birkaç nokta CA/sıcak silikon). Ekranı ekran yüzü öne gelecek şekilde vizörün arkasına koy, ekranı 7_ekran_braketi parçasına oturt ve ikisini birlikte kafanın açık arkasından düz it (zorlamadan girer, her yanda ≥0,6 mm boşluk); **2x M3x10** vidayı braket kulaklarından ön duvardaki kısa kolonlara sık (v2). Ekran kablosu braketin alt çentiğinden çıkar.
5. **Kamera:** C270 kartını lens öne gelecek şekilde 8_kamera_braketi raylarına koy (lens kafadaki deliğe oturur), yan dudakların üstünden **4x M2x6 + pul** ile kıskaçla. Braketi **2x M3x18** ile kafadaki kolonlara vida (bölme yüzü tarafından).
6. **Kafayı kapat:** Kablolarda 6-8 cm **servis halkası** bırak (±90° dönüş için). 6_kafa_arka parçasını takıp dışarıdan **4x M3x12** ile kapat.
7. **Gövde içi:** Hoparlörü ön duvardaki halkaya sıcak silikonla otur (ızgaranın arkası).
8. **Taban plakası (1_taban_plakasi):**
   - **Kablo çıkışları:** Arkadan bakınca sol çentik C270, sağ çentik ESP32 kablosu içindir (çentikler 2_kaide parçasının alt kenarında, alttan açık). Kabloyu plakanın üstünden geçirip arka kenara getir, yanındaki küçük ankraj bloğunun tünelinden cırt kelepçe geçirip kabloyu ankraja sıkıca bağla (dışarıdan çekilince içerideki fiş/lehim zorlanmasın). İçeride 3-4 cm boşluk bırak.
   - ESP32 kablosu **90° açılı micro-USB** olmalı; takınca kablo aşağı dönüp güverte açıklığından plakaya iner. Düz fiş gövde duvarına dayanır (~18 mm boşluk).
   - ESP32.yi (pinler aşağı, micro-USB ucu önden bakınca sağ tarafa) iki ince duvarın üstüne yatır, ortadaki yuvadan cırt kelepçe ile bağla. Dupont kablolar kartın altından çıkar.
   - PAM8403 amfiyi sol tepsiye (v2 cep 22,2x20,2 mm; pedler X uçlarında, kablo çentikleri iki uçta) koy, altına çift taraflı bant; LED çubuğunu öndeki iki rayın arasına (LED'ler öne bakacak) koy; sıcak silikonla sabitle.
   - Ön ağırlık kabını somun/bilye ile doldur (40-70 g) ve üstünü bantla kapat. Bu, kafayı çevirirken devrilmeyi önler.
9. **Kablolama:** Aşağıdaki tabloya ve `gorseller/baglanti_semasi.png` şemasına göre bağla. Kablo yolu için `gorseller/kablo_yolu.png`. Test et (bölüm 7) ve sonra kapat.
10. **Kapatma:** Kaide halkasını (2_kaide) taban plakasının üstüne geçir (plaka halkanın altındaki yuvaya oturur); geçirirken iki kabloyu arkadaki çentiklere yukarıdan yatır, sıkışmasın, gövdeyi güverteye oturt (alt dudak güverte açıklığına girer). **4x M3x18** (M3x20 daha iyi tutunur) vidayı alttan taban plakasının burçlarından geçirip gövde kolonlarındaki Ø2,6 kılavuz deliklere yavaşça vidala, fazla sıkma. 4 lastik ayağı alttaki yuvalara yapıştır.

## 5. Bağlantı şeması

![Kablo yolu](gorseller/kablo_yolu.png)


### 5.1 USB (2 ayrı kablo, hub yok)

```
PC USB portu A (herhangi)          <── C270 kamera+mikrofon (kendi kablosu, sol çentik)
PC USB portu B (USB 3.x, mavi/SS)  <── ESP32 micro-USB data kablosu (90° açılı fiş, sağ çentik)
                                        servo + amfi + LED de bu kablodan beslenir
```

Lehim yok. ESP32 kablosu mutlaka **data** kablosu olmalı (sadece şarj kablosunda COM port görünmez).

### 5.2 ESP32 pinleri (30 pin DevKit)

![Bağlantı şeması](gorseller/baglanti_semasi.png)


| ESP32 pini | Bağlandığı yer | Not |
|---|---|---|
| GPIO18 | Ekran SCK/CLK | SPI saat |
| GPIO23 | Ekran MOSI/DIN | SPI veri |
| GPIO5 | Ekran CS | |
| GPIO16 | Ekran DC | |
| GPIO17 | Ekran RST | |
| GPIO4 | Ekran BL (arka ışık) | PWM ile parlaklık |
| 3V3 | Ekran VCC | Ekran 3,3V ile çalışır |
| GPIO13 | Servo sinyal (turuncu) | |
| GPIO25 | PAM8403 **L** girişi (alttaki 3'lü pedin L'si) | Dahili DAC (8 bit ses). Önerilen: araya bölücü (aşağıda) |
| GND | PAM8403 giriş **⊥** (L ile R arasındaki orta ped) | Ses toprağı |
| VIN (5V) | PAM8403 **5V +** | RAIL (bkz. 5.3) |
| GND | PAM8403 **5V −** | |
| GPIO27 | WS2812B DIN | Araya **330 Ω** seri direnç |
| GND | Tüm GND'ler (ortak) | **Şart** |

**PAM8403 (Motorobit, ~21x18 mm, 2 kanal; sadece sol kanal kullanılır):**

```
ESP32 GPIO25 ──[10 kΩ]──┬──[1-10 µF, opsiyonel; + ucu ESP32 tarafına]── PAM8403 L-IN
                        └──[2,2 kΩ]── GND                        PAM8403 ⊥ (giriş GND) ── ESP32 GND
ESP32 VIN (5V) ── PAM8403 5V+        ESP32 GND ── PAM8403 5V−
Hoparlör (4Ω 3W) ── PAM8403 çıkış L+ ve L−   (R+ / R− boş)
```

- Bölücü (10k + 2,2k) önerilir: PAM8403'ün kazancı yüksek (~24 dB); bölücüyle firmware'de `DAC_SWING` 120 yapılır, cızırtı azalır. Bölücü olmadan GPIO25'i doğrudan L-IN'e bağlayabilirsin; o zaman `DAC_SWING` 48 (varsayılan) kalsın.
- Kartın girişinde zaten kuplaj kondansatörü vardır; 1-10 µF ek kondansatör opsiyoneldir (elektrolitse + ucu ESP32/bölücü tarafına).
- **Hoparlör L− ucunu GND'ye bağlama** (köprü çıkış). Hoparlörü güç vermeden önce bağla.
- R girişi ve R çıkışı boş kalır. GPIO26 ve GPIO22 artık boş.

### 5.3 5V güç hattı ("RAIL")

- Servo (kırmızı), amfi VIN ve LED 5V aynı **RAIL**'den beslenir. **RAIL = ESP32'nin VIN pini** (USB'den gelen 5V; çoğu 30 pin DevKit'te arada bir diyot olduğu için ~4,6-4,9 V ölçülür). Kamera kendi kablosundan beslenir.
- Servo/amfi/LED GND'leri ESP32 GND'sine. RAIL'e başka bir 5V kaynağı (şarj aleti vb.) **bağlama**; USB'ye geri besleme olur.
- **1000 µF 16 V kondansatörü** servonun 5V-GND uçlarına, servoya yakın lehimle (uzun bacak / işaretsiz taraf = +, şeritli taraf = -). Servo kalkışında voltaj düşüşünü ve ESP32 resetlerini azaltır.
- İlk testte servo dönerken ve ses çalarken VIN-GND gerilimini multimetreyle ölç; 4,4 V altına iniyorsa LED parlaklığını ve sesi düşür.

### 5.4 Güç bütçesi (tahmini, ölçülmedi)

| Tüketici | Normal | Tepe |
|---|---|---|
| C270 kamera+mik (ayrı port) | ~0,15-0,25 A | ~0,3 A |
| ESP32 (Wi-Fi kapalı) + ekran | ~0,1-0,15 A | ~0,25 A (Wi-Fi açılırsa) |
| MG90S servo | ~0,01 A (dururken) / 0,15-0,3 A (dönerken) | ~0,7 A+ (zorlanınca) |
| PAM8403 + 3W hoparlör | ~0,1-0,2 A (konuşma) | ~0,6-0,8 A (tam ses) |
| WS2812B 8 LED | ~0,05-0,1 A (%20 parlaklık) | ~0,48 A (tam beyaz) |
| **ESP32 portu toplamı (kamera hariç)** | **~0,3-0,6 A** | **>1,2 A** |

Sonuç: Kamera ayrı porta geçtiği için ESP32 portunun yükü hafifledi. USB 2.0 portu (0,5 A) yine **sınırda**, USB 3.x portu (0,9 A) normal kullanımda yeter; şu kurallarla:
- ESP32 kablosunu PC'nin **USB 3 (mavi/SS) portuna** tak, araya pasif çoklayıcı koyma. Kamerayı herhangi bir porta takabilirsin.
- Yazılımda: LED parlaklığı ≤ %20, ses seviyesi orta, servoyu yavaş ve kademeli hareket ettir (ani 180° sıçrama yok), servo, hoparlör ve LED'i aynı anda tam güçte çalıştırma.
- ESP32 resetleniyorsa: ses ve LED'i düşür, servoyu yavaşlat. Harici güç girişi bu sürümde yok.

## 6. Yazılım notları (kısa)

- PC (Python): kamera ve mikrofon Windows'ta "Logitech C270" olarak görünür (OpenCV / sounddevice ile okunur).
- PC → ESP32: USB seri port (COM). Komutlar: göz ifadesi, kafa açısı, LED rengi. Ses: PC 16 kHz 16 bit mono PCM'i seri portla (921600 baud yeterli) ESP32'ye akıtır; PC sesi normalize eder (DC/150 Hz altı kesilir, tepe -1 dBFS), ESP32 8 bit dahili DAC'tan (GPIO25, 16 kHz) PAM8403'e verir. Ses seviyesi + limitleyici firmware'de. Alternatif: PC'ye USB ses kartı + küçük amfi (bu listede yok).
- Kafa açısı yazılımda **-90..+90 (servo 0..180)** ile sınırlanmalı; mekanik dayanak yok, kablo halkası bu aralığa göre bırakıldı.

## 7. Kapatmadan önce test listesi

1. C270'i PC'ye tak: Kamera uygulamasında görüntü + mikrofon testi.
2. ESP32'yi USB 3 portuna tak: Aygıt Yöneticisi'nde COM port olarak görünmeli; örnek kodla ekrana göz çiz.
3. Kabloları ankrajlara bağladıktan sonra dışarıdan hafifçe çek: içerideki fişler oynamamalı.
4. Servo: 90° → 0° → 180° yavaş tarama; kafa hiçbir yere sürtmemeli, kablolar gerilmemeli.
5. Ses: test tonu; ses kısıkken servo hareketiyle beraber çal, kamera kopmamalı.
6. LED: %20 parlaklıkta camgöbeği.

## 8. Bilinen riskler / doğrulanmamış noktalar

- Model **basılıp denenmedi**; ölçüler ürün sayfası/çizimlerine göre. İlk baskıdan sonra ekran ve kamera oturuşunu kontrol et (parametreler `robot_model.scad` başında).
- 2" ekranın aktif alanının PCB üzerindeki kaçıklığı bilinmiyor; pencere 42x32 mm, gerekirse `win_w/win_h` ya da vizör konumunu düzelt.
- C270 kart ölçüsü (≈21-23,5 x 58 mm, lens ekseni uçtan 13 mm) topluluk ölçümünden; parti farkı olabilir.
- Kablo çentikleri 5 mm genişliğinde (C270 ve çoğu USB kablosu 3-4,5 mm). Kablon kalınsa `cab_w` değerini büyüt; inceyse kablo ankraja bağlı olduğu için sorun olmaz.
- ESP32 VIN pininden çekilebilecek akım kartın diyot/hat değerine bağlı, doğrulanmadı.
- MG90S mil yüksekliği üreticiye göre ±1 mm değişir; göbek gövdeye sürtüyorsa göbek altına pul koy, boşluk fazlaysa `standoff` değerini değiştir.
- Güç bütçesi tahmindir, ölçülmedi.
- PC'den ESP32'ye ses akıtma yazılım işi ister (hazır değil).
- WS2812B 8'li çubuğun Elektronikport sayfasındaki stok durumu çelişkiliydi; vida setinde M3x30 olmayabilir.
