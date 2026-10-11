"""ESP32 ile USB seri bağlantı: komut gönderme, ses akıtma, kopunca yeniden bağlanma."""
import logging
import threading
import time

import serial
from serial.tools import list_ports

log = logging.getLogger("seri")

# ESP32 DevKit kartlarındaki USB-seri çiplerin VID:PID değerleri
KNOWN_USB_IDS = {
    (0x10C4, 0xEA60): "CP210x",
    (0x1A86, 0x7523): "CH340",
    (0x1A86, 0x55D4): "CH9102",
    (0x0403, 0x6001): "FTDI",
    (0x303A, 0x1001): "ESP32 USB",
}

AUDIO_CHUNK = 2048          # bayt (64 ms ses), firmware en fazla 4096 kabul eder
ESP_AUDIO_BUF = 32768       # firmware'deki tampon boyutu
SAMPLE_RATE = 16000


def prep_for_dac(pcm: bytes) -> bytes:
    """ESP32'nin 8 bit DAC'ı (PAM8403) için konuşmayı hazırla: DC'yi at, ~150 Hz altını kes
    (küçük hoparlör zaten veremez, amfiyi boşa zorlar), tepeyi -1 dBFS'e normalize et
    (en fazla 4 kat yükselt; sessizlik/gürültü şişmesin) ve hafif yumuşak sınırlama uygula.
    Format değişmez: 16 kHz, 16 bit, mono."""
    try:
        import numpy as np
    except ImportError:
        return pcm
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    if x.size < 32:
        return pcm
    x -= x.mean()
    a = np.exp(-2 * np.pi * 150 / SAMPLE_RATE)          # 1. derece yüksek geçiren
    y = np.empty_like(x); prev_x = 0.0; prev_y = 0.0
    try:
        from scipy.signal import lfilter
        y = lfilter([(1 + a) / 2, -(1 + a) / 2], [1, -a], x).astype(np.float32)
    except Exception:
        for i in range(x.size):
            prev_y = (1 + a) / 2 * (x[i] - prev_x) + a * prev_y; prev_x = x[i]; y[i] = prev_y
    peak = float(np.max(np.abs(y))) or 1.0
    y *= min(0.89 * 32767 / peak, 4.0)
    y = 32767 * np.tanh(y / 32767 * 1.2) / np.tanh(1.2)   # yumuşak sınır, kırpma yok
    return np.clip(y, -32767, 32767).astype(np.int16).tobytes()


