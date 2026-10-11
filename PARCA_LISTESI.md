# Parça Listesi - Masaüstü Robot v1 (sabit, kafa sağ-sol, PC'ye 2 ayrı USB kablo, hub yok)

Fiyatlar 10 Ekim 2026'da ürün sayfalarında görünen KDV dahil fiyatlardır (kargo hariç). Fiyat/stok değişebilir; almadan önce sayfayı kontrol et.

| # | Parça | Adet | Link | Fiyat (TL) | Not |
|---|---|---|---|---|---|
| 1 | 2 inç IPS LCD Ekran 240x320 ST7789 (Robotistan) | 1 | [link](https://www.robotistan.com/2-inc-lcd-ekran-modulu) | 702,56 | Göz ekranı, SPI; PCB 58x35 mm. Stokta görünüyordu. |
| 2 | MG90S Servo Motor 180° (Robotistan) | 1 | [link](https://www.robotistan.com/mg90s-servo-motor) | 124,69 | Kafa sağ-sol ±90°. Kol (horn) ve vidaları kutudan çıkar. |
| 3 | Logitech C270 Mikrofonlu HD Webcam (Trendyol) | 1 | [link](https://www.trendyol.com/logitech/c270-960-001063-mikrofonlu-hd-webcam-p-2378692) | 1.549,00 | Kasası sökülüp kartı kafaya girer; kamera + mikrofon tek USB. |
| 4 | 3W 2 Kanal Mini Amfi Devresi - PAM8403 (Motorobit) | 1 | [link](https://www.motorobit.com/3w-2-kanal-mini-amfi-devresi-pam8403) | 21,00 | 17,50 TL + KDV. ESP32 DAC (GPIO25) -> L-IN; sadece sol kanal kullanılır. Kart ~21x18 mm, montaj deliği yok. |
| 5 | Hoparlör 4Ω 3W 40 mm (Motorobit) | 1 | [link](https://www.motorobit.com/hoparlor-4-ohm-3w-40mm) | 105,00 | Gövde önündeki ızgaranın arkası. |
| 6 | WS2812B 8'li RGB LED Çubuk (Elektronikport) | 1 | [link](https://www.elektronikport.com/urun/ws2812b-neopixel-8li-serit-ws2812-full-color-rgb-led-module-neo-pixel-8-bit) | 54,71 | Kaidenin önündeki camgöbeği ışık. Sayfada stok durumu net değildi. |
| 7 | 1000 uF 16 V Elektrolit Kondansatör (Robotistan) | 1 | [link](https://www.robotistan.com/16v-1000uf-kondansator-paketi-5-adet) | 6,71 | Servo 5V-GND arasına (+ uca dikkat). |
| 8 | M2/M2.5/M3 YSB Vida Seti 900 parça (Özkuvvet) | 1 | [link](https://ozkuvvet.com/m2-m2-5-m3-ysb-vida-seti-900-parca-dopdolu-paket) | 1.062,68 | Sayfada 'stok bilgisi için ulaşınız' da yazıyordu. Alternatif: Deneystore 600 parça 1225,48 TL. M3x30 sette yoksa ayrıca al. |
| 9 | 40 pin Dişi-Dişi Jumper Kablo 200 mm (Robotistan) | 1 | [link](https://www.robotistan.com/40-pin-ayrilabilen-disi-disi-f-f-jumper-kablo-200-mm) | 48,56 | ESP32 - ekran/servo/amfi/LED bağlantıları. |
| 10 | HAMADEX 10 mm Şeffaf Silikon Tampon 50 adet (Trendyol) | 1 | [link](https://www.trendyol.com/hamadex/50-adet-10mm-seffaf-silikon-tampon-ses-stoperi-yapiskanli-dolap-kapi-tamponu-mobilya-koruyucu-p-971115540) | 156,08 | Kaide altı lastik ayak (4 adet). Fiyat arama sonucundan; sayfada kontrol et. |

**Toplam: 3.830,99 TL**  
C270 ve vida seti hariç: **1.219,31 TL**  
ESP32 listede yok (sende var: 30 pin DevKit, kaidedeki yuva buna göre).

## Listede fiyatı olmayan küçük malzemeler (elinde muhtemelen var)
- Micro-USB **data** kablosu (ESP32 -> PC), en az 1,5 m, **90° açılı fiş** (takılınca kablo aşağı, taban plakasına doğru dönmeli). Düz fiş sığmayabilir: ESP32 USB ağzından gövde iç duvarına ~18 mm boşluk var.
- C270 kendi kablosuyla PC'ye gider, kesilmez.
- 330 Ω direnç (LED veri hattı) - 1 adet
- Amfi girişi için (önerilir): 10 kΩ + 2,2 kΩ direnç (gerilim bölücü) ve 1-10 µF kondansatör (opsiyonel, DC engelleme)
- 2 adet M3 somun, ince kablo, lehim, makaron, sıcak silikon, cırt kelepçe
- Ağırlık için: M8 somun / bozuk para / çelik bilye (ön ağırlık kabına, ~40-70 g)
- Filament: beyaz PLA (~250 g), siyah PLA (vizör, ~2 g), gri/herhangi PLA (iç parçalar, ~60 g)

## Çıkarılanlar (önceki sürüme göre)
- USB hub kartı (CH334F), Type-C kablo ve opsiyonel USB-C 5V giriş kartı: hub kaldırıldı, kamera ve ESP32 ayrı kablolarla PC'ye bağlanır.
- ESP32: sende var, listeden çıkarıldı.
- 5V DC adaptör ve DC jak: gerek yok.
- MAX98357A I2S amfi: yerine PAM8403 (ESP32 dahili DAC ile analog giriş) geldi.
