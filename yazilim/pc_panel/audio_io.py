"""Mikrofon dinleme (VAD ile konuşma algılama) ve bilgisayar hoparlöründen çalma."""
import collections
import io
import logging
import queue
import threading
import time
import wave

import numpy as np
import sounddevice as sd

log = logging.getLogger("ses")

SR = 16000
FRAME_MS = 30
FRAME_SAMPLES = SR * FRAME_MS // 1000      # 480


def find_input_device(name_hint="C270", setting="auto"):
    if str(setting).lower() != "auto":
        try:
            return int(setting)
        except ValueError:
            name_hint = str(setting)
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0 and name_hint.lower() in d["name"].lower():
                return i
    except Exception as e:
        log.debug("Ses cihazları listelenemedi: %s", e)
    return None        # None = Windows varsayılan mikrofonu


def pcm_to_wav(pcm: bytes, sr=SR) -> bytes:
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)
    return bio.getvalue()


def play_local(pcm: bytes, sr=SR, stop_event=None):
    """PCM'i bilgisayarın varsayılan hoparlöründen çal (bitene kadar bekler)."""
    data = np.frombuffer(pcm, dtype=np.int16)
    if data.size == 0:
        return
    sd.play(data, sr)
    end = time.time() + data.size / sr + 0.1
    while time.time() < end:
        if stop_event is not None and stop_event.is_set():
            sd.stop()
            return
        time.sleep(0.02)
    sd.wait()


def beep_pcm(hz=880, ms=250, amp=8000):
    t = np.arange(int(SR * ms / 1000)) / SR
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.int16).tobytes()


class Listener:
    """Mikrofonu sürekli dinler; bir konuşma bitince PCM'i kuyruğa koyar.
    Robot konuşurken (muted) gelen sesler yok sayılır (kendi sesini duymasın)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.utterances = queue.Queue()
        self.muted = threading.Event()
        self._unmute_at = 0.0
        self._stream = None
        self._native_sr = SR
        self._resample_buf = np.zeros(0, dtype=np.float32)
        self._frames = queue.Queue(maxsize=500)
        self.vad = None
        try:
            import webrtcvad
            self.vad = webrtcvad.Vad(int(cfg.get("vad_aggressiveness", 2)))
            log.info("Konuşma algılama: webrtcvad")
        except Exception as e:
            log.warning("webrtcvad yüklenemedi (%s), basit ses eşiği kullanılacak.", e)
        self.level = 0

    def mute(self):
        self.muted.set()

    def unmute(self, delay=0.4):
        self._unmute_at = time.time() + delay
        self.muted.clear()

    def start(self):
        dev = find_input_device(self.cfg.get("name_hint", "C270"), self.cfg.get("device", "auto"))
        name = sd.query_devices(dev, "input")["name"] if dev is not None else "varsayılan mikrofon"
        try:
            self._stream = sd.InputStream(device=dev, channels=1, samplerate=SR, dtype="int16",
                                          blocksize=FRAME_SAMPLES, callback=self._cb)
            self._native_sr = SR
        except Exception:
            # Cihaz 16 kHz desteklemiyorsa kendi hızında aç, yazılımda 16 kHz'e çevir
            self._native_sr = int(sd.query_devices(dev, "input")["default_samplerate"])
            self._stream = sd.InputStream(device=dev, channels=1, samplerate=self._native_sr,
                                          dtype="int16", callback=self._cb)
        self._stream.start()
        log.info("Mikrofon açıldı: %s (%d Hz)", name, self._native_sr)
        threading.Thread(target=self._segmenter, daemon=True, name="dinleyici").start()

    def _cb(self, indata, frames, time_info, status):
        x = indata[:, 0]
        if self._native_sr != SR:     # basit doğrusal yeniden örnekleme
            x = x.astype(np.float32)
            n_out = int(len(x) * SR / self._native_sr)
            x = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x)
            self._resample_buf = np.concatenate([self._resample_buf, x])
            while len(self._resample_buf) >= FRAME_SAMPLES:
                fr = self._resample_buf[:FRAME_SAMPLES].astype(np.int16)
                self._resample_buf = self._resample_buf[FRAME_SAMPLES:]
                self._put(fr)
        else:
            self._put(x.copy())

    def _put(self, fr):
        try:
            self._frames.put_nowait(fr)
        except queue.Full:
            pass

    def _is_speech(self, fr):
        self.level = int(np.abs(fr).mean())
        if self.vad is not None:
            try:
                return self.vad.is_speech(fr.tobytes(), SR)
            except Exception:
                pass
        return self.level > self.cfg.get("energy_threshold", 500)

    def _segmenter(self):
        pre = collections.deque(maxlen=10)        # konuşma başlamadan önceki 300 ms
        ring = collections.deque(maxlen=10)
        voiced = []
        in_speech = False
        silence = 0
        end_frames = int(self.cfg.get("silence_end_ms", 800) / FRAME_MS)
        min_frames = int(self.cfg.get("min_speech_ms", 500) / FRAME_MS)
        max_frames = int(self.cfg.get("max_speech_s", 15) * 1000 / FRAME_MS)
        while True:
            fr = self._frames.get()
            if self.muted.is_set() or time.time() < self._unmute_at:
                in_speech, voiced, silence = False, [], 0
                pre.clear()
                ring.clear()
                continue
            sp = self._is_speech(fr)
            if not in_speech:
                pre.append(fr)
                ring.append(sp)
                if sum(ring) >= 6:                 # son 10 karenin 6'sı konuşma -> başladı
                    in_speech, voiced, silence = True, list(pre), 0
                    ring.clear()
            else:
                voiced.append(fr)
                silence = 0 if sp else silence + 1
                if silence >= end_frames or len(voiced) >= max_frames:
                    if len(voiced) - silence >= min_frames:
                        pcm = np.concatenate(voiced).astype(np.int16).tobytes()
                        self.utterances.put(pcm)
                    in_speech, voiced, silence = False, [], 0
                    pre.clear()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
