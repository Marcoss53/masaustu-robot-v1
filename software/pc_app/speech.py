"""Sesi yazıya çevirme (xAI STT) ve yazıyı sese çevirme (xAI TTS veya edge-tts)."""
import asyncio
import logging
import os
import re
import time

import requests

from audio_io import pcm_to_wav

log = logging.getLogger("konusma")


def api_key():
    return os.environ.get("XAI_API_KEY", "").strip()


def _post_with_retry(url, retries=3, timeout=30, **kw):
    r = None
    for i in range(retries):
        try:
            r = requests.post(url, timeout=timeout, **kw)
        except requests.RequestException as e:
            if i == retries - 1:
                raise
            log.warning("Ağ hatası (%s), tekrar deneniyor...", e)
            time.sleep(1 + i)
            continue
        if r.status_code in (429, 500, 502, 503) and i < retries - 1:
            time.sleep(1.5 * (i + 1))
            continue
        return r
    return r


class STT:
    """xAI Speech to Text (REST): POST {base}/stt, multipart file + model + language."""

    def __init__(self, cfg):
        self.base = cfg["xai"]["base_url"].rstrip("/")
        self.model = cfg["xai"].get("stt_model", "grok-voice-transcribe-2.0")
        self.lang = cfg["xai"].get("language", "tr")
        self.keyterms = [w for w in cfg["conversation"].get("wake_words", [])][:20]

    def transcribe(self, pcm: bytes) -> str:
        wav = pcm_to_wav(pcm)
        headers = {"Authorization": f"Bearer {api_key()}"}
        data = [("model", self.model), ("language", self.lang)] + [("keyterm", k) for k in self.keyterms]
        r = _post_with_retry(f"{self.base}/stt", headers=headers, data=data,
                             files={"file": ("ses.wav", wav, "audio/wav")})
        if r.status_code == 400:      # dil/anahtar kelime kabul edilmezse sade dene
            log.debug("STT 400: %s, sade istekle tekrar.", r.text[:200])
            r = _post_with_retry(f"{self.base}/stt", headers=headers, data={"model": self.model},
                                 files={"file": ("ses.wav", wav, "audio/wav")})
        r.raise_for_status()
        return (r.json().get("text") or "").strip()


def clean_for_speech(text, keep_tags=True):
    """Sesli okumaya uygun hale getir: link, markdown, kaynak numaraları vs. temizle."""
    t = re.sub(r"\[\[(mutlu|kizgin|kızgın|normal)\]\]", "", text, flags=re.I)
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\[\d+\]", "", t)                       # [1] gibi kaynak işaretleri
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)      # markdown link
    t = re.sub(r"[*_#`>|]", "", t)
    if not keep_tags:
        t = re.sub(r"\[[a-z\- ]+\]", "", t)             # [laugh] gibi ses etiketleri
        t = re.sub(r"</?[a-z\-]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


class TTS:
    """Çıktı her zaman 16 kHz 16 bit mono PCM (ESP32 ile aynı format)."""

    def __init__(self, cfg):
        self.base = cfg["xai"]["base_url"].rstrip("/")
        self.v = cfg["voice"]
        self.lang = cfg["xai"].get("language", "tr")

    def synth(self, text: str) -> bytes:
        engine = self.v.get("tts_engine", "xai")
        if engine == "xai":
            try:
                return self._xai(clean_for_speech(text, keep_tags=True))
            except Exception as e:
                log.warning("xAI TTS başarısız (%s), edge-tts ile deneniyor.", e)
        return self._edge(clean_for_speech(text, keep_tags=False))

    def _xai(self, text):
        body = {
            "text": text,
            "voice_id": self.v.get("xai_voice", "rex"),
            "language": self.lang,
            "speed": float(self.v.get("speed", 1.0)),
            "output_format": {"codec": "pcm", "sample_rate": 16000},
        }
        r = _post_with_retry(f"{self.base}/tts", json=body, timeout=60,
                             headers={"Authorization": f"Bearer {api_key()}"})
        r.raise_for_status()
        pcm = r.content
        if pcm[:4] == b"RIFF":            # beklenmedik şekilde WAV gelirse başlığı at
            pcm = pcm[44:]
        return pcm[: len(pcm) // 2 * 2]

    def _edge(self, text):
        import edge_tts
        import miniaudio

        async def run():
            rate = int(round((float(self.v.get("speed", 1.0)) - 1) * 100))
            com = edge_tts.Communicate(text, self.v.get("edge_voice", "tr-TR-AhmetNeural"),
                                       rate=f"{rate:+d}%")
            mp3 = bytearray()
            async for chunk in com.stream():
                if chunk["type"] == "audio":
                    mp3.extend(chunk["data"])
            return bytes(mp3)

        mp3 = asyncio.run(run())
        dec = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16,
                               nchannels=1, sample_rate=16000)
        return dec.samples.tobytes()