class SerialLink:
    def __init__(self, port="auto", baud=921600):
        self.port_setting = port
        self.baud = baud
        self.ser = None
        self.port_name = None
        self.connected = False
        self._wlock = threading.Lock()
        self._cv = threading.Condition()
        self._free = ESP_AUDIO_BUF      # ESP32 tamponundaki boş yer (son bildirilen)
        self._inflight = 0              # onayı (A:) beklenen ses paketi sayısı
        self._free_t = time.time()      # _free'nin bildirildiği an
        self._sent_t = 0.0
        self._pong = threading.Event()
        self._last_status = ""
        self._stop = threading.Event()
        self._state_cache = {}          # yeniden bağlanınca son durumu geri yüklemek için
        threading.Thread(target=self._manager, daemon=True, name="seri-yonetici").start()

    # ---------------- bağlantı yönetimi ----------------
    def _candidates(self):
        if self.port_setting and str(self.port_setting).lower() != "auto":
            return [self.port_setting]
        ports = list(list_ports.comports())
        known = [p.device for p in ports if (p.vid, p.pid) in KNOWN_USB_IDS]
        others = [p.device for p in ports if p.device not in known and p.vid is not None]
        return known + others

    def _try_open(self, dev):
        try:
            s = serial.Serial()
            s.port = dev
            s.baudrate = self.baud
            s.timeout = 0.05
            s.write_timeout = 2
            s.dtr = False            # ESP32'yi açılışta resetlememek için
            s.rts = False
            s.open()
        except Exception as e:
            log.debug("%s açılamadı: %s", dev, e)
            return None
        # Kart resetlenmiş olabilir; açılış mesajı için biraz bekle, sonra PING
        deadline = time.time() + 3.0
        buf = b""
        next_ping = time.time() + 0.3
        while time.time() < deadline:
            if time.time() >= next_ping:
                try:
                    s.write(b"\nPING\n")
                except Exception:
                    break
                next_ping = time.time() + 0.6
            buf += s.read(256)
            if b"PONG DESKBOT" in buf:
                return s
        s.close()
        return None

    def _manager(self):
        while not self._stop.is_set():
            if not self.connected:
                for dev in self._candidates():
                    s = self._try_open(dev)
                    if s:
                        self.ser, self.port_name, self.connected = s, dev, True
                        with self._cv:
                            self._free, self._inflight, self._free_t = ESP_AUDIO_BUF, 0, time.time()
                        log.info("Robot bağlandı: %s", dev)
                        threading.Thread(target=self._reader, daemon=True, name="seri-okuyucu").start()
                        self._restore_state()
                        break
                else:
                    log.warning("Robot (ESP32) bulunamadı, 3 sn sonra tekrar denenecek...")
                    self._stop.wait(3)
                    continue
            self._stop.wait(1)

    def _restore_state(self):
        for cmd in list(self._state_cache.values()):
            self.send(cmd, cache=False)

    def _drop(self, why):
        if self.connected:
            log.warning("Robot bağlantısı koptu (%s). Yeniden bağlanılacak.", why)
        self.connected = False
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        with self._cv:
            self._inflight = 0
            self._cv.notify_all()

    def _reader(self):
        ser = self.ser
        buf = b""
        while self.connected and ser is self.ser:
            try:
                data = ser.read(512)
            except Exception as e:
                self._drop(str(e))
                return
            if not data:
                continue
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                self._on_line(line.decode("utf-8", "replace").strip())

    def _on_line(self, line):
        if not line:
            return
        if line.startswith("A:"):
            with self._cv:
                try:
                    self._free = int(line[2:])
                    self._free_t = time.time()
                except ValueError:
                    pass
                self._inflight = max(0, self._inflight - 1)
                self._cv.notify_all()
        elif line.startswith("E:AUDIO_TIMEOUT") or line.startswith("E:AUDIO_LEN"):
            with self._cv:
                self._inflight = max(0, self._inflight - 1)
                self._cv.notify_all()
            log.debug("ESP32: %s", line)
        elif line.startswith("PONG"):
            self._pong.set()
        elif line.startswith("S:"):
            self._last_status = line
        elif line.startswith("READY"):
            log.info("ESP32 açıldı (%s)", line)
        elif line.startswith("E:"):
            log.debug("ESP32 hata: %s", line)

    # ---------------- komutlar ----------------
    def send(self, cmd, cache=True):
        """Tek satırlık komut gönder. Bağlı değilse sessizce atlar."""
        key = cmd.split(":", 1)[0]
        if cache and key in ("LED", "VOL", "EYES"):
            self._state_cache[key] = cmd
        if not self.connected:
            return False
        try:
            with self._wlock:
                self.ser.write((cmd + "\n").encode("ascii", "ignore"))
            return True
        except Exception as e:
            self._drop(str(e))
            return False

    def ping(self, timeout=1.0):
        self._pong.clear()
        self.send("PING")
        return self._pong.wait(timeout)

    def status(self, timeout=1.0):
        self._last_status = ""
        self.send("STATUS")
        t = time.time() + timeout
        while time.time() < t and not self._last_status:
            time.sleep(0.02)
        return self._last_status

    def pan(self, deg):
        self.send(f"PAN:{deg:.1f}")

    def pan_speed(self, dps):
        self.send(f"PANSPEED:{int(dps)}")

    def eyes(self, mode):
        self.send(f"EYES:{mode}")

    def look(self, x, y=0):
        self.send(f"LOOK:{int(x)},{int(y)}")

    def led(self, r, g, b, br):
        self.send(f"LED:{int(r)},{int(g)},{int(b)},{int(br)}")

    def volume(self, v):
        self.send(f"VOL:{int(v)}")

    def beep(self, hz=880, ms=200):
        self.send(f"BEEP:{int(hz)},{int(ms)}")

    def stop_audio(self):
        self.send("AUDIO_STOP")

    def _est_free(self):
        """ESP32 tamponundaki tahmini boş yer: son bildirilen değer + o andan beri çalınan ses."""
        drained = (time.time() - self._free_t) * SAMPLE_RATE * 2
        return min(ESP_AUDIO_BUF, self._free + drained)

    def play_pcm(self, pcm: bytes, stop_event=None):
        """16 kHz 16 bit mono PCM'i ESP32'ye kredi tabanlı akış kontrolüyle akıt
        ve çalma bitene kadar bekle. Başarılıysa True döner."""
        if not self.connected:
            return False
        if len(pcm) % 2:
            pcm = pcm[:-1]
        pcm = prep_for_dac(pcm)
        pos = 0
        while pos < len(pcm):
            if stop_event is not None and stop_event.is_set():
                self.stop_audio()
                return True
            chunk = pcm[pos:pos + AUDIO_CHUNK]
            with self._cv:
                # En fazla 2 onaysız paket ve ESP32'de yer varsa gönder
                ok = self._cv.wait_for(
                    lambda: not self.connected or
                    (self._inflight < 2 and self._est_free() - self._inflight * AUDIO_CHUNK >= len(chunk) + 512),
                    timeout=0.05)
                if not self.connected:
                    return False
                if not ok:
                    # Onay 1 sn'den uzun gelmediyse kaybolmuştur: sayacı sıfırla
                    if self._inflight and time.time() - self._sent_t > 1.0:
                        self._inflight = 0
                    continue
                self._sent_t = time.time()
                self._inflight += 1
            header = f"AUDIO:{len(chunk)}:{sum(chunk) & 0xFFFF}\n".encode()
            try:
                with self._wlock:
                    self.ser.write(header + chunk)
            except Exception as e:
                self._drop(str(e))
                return False
            pos += len(chunk)
        # Tampondaki sesin bitmesini bekle
        with self._cv:
            self._cv.wait_for(lambda: self._inflight == 0 or not self.connected, timeout=1.0)
            remaining = max(0, ESP_AUDIO_BUF - self._est_free())
        end = time.time() + remaining / (SAMPLE_RATE * 2) + 0.15
        while time.time() < end:
            if stop_event is not None and stop_event.is_set():
                self.stop_audio()
                break
            time.sleep(0.02)
        return True

    def close(self):
        self._stop.set()
        self._drop("kapatılıyor")
