"""Grok (xAI) ile sohbet: karakter, kısa hafıza, kalıcı notlar ve internet araçları."""
import collections
import datetime
import json
import logging
import os
import re

import requests
import openai
from openai import OpenAI

log = logging.getLogger("beyin")

# ---------------- Araçlar (function calling) ----------------
WMO = {0: "açık", 1: "az bulutlu", 2: "parçalı bulutlu", 3: "kapalı", 45: "sisli", 48: "kırağılı sis",
       51: "hafif çisenti", 53: "çisenti", 55: "yoğun çisenti", 61: "hafif yağmurlu", 63: "yağmurlu",
       65: "şiddetli yağmurlu", 71: "hafif karlı", 73: "karlı", 75: "yoğun karlı", 80: "sağanak",
       81: "kuvvetli sağanak", 82: "çok şiddetli sağanak", 95: "gök gürültülü fırtına",
       96: "dolu ile fırtına", 99: "şiddetli dolu ile fırtına"}


def tool_weather(sehir="İstanbul"):
    g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": sehir, "count": 1, "language": "tr"}, timeout=10).json()
    if not g.get("results"):
        return {"hata": f"{sehir} bulunamadı"}
    loc = g["results"][0]
    w = requests.get("https://api.open-meteo.com/v1/forecast", params={
        "latitude": loc["latitude"], "longitude": loc["longitude"], "timezone": "auto",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
        "forecast_days": 3}, timeout=10).json()
    cur, d = w.get("current", {}), w.get("daily", {})
    return {
        "yer": f'{loc.get("name")}, {loc.get("country", "")}',
        "simdi": {"sicaklik_C": cur.get("temperature_2m"), "hissedilen_C": cur.get("apparent_temperature"),
                  "durum": WMO.get(cur.get("weather_code"), cur.get("weather_code")),
                  "ruzgar_kmh": cur.get("wind_speed_10m"), "nem_yuzde": cur.get("relative_humidity_2m")},
        "gunler": [{"tarih": d["time"][i], "max": d["temperature_2m_max"][i], "min": d["temperature_2m_min"][i],
                    "yagis_ihtimali": d["precipitation_probability_max"][i],
                    "durum": WMO.get(d["weather_code"][i], d["weather_code"][i])}
                   for i in range(len(d.get("time", [])))],
    }


def tool_currency(baz="USD", hedef="TRY"):
    r = requests.get(f"https://open.er-api.com/v6/latest/{baz.upper()}", timeout=10).json()
    if r.get("result") != "success":
        return {"hata": "kur alınamadı"}
    rate = r["rates"].get(hedef.upper())
    return {"baz": baz.upper(), "hedef": hedef.upper(), "kur": rate, "guncelleme": r.get("time_last_update_utc")}


def tool_ddg(sorgu):
    try:
        from ddgs import DDGS
    except ImportError:
        return {"hata": "ddgs paketi kurulu değil"}
    with DDGS() as d:
        res = list(d.text(sorgu, region="tr-tr", max_results=5))
    return [{"baslik": x.get("title"), "ozet": x.get("body")} for x in res]


