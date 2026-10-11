"""
Masaüstü Robot v1 - PC beyni
============================
Kamera ile yüz takibi, mikrofonla dinleme, Grok ile konuşma, robot hoparlöründen cevap.

Kullanım:
    python robot.py            normal çalıştırma
    python robot.py --test     donanım + API kontrolü
    python robot.py --yazi     mikrofon yerine klavyeden yazarak konuş (deneme için)
"""
import argparse
import logging
import os
import queue
import re
import sys
import threading
import time

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
log = logging.getLogger("robot")


def setup_logging():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(name)-8s %(message)s", datefmt="%H:%M:%S",
                        handlers=[logging.StreamHandler(sys.stdout),
                                  logging.FileHandler(os.path.join(HERE, "robot.log"), encoding="utf-8")])
    for noisy in ("httpx", "openai", "urllib3", "httpcore", "primp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def load_config():
    with open(os.path.join(HERE, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def tr_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


# ---------------- LED renkleri (durum göstergesi) ----------------
LED_STATES = {"idle": (0, 60, 160), "listen": (0, 200, 60), "think": (150, 0, 200),
              "speak": (0, 180, 200), "error": (255, 0, 0), "off": (0, 0, 0)}


def is_net_error(e):
    """İnternet/bağlantı kaynaklı hata mı? (telefon hotspot'u kopunca sık olur)"""
    import requests
    try:
        import openai
        if isinstance(e, (openai.APIConnectionError, openai.APITimeoutError)):
            return True
    except ImportError:
        pass
    if isinstance(e, requests.HTTPError):
        return False
    return isinstance(e, (requests.ConnectionError, requests.Timeout, OSError))


class Robot:
    def __init__(self, cfg, text_mode=False, link=None, on_event=None):
        from serial_link import SerialLink
        self.cfg = cfg
        self.text_mode = text_mode
        self.link = link or SerialLink(cfg["serial"].get("port", "auto"), int(cfg["serial"].get("baud", 921600)))
        self.speaking = threading.Event()
        self.listener = None
        self.tracker = None
        self.brain = None
        self.tts = None
        self.state = "off"
        self.on_event = on_event            # kontrol paneli için: on_event(tür, veri)
        self.stop_event = threading.Event()
        self._lock = threading.Lock()

    def _emit(self, kind, data):
        if self.on_event:
            try:
                self.on_event(kind, data)
            except Exception:
                pass

    def led(self, state):
        self.state = state
        self._emit("state", state)
        if self.cfg["leds"].get("enabled", True):
            r, g, b = LED_STATES[state]
            self.link.led(r, g, b, self.cfg["leds"].get("brightness", 12) if state != "off" else 0)

    def say(self, text, mood="idle"):
        """Metni seslendir; robot hoparlöründen ya da PC'den çal."""
        from audio_io import play_local
        spoken = re.sub(r"\[\[(mutlu|kizgin|kızgın|normal)\]\]", "", text, flags=re.I).strip()
        if not spoken:
            return
        print(f"\n  🤖 {self.cfg.get('robot_adi', 'Robot')}: {spoken}\n", flush=True)
        self._emit("robot", spoken)
        try:
            pcm = self.tts.synth(spoken)
        except Exception as e:
            log.error("Ses üretilemedi: %s", e)
            self._emit("error", "internet yok, sesli okunamadı" if is_net_error(e) else f"ses üretilemedi: {e}")
            return
        self.speaking.set()
        if self.listener:
            self.listener.mute()
        self.led("speak")
        self.link.eyes(mood if mood in ("happy", "angry") else "talk")
        try:
            out = self.cfg["voice"].get("output", "robot")
            if out == "robot" and self.link.connected:
                ok = self.link.play_pcm(pcm)
                if not ok:
                    play_local(pcm)
            else:
                play_local(pcm)
        finally:
            self.link.eyes("idle")
            self.led("idle")
            self.speaking.clear()
            if self.listener:
                self.listener.unmute(0.5)

    def should_answer(self, text):
        conv = self.cfg["conversation"]
        low = tr_lower(text)
        wake = any(w in low for w in conv.get("wake_words", []))
        if conv.get("require_wake_word", False) and not wake:
            return False
        if conv.get("only_when_face_visible", True) and not wake and not self.tracker.seen_recently(5):
            return False
        return len(low.strip(" .,!?")) >= 2

    def run(self):
        """Ana döngü. stop_event set edilince (panelden Durdur) temiz çıkar."""
        from brain import Brain
        from speech import STT, TTS, api_key
        from vision import Tracker

        if not api_key():
            log.error("XAI_API_KEY ortam değişkeni yok! KURULUM.md'deki 'API anahtarı' adımını yap.")
        self.brain, self.stt, self.tts = Brain(self.cfg), STT(self.cfg), TTS(self.cfg)
        self.tracker = Tracker(self.cfg, self.link)
        self.tracker.start()
        self.listener = None
        self.stop_event.clear()
        self.link.volume(self.cfg["voice"].get("robot_volume", 60))
        self.link.eyes("idle")
        self.led("idle")

        if self.text_mode:
            log.info("Yazı modu: mesajını yazıp Enter'a bas (çıkmak için Ctrl+C).")
            while True:
                text = input("Sen: ").strip()
                if text:
                    self.handle(text, force=True)

        try:
            from audio_io import Listener
            self.listener = Listener(self.cfg["audio_in"])
            self.listener.start()
            log.info("Hazırım! Konuşabilirsin. (Kapatmak için bu pencerede Ctrl+C)")
        except Exception as e:
            self.listener = None
            log.error("Mikrofon açılamadı (%s). Sadece yazarak konuşulabilir.", e)
        while not self.stop_event.is_set():
            if self.listener is None:
                self.stop_event.wait(0.5)
                continue
            try:
                pcm = self.listener.utterances.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._hear(pcm)
            except Exception as e:          # döngü asla ölmesin
                log.exception("Beklenmeyen hata: %s", e)
                self.led("idle")
        self.shutdown()

    def _hear(self, pcm):
        self.led("think")
        try:
            text = self.stt.transcribe(pcm)
        except Exception as e:
            log.error("Ses yazıya çevrilemedi: %s", "internet yok" if is_net_error(e) else e)
            self._emit("error", "internet yok" if is_net_error(e) else f"ses yazıya çevrilemedi: {e}")
            self.led("idle")
            return
        if not text:
            self.led("idle")
            return
        log.info("Duyulan: %s", text)
        self.handle(text)

    def handle(self, text, force=False, speak=True):
        with self._lock:
            if not force and not self.should_answer(text):
                log.info("(Cevap vermiyorum: kimse görünmüyor / isim söylenmedi)")
                self.led("idle")
                return
            self._emit("user", text)
            self.led("think")
            self.link.eyes("blink")
            hint = "Karşında şu an bir yüz görüyorsun." if self.tracker and self.tracker.face_visible else ""
            try:
                reply, mood = self.brain.reply(text, hint)
            except Exception as e:
                net = is_net_error(e)
                log.error("Grok cevap veremedi: %s", "internet yok" if net else e)
                self._emit("error", "internet yok" if net else f"Grok cevap veremedi: {e}")
                self.led("error")
                time.sleep(1)
                self.link.eyes("idle")
                self.led("idle")
                return
            if speak:
                self.say(reply, mood)
            else:
                spoken = re.sub(r"\[\[(mutlu|kizgin|kızgın|normal)\]\]", "", reply, flags=re.I).strip()
                self._emit("robot", spoken)
                self.link.eyes(mood if mood in ("happy", "angry") else "idle")
                self.led("idle")

    def stop(self):
        self.stop_event.set()

    def shutdown(self):
        """Dinlemeyi ve takibi kapat, kafayı ortala (seri bağlantı açık kalır)."""
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
        if self.tracker:
            self.tracker.stop_event.set()
        try:
            self.link.eyes("sleep")
            self.link.pan(0)
        except Exception:
            pass
        self.led("off")


# ---------------- TEST MODU ----------------
def run_tests(cfg):
    import numpy as np
    import requests
    import sounddevice as sd

    from audio_io import SR, beep_pcm, find_input_device, play_local
    from serial_link import SerialLink
    from speech import TTS, api_key
    from vision import FaceDetector, open_camera

    results = []

    def report(name, ok, detail=""):
        results.append((name, ok))
        print(f"  [{'TAMAM' if ok else 'HATA '}] {name}  {detail}", flush=True)

    print("\n=== Masaüstü Robot v1 - Test ===\n")

    # 1) API anahtarı
    key = api_key()
    if not key:
        report("API anahtarı (XAI_API_KEY)", False, "ortam değişkeni bulunamadı")
    else:
        try:
            r = requests.get(cfg["xai"]["base_url"].rstrip("/") + "/models",
                             headers={"Authorization": f"Bearer {key}"}, timeout=15)
            report("API anahtarı (XAI_API_KEY)", r.ok, f"HTTP {r.status_code}")
            v = requests.get(cfg["xai"]["base_url"].rstrip("/") + "/tts/voices",
                             headers={"Authorization": f"Bearer {key}"}, timeout=15)
            if v.ok:
                names = [x.get("voice_id") for x in v.json().get("voices", [])]
                print(f"         xAI sesleri: {', '.join(n for n in names if n)}")
        except Exception as e:
            report("API anahtarı (XAI_API_KEY)", False, str(e))

    # 2) Kamera + yüz bulucu
    cap, idx = open_camera(cfg["camera"])
    if cap is None:
        report("Kamera", False, f"index {idx} açılamadı")
    else:
        ok, frame = False, None
        for _ in range(10):
            ok, frame = cap.read()
            if ok:
                break
            time.sleep(0.1)
        report("Kamera", ok, f"index {idx}, {frame.shape[1]}x{frame.shape[0]}" if ok else "görüntü yok")
        if ok:
            det = FaceDetector(cfg["tracking"].get("detector", "mediapipe"))
            face = det.detect(frame)
            print(f"         Yüz bulucu: {det.kind}, şu an yüz {'VAR' if face else 'yok'}")
        cap.release()

    # 3) Mikrofon
    try:
        dev = find_input_device(cfg["audio_in"].get("name_hint", "C270"), cfg["audio_in"].get("device", "auto"))
        name = sd.query_devices(dev, "input")["name"] if dev is not None else "varsayılan"
        print("         Mikrofon 2 saniye dinleniyor, bir şey söyle...")
        rec = sd.rec(int(2 * SR), samplerate=SR, channels=1, dtype="int16", device=dev)
        sd.wait()
        lvl = int(np.abs(rec).mean())
        report("Mikrofon", lvl > 20, f"{name}, ortalama seviye {lvl}" + ("" if lvl > 20 else " (çok düşük/sessiz)"))
    except Exception as e:
        report("Mikrofon", False, str(e))

    # 4) Seri bağlantı + servo + göz + LED + hoparlör
    link = SerialLink(cfg["serial"].get("port", "auto"), int(cfg["serial"].get("baud", 921600)))
    t0 = time.time()
    while not link.connected and time.time() - t0 < 12:
        time.sleep(0.2)
    report("ESP32 seri bağlantı", link.connected and link.ping(), link.port_name or "bulunamadı")
    if link.connected:
        print("         Servo taraması: orta -> sol -> sağ -> orta (kafa sürtmemeli)")
        link.pan_speed(60)
        for a in (0, -90, 90, 0):
            link.pan(a)
            time.sleep(3.2)
        print(f"         {link.status()}")
        report("Servo taraması", True, "gözle kontrol et: + açıda kafa hangi yöne döndü?")
        for m in ("happy", "angry", "look_left", "look_right", "blink", "sleep", "idle"):
            link.eyes(m)
            print(f"         Göz: {m}")
            time.sleep(1.2)
        link.look(0, 0)
        report("Göz ekranı", True, "gözle kontrol et")
        for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 60, 160)):
            link.led(*c, 15)
            time.sleep(0.5)
        report("LED çubuğu", True, "gözle kontrol et")
        link.volume(cfg["voice"].get("robot_volume", 60))
        ok = link.play_pcm(beep_pcm(660, 250) + bytes(3200) + beep_pcm(880, 250))
        report("Robot hoparlörü (bip)", ok, "iki bip duymalısın")

    # 5) Konuşma sesi
    if key:
        try:
            pcm = TTS(cfg).synth("Selam kanka, ben Şakir. Test tamam.")
            if cfg["voice"].get("output") == "robot" and link.connected:
                link.play_pcm(pcm)
            else:
                play_local(pcm)
            report("Ses üretme (TTS)", len(pcm) > 1000, f"{len(pcm) / 32000:.1f} sn ses")
        except Exception as e:
            report("Ses üretme (TTS)", False, str(e))
    else:
        play_local(beep_pcm())

    link.close()
    bad = [n for n, ok in results if not ok]
    print("\n=== Sonuç: " + ("hepsi TAMAM ===" if not bad else f"{len(bad)} sorun var: {', '.join(bad)} ===") + "\n")


def main():
    ap = argparse.ArgumentParser(description="Masaüstü Robot v1")
    ap.add_argument("--test", action="store_true", help="donanım ve API testi")
    ap.add_argument("--yazi", action="store_true", help="mikrofon yerine klavyeden yaz")
    args = ap.parse_args()
    setup_logging()
    cfg = load_config()
    if args.test:
        run_tests(cfg)
        return
    robot = Robot(cfg, text_mode=args.yazi)
    try:
        robot.run()
    except KeyboardInterrupt:
        log.info("Kapatılıyor... Görüşürüz kanka.")
        robot.link.eyes("sleep")
        robot.led("off")
        robot.link.pan(0)
        time.sleep(0.3)


if __name__ == "__main__":
    main()