class Brain:
    def __init__(self, cfg):
        self.cfg = cfg
        x = cfg["xai"]
        self.client = OpenAI(api_key=os.environ.get("XAI_API_KEY", "yok"), base_url=x["base_url"],
                             timeout=30, max_retries=1)   # internet kopunca uzun takılmasın
        self.model = x["model"]
        self.search_mode = x.get("web_search", "xai")
        self.history = collections.deque(maxlen=int(cfg["conversation"].get("memory_turns", 8)) * 2)
        self.notes_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       cfg["conversation"].get("notes_file", "notlar.txt"))
        self.use_responses = True

    # ---- kalıcı notlar ----
    def _notes(self):
        try:
            with open(self.notes_path, encoding="utf-8") as f:
                return f.read()[-3000:]
        except FileNotFoundError:
            return ""

    def tool_note(self, not_metni):
        with open(self.notes_path, "a", encoding="utf-8") as f:
            f.write(f"- {datetime.date.today().isoformat()}: {not_metni.strip()}\n")
        return {"durum": "kaydedildi"}

    def _tool_defs(self):
        defs = [
            ("hava_durumu", "Bir şehrin güncel hava durumu ve 3 günlük tahmini.",
             {"sehir": {"type": "string", "description": "Şehir adı, örn. İstanbul"}}, ["sehir"]),
            ("doviz_kuru", "Güncel döviz kuru. Örn. baz=USD hedef=TRY.",
             {"baz": {"type": "string"}, "hedef": {"type": "string"}}, ["baz", "hedef"]),
            ("not_al", "Kalıcı hafızaya not yaz (biri 'bunu unutma' derse ya da önemli bir bilgi verirse).",
             {"not_metni": {"type": "string"}}, ["not_metni"]),
        ]
        if self.search_mode == "ddg" or (self.search_mode == "xai" and not self.use_responses):
            defs.append(("web_ara", "İnternette arama yap (haber, maç sonucu, güncel olaylar).",
                         {"sorgu": {"type": "string"}}, ["sorgu"]))
        return [{"name": n, "description": d,
                 "parameters": {"type": "object", "properties": p, "required": r}} for n, d, p, r in defs]

    def _run_tool(self, name, args):
        log.info("Araç kullanılıyor: %s %s", name, args)
        try:
            if name == "hava_durumu":
                out = tool_weather(args.get("sehir", "İstanbul"))
            elif name == "doviz_kuru":
                out = tool_currency(args.get("baz", "USD"), args.get("hedef", "TRY"))
            elif name == "not_al":
                out = self.tool_note(args.get("not_metni", ""))
            elif name == "web_ara":
                out = tool_ddg(args.get("sorgu", ""))
            else:
                out = {"hata": "bilinmeyen araç"}
        except Exception as e:
            out = {"hata": str(e)}
        return json.dumps(out, ensure_ascii=False)[:4000]

    def _system(self, speaker_hint=""):
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M, %A")
        s = self.cfg["persona"].strip() + f"\n\nŞu an: {now} (Türkiye saati)."
        notes = self._notes()
        if notes:
            s += "\n\nKalıcı notların (hatırladığın şeyler):\n" + notes
        if speaker_hint:
            s += "\n\n" + speaker_hint
        return s

    # ---- ana fonksiyon ----
    def reply(self, user_text, speaker_hint=""):
        """Kullanıcının sözüne cevap üret. (metin, ruh_hali) döner."""
        msgs = [{"role": "system", "content": self._system(speaker_hint)}] + list(self.history) + \
               [{"role": "user", "content": user_text}]
        text = None
        if self.use_responses:
            try:
                text = self._reply_responses(msgs)
            except (openai.BadRequestError, openai.NotFoundError, openai.UnprocessableEntityError) as e:
                log.warning("Responses API hatası (%s). Chat Completions'a geçiliyor.", e)
                self.use_responses = False
        if text is None:
            text = self._reply_chat(msgs)
        text = (text or "").strip() or "[[normal]] Bir şey diyecektim, unuttum lan."
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": text})
        m = re.search(r"\[\[(mutlu|kizgin|kızgın|normal)\]\]", text, re.I)
        mood = {"mutlu": "happy", "kizgin": "angry", "kızgın": "angry"}.get(m.group(1).lower(), "idle") if m else "idle"
        return text, mood

    def _reply_responses(self, msgs):
        """xAI Responses API: sunucu tarafı web_search + kendi fonksiyon araçlarımız."""
        x = self.cfg["xai"]
        tools = [dict(type="function", **t) for t in self._tool_defs()]
        if self.search_mode == "xai":
            tools.insert(0, {"type": "web_search"})
        inp = list(msgs)
        for _ in range(4):
            resp = self.client.responses.create(model=self.model, input=inp, tools=tools,
                                                max_output_tokens=int(x.get("max_output_tokens", 300)),
                                                temperature=float(x.get("temperature", 0.9)))
            calls = [o for o in (resp.output or []) if getattr(o, "type", "") == "function_call"]
            if not calls:
                return resp.output_text
            for c in calls:
                try:
                    args = json.loads(c.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                inp.append({"type": "function_call", "call_id": c.call_id, "name": c.name,
                            "arguments": c.arguments or "{}"})
                inp.append({"type": "function_call_output", "call_id": c.call_id,
                            "output": self._run_tool(c.name, args)})
        return resp.output_text

    def _reply_chat(self, msgs):
        """Yedek: OpenAI uyumlu Chat Completions (web araması ddg aracıyla)."""
        x = self.cfg["xai"]
        tools = [{"type": "function", "function": t} for t in self._tool_defs()]
        msgs = list(msgs)
        for _ in range(4):
            r = self.client.chat.completions.create(model=self.model, messages=msgs, tools=tools,
                                                    max_tokens=int(x.get("max_output_tokens", 300)),
                                                    temperature=float(x.get("temperature", 0.9)))
            m = r.choices[0].message
            if not m.tool_calls:
                return m.content
            msgs.append({"role": "assistant", "content": m.content or "",
                         "tool_calls": [tc.model_dump() for tc in m.tool_calls]})
            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                msgs.append({"role": "tool", "tool_call_id": tc.id,
                             "content": self._run_tool(tc.function.name, args)})
        return m.content
