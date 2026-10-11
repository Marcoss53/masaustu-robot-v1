"""
Masaüstü Robot v1 - Kontrol paneli
==================================
robot.py'deki Robot sınıfını arka planda çalıştırır; durum, kişilik, hafıza,
sohbet ve donanım testi tek pencerede.

Açmak için: panel_baslat.bat (çift tıkla).   python panel.py --oto  -> açılınca robotu da başlatır
"""
import datetime
import logging
import os
import queue
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
if sys.stdout is None:              # pythonw: konsol yok, print'ler kaybolsun
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")



def _fatal(err):
    """pythonw'da konsol yok: hatayı dosyaya yaz ve pencereyle göster."""
    with open(os.path.join(HERE, "panel_hata.txt"), "w", encoding="utf-8") as f:
        f.write(err)
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        r = _tk.Tk()
        r.withdraw()
        _mb.showerror("Panel açılamadı", err[-1500:] + "\n\n(panel_hata.txt dosyasına da yazıldı)")
    except Exception:
        pass


try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox

    from robot import LED_STATES, Robot, load_config
except Exception:
    import traceback
    _fatal(traceback.format_exc() + "\nPaketler eksik olabilir: pc_panel\\.venv klasörünü silip panel_baslat.bat'ı tekrar çalıştır.")
    sys.exit(1)

log = logging.getLogger("panel")

STATE_TR = {"idle": ("Dinliyor", "#3b82f6"), "listen": ("Dinliyor", "#22c55e"),
            "think": ("Düşünüyor", "#a855f7"), "speak": ("Konuşuyor", "#06b6d4"),
            "error": ("Hata", "#ef4444"), "off": ("Kapalı", "#6b7280")}
GREEN, RED, YELLOW, GRAY = "#22c55e", "#ef4444", "#eab308", "#6b7280"
XAI_VOICES = ["rex", "eve", "ara", "leo", "sal"]
EDGE_VOICES = ["tr-TR-AhmetNeural", "tr-TR-EmelNeural"]
MODELS = ["grok-4.20-0309-non-reasoning", "grok-4.7"]
EYES = [("Normal", "idle"), ("Mutlu", "happy"), ("Kızgın", "angry"), ("Kırp", "blink"),
        ("Konuş", "talk"), ("Sola bak", "look_left"), ("Sağa bak", "look_right"), ("Uyku", "sleep")]
COLORS = [("Kırmızı", (255, 0, 0)), ("Yeşil", (0, 255, 0)), ("Mavi", (0, 60, 255)), ("Mor", (150, 0, 200)),
          ("Turkuaz", (0, 180, 200)), ("Beyaz", (255, 255, 255)), ("Kapalı", (0, 0, 0))]
STARTUP_DIR = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
STARTUP_FILE = os.path.join(STARTUP_DIR, "Masaustu Robot Panel.vbs")
OLD_STARTUP_FILE = os.path.join(STARTUP_DIR, "Masaustu Robot.bat")


# ---------------- yardımcılar ----------------
def setup_logging(gui_queue):
    class GuiHandler(logging.Handler):
        last = None

        def emit(self, rec):
            msg = self.format(rec)
            if rec.getMessage() != self.last:       # aynı uyarı arka arkaya yağmasın
                self.last = rec.getMessage()
                gui_queue.put(("log", msg))

    fmt = logging.Formatter("%(asctime)s  %(name)-8s %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(os.path.join(HERE, "robot.log"), encoding="utf-8")
    gh = GuiHandler()
    for h in (fh, gh):
        h.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[fh, gh])
    for noisy in ("httpx", "openai", "urllib3", "httpcore", "primp", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def save_config(updates):
    """config.yaml'da sadece verilen anahtarları değiştir; yorumlar ve diğer ayarlar korunur.
    updates: {("xai", "model"): "grok-4.7", ...}"""
    from ruamel.yaml import YAML
    from ruamel.yaml.scalarstring import LiteralScalarString
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    path = os.path.join(HERE, "config.yaml")
    with open(path, encoding="utf-8") as f:
        data = y.load(f)
    for keys, val in updates.items():
        d = data
        for k in keys[:-1]:
            d = d[k]
        if isinstance(val, str) and "\n" in val:
            val = LiteralScalarString(val.rstrip() + "\n")
        d[keys[-1]] = val
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        y.dump(data, f)
    os.replace(tmp, path)


def set_cfg(cfg, updates):
    """Çalışan robotun ayar sözlüğünü yerinde güncelle (yeniden başlatmadan geçerli olsun)."""
    for keys, val in updates.items():
        d = cfg
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = val


def api_key():
    return os.environ.get("XAI_API_KEY", "").strip()


def bg(fn, *a):
    threading.Thread(target=fn, args=a, daemon=True).start()


# ---------------- panel ----------------
class Panel(ctk.CTk):
    def __init__(self, auto_start=False):
        super().__init__()
        self.title("Masaüstü Robot - Kontrol Paneli")
        self.geometry("900x680")
        self.minsize(780, 560)
        self.ev = queue.Queue()
        setup_logging(self.ev)
        self.cfg = load_config()
        from serial_link import SerialLink
        self.link = SerialLink(self.cfg["serial"].get("port", "auto"), int(self.cfg["serial"].get("baud", 921600)))
        self.robot = None
        self.robot_thread = None
        self.net = ("?", GRAY)
        self.mic_name = None
        self._net_kick = threading.Event()
        self._notes_mtime = None
        self._vol_job = None
        self._preview_t = 0

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabs = tabs
        for name in ("Durum", "Kişilik", "Hafıza", "Sohbet", "Test"):
            tabs.add(name)
        self._build_status(tabs.tab("Durum"))
        self._build_persona(tabs.tab("Kişilik"))
        self._build_memory(tabs.tab("Hafıza"))
        self._build_chat(tabs.tab("Sohbet"))
        self._build_test(tabs.tab("Test"))

        bg(self._net_loop)
        bg(self._mic_loop)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._poll)
        if auto_start:
            self.after(1500, self.start_robot)
        log.info("Panel açıldı.")

    # ======== 1) Durum ========
    def _build_status(self, t):
        top = ctk.CTkFrame(t, fg_color="transparent")
        top.pack(fill="x", pady=(5, 10))
        self.btn_run = ctk.CTkButton(top, text="▶  Robotu Başlat", width=200, height=44,
                                     font=ctk.CTkFont(size=16, weight="bold"), command=self.toggle_robot)
        self.btn_run.pack(side="left", padx=5)
        self.lbl_state = ctk.CTkLabel(top, text="Kapalı", font=ctk.CTkFont(size=22, weight="bold"),
                                      text_color=GRAY)
        self.lbl_state.pack(side="left", padx=25)

        mid = ctk.CTkFrame(t, fg_color="transparent")
        mid.pack(fill="x")
        grid = ctk.CTkFrame(mid)
        grid.pack(side="left", fill="y", padx=5)
        self.st = {}
        for i, (key, name) in enumerate((("esp", "Robot (ESP32)"), ("cam", "Kamera"),
                                         ("mic", "Mikrofon"), ("net", "İnternet / Grok API"))):
            ctk.CTkLabel(grid, text=name, anchor="w", width=150).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            lbl = ctk.CTkLabel(grid, text="●  ?", anchor="w", width=230, text_color=GRAY)
            lbl.grid(row=i, column=1, padx=10, pady=8, sticky="w")
            self.st[key] = lbl
        self.auto_var = tk.BooleanVar(value=os.path.exists(STARTUP_FILE))
        ctk.CTkSwitch(grid, text="Windows açılınca paneli başlat", variable=self.auto_var,
                      command=self.toggle_autostart).grid(row=4, column=0, columnspan=2, padx=10, pady=(14, 8),
                                                          sticky="w")
        self.preview = ctk.CTkLabel(mid, text="Kamera önizlemesi\n(robot çalışınca)", width=320, height=240,
                                    fg_color="#1f1f1f", corner_radius=8)
        self.preview.pack(side="right", padx=5)

        ctk.CTkLabel(t, text="Olaylar", anchor="w").pack(fill="x", padx=5, pady=(10, 0))
        self.logbox = ctk.CTkTextbox(t, height=150, font=ctk.CTkFont(family="Consolas", size=12))
        self.logbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.logbox.configure(state="disabled")

    def robot_running(self):
        return self.robot_thread is not None and self.robot_thread.is_alive()

    def toggle_robot(self):
        if self.robot_running():
            self.btn_run.configure(state="disabled", text="Durduruluyor...")
            self.robot.stop()
        else:
            self.start_robot()

    def start_robot(self):
        if self.robot_running():
            return
        self.robot = Robot(self.cfg, link=self.link, on_event=lambda k, d: self.ev.put((k, d)))

        def run():
            try:
                self.robot.run()
            except Exception as e:
                log.exception("Robot durdu: %s", e)
                self.ev.put(("error", f"robot durdu: {e}"))
            finally:
                self.ev.put(("stopped", None))

        self.robot_thread = threading.Thread(target=run, daemon=True, name="robot")
        self.robot_thread.start()
        self.btn_run.configure(text="■  Robotu Durdur", fg_color="#b91c1c", hover_color="#991b1b")
        self._set_state("idle")

    def _set_state(self, s):
        txt, col = STATE_TR.get(s, (s, GRAY))
        if s == "idle" and self.robot and self.robot_running() and self.robot.listener is None:
            txt = "Hazır (yazı)"
        self.lbl_state.configure(text=txt, text_color=col)

    def _dot(self, key, text, color):
        self.st[key].configure(text=f"●  {text}", text_color=color)

    def _update_status(self):
        if self.link.connected:
            self._dot("esp", f"Bağlı ({self.link.port_name})", GREEN)
        else:
            self._dot("esp", "Bulunamadı, aranıyor...", RED)
        r = self.robot if self.robot_running() else None
        tr = r.tracker if r else None
        if tr is None:
            self._dot("cam", "Kapalı (robot durduruldu)", GRAY)
        elif time.time() - tr.last_frame_t < 3:
            self._dot("cam", "Açık" + (" - yüz var" if tr.face_visible else ""), GREEN)
        else:
            self._dot("cam", "Açılamadı / bekleniyor", YELLOW)
        if r and r.listener:
            self._dot("mic", f"Dinliyor (seviye {r.listener.level})", GREEN)
        elif r:
            self._dot("mic", "Açılamadı (sadece yazı)", RED)
        elif self.mic_name:
            self._dot("mic", self.mic_name[:32], GRAY)
        else:
            self._dot("mic", "?", GRAY)
        self._dot("net", *self.net)

    def _update_preview(self):
        r = self.robot if self.robot_running() else None
        tr = r.tracker if r else None
        if tr is None or tr.last_frame is None or time.time() - tr.last_frame_t > 3 \
                or self.tabs.get() != "Durum":
            return
        if tr.last_frame_t == self._preview_t:
            return
        self._preview_t = tr.last_frame_t
        try:
            import cv2
            from PIL import Image
            frame, box = tr.last_frame, tr.last_box
            h, w = frame.shape[:2]
            img = cv2.resize(frame, (320, int(320 * h / w)))
            if box:
                ih, iw = img.shape[:2]
                x, y, bw, bh = box
                cv2.rectangle(img, (int(x * iw), int(y * ih)), (int((x + bw) * iw), int((y + bh) * ih)),
                              (0, 255, 0), 2)
            pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            self._preview_img = ctk.CTkImage(pil, size=pil.size)
            self.preview.configure(image=self._preview_img, text="")
        except Exception as e:
            log.debug("Önizleme hatası: %s", e)

    def _net_loop(self):
        import requests
        while True:
            base = self.cfg["xai"]["base_url"].rstrip("/")
            key = api_key()
            try:
                if key:
                    r = requests.get(base + "/models", headers={"Authorization": f"Bearer {key}"}, timeout=8)
                    if r.ok:
                        self.net = ("Bağlı", GREEN)
                    elif r.status_code in (400, 401, 403):
                        self.net = ("API anahtarı hatalı", RED)
                    else:
                        self.net = (f"API hatası (HTTP {r.status_code})", YELLOW)
                else:
                    requests.head("https://api.x.ai", timeout=8)
                    self.net = ("İnternet var, API anahtarı yok", YELLOW)
            except Exception:
                self.net = ("İnternet yok", RED)
            ok = self.net[1] == GREEN
            self._net_kick.wait(120 if ok else 10)      # bağlıyken seyrek kontrol (kota dostu)
            self._net_kick.clear()

    def _mic_loop(self):
        while True:
            try:
                import sounddevice as sd
                from audio_io import find_input_device
                a = self.cfg["audio_in"]
                dev = find_input_device(a.get("name_hint", "C270"), a.get("device", "auto"))
                self.mic_name = sd.query_devices(dev, "input")["name"] if dev is not None else "Varsayılan mikrofon"
            except Exception as e:
                self.mic_name = f"Ses sistemi yok ({e.__class__.__name__})"
            time.sleep(15)

    def toggle_autostart(self):
        try:
            if self.auto_var.get():
                exe = sys.executable
                if exe.lower().endswith("python.exe"):
                    exe = exe[:-10] + "pythonw.exe"
                vbs = ('Set sh = CreateObject("WScript.Shell")\r\n'
                       f'sh.CurrentDirectory = "{HERE}"\r\n'
                       f'sh.Run """{exe}"" ""{os.path.join(HERE, "panel.py")}"" --oto", 0, False\r\n')
                with open(STARTUP_FILE, "w", encoding="utf-16") as f:
                    f.write(vbs)
                if os.path.exists(OLD_STARTUP_FILE) and messagebox.askyesno(
                        "Eski otomatik başlatma",
                        "Konsol penceresiyle açılan eski otomatik başlatma da açık. İkisi birlikte "
                        "çalışırsa robota bağlanırken çakışır.\n\nEskisini kaldırayım mı?"):
                    os.remove(OLD_STARTUP_FILE)
                log.info("Windows açılınca panel (ve robot) otomatik başlayacak.")
            else:
                if os.path.exists(STARTUP_FILE):
                    os.remove(STARTUP_FILE)
                log.info("Otomatik başlatma kapatıldı.")
        except Exception as e:
            self.auto_var.set(os.path.exists(STARTUP_FILE))
            messagebox.showerror("Hata", f"Otomatik başlatma ayarlanamadı:\n{e}")

    # ======== 2) Kişilik ========
    def _build_persona(self, t):
        ctk.CTkLabel(t, text="Karakter (robot bu talimata göre konuşur)", anchor="w").pack(fill="x", padx=5)
        self.persona = ctk.CTkTextbox(t, wrap="word", font=ctk.CTkFont(size=13))
        self.persona.pack(fill="both", expand=True, padx=5, pady=5)
        self.persona.insert("1.0", self.cfg.get("persona", "").rstrip())
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", pady=5)
        x, v = self.cfg["xai"], self.cfg["voice"]
        ctk.CTkLabel(row, text="Model").grid(row=0, column=0, padx=5, sticky="w")
        self.cb_model = ctk.CTkComboBox(row, width=260, values=sorted(set(MODELS + [x["model"]])))
        self.cb_model.set(x["model"])
        self.cb_model.grid(row=0, column=1, padx=5, pady=4)
        ctk.CTkLabel(row, text="Ses motoru").grid(row=0, column=2, padx=(20, 5), sticky="w")
        self.seg_engine = ctk.CTkSegmentedButton(row, values=["xai", "edge"], command=self._engine_changed)
        self.seg_engine.set(v.get("tts_engine", "xai"))
        self.seg_engine.grid(row=0, column=3, padx=5)
        ctk.CTkLabel(row, text="Ses").grid(row=1, column=0, padx=5, sticky="w")
        self.cb_voice = ctk.CTkComboBox(row, width=260, values=[])
        self.cb_voice.grid(row=1, column=1, padx=5, pady=4)
        ctk.CTkLabel(row, text="Hoparlör").grid(row=1, column=2, padx=(20, 5), sticky="w")
        self.seg_out = ctk.CTkSegmentedButton(row, values=["robot", "pc"])
        self.seg_out.set(v.get("output", "robot"))
        self.seg_out.grid(row=1, column=3, padx=5)
        self._xai_voices = list(XAI_VOICES)
        self._engine_changed(v.get("tts_engine", "xai"))
        bot = ctk.CTkFrame(t, fg_color="transparent")
        bot.pack(fill="x", pady=5)
        ctk.CTkButton(bot, text="Kaydet", width=140, command=self.save_persona).pack(side="left", padx=5)
        ctk.CTkButton(bot, text="Grok seslerini getir", width=160, fg_color="#374151",
                      command=lambda: bg(self._fetch_voices)).pack(side="left", padx=5)
        self.lbl_persona = ctk.CTkLabel(bot, text="")
        self.lbl_persona.pack(side="left", padx=10)

    def _engine_changed(self, eng):
        v = self.cfg["voice"]
        if eng == "edge":
            cur = v.get("edge_voice", EDGE_VOICES[0])
            vals = sorted(set(EDGE_VOICES + [cur]))
        else:
            cur = v.get("xai_voice", "rex")
            vals = sorted(set(self._xai_voices + [cur]))
        self.cb_voice.configure(values=vals)
        self.cb_voice.set(cur)

    def _fetch_voices(self):
        import requests
        try:
            r = requests.get(self.cfg["xai"]["base_url"].rstrip("/") + "/tts/voices",
                             headers={"Authorization": f"Bearer {api_key()}"}, timeout=10)
            r.raise_for_status()
            names = [x.get("voice_id") for x in r.json().get("voices", []) if x.get("voice_id")]
            if names:
                self._xai_voices = names
                self.ev.put(("ui", lambda: (self._engine_changed(self.seg_engine.get()),
                                            self.lbl_persona.configure(text=f"{len(names)} ses bulundu."))))
        except Exception as e:
            self.ev.put(("ui", lambda: self.lbl_persona.configure(text=f"Sesler alınamadı (internet?)")))
            log.warning("Ses listesi alınamadı: %s", e)

    def save_persona(self):
        eng = self.seg_engine.get()
        upd = {("persona",): self.persona.get("1.0", "end").rstrip() + "\n",
               ("xai", "model"): self.cb_model.get().strip(),
               ("voice", "tts_engine"): eng,
               ("voice", "output"): self.seg_out.get(),
               ("voice", "edge_voice" if eng == "edge" else "xai_voice"): self.cb_voice.get().strip()}
        try:
            save_config(upd)
        except Exception as e:
            messagebox.showerror("Kaydedilemedi", f"config.yaml yazılamadı:\n{e}")
            return
        set_cfg(self.cfg, upd)                     # canlı uygula
        if self.robot and self.robot.brain:
            self.robot.brain.model = upd[("xai", "model")]
        self.lbl_persona.configure(text="Kaydedildi, hemen geçerli ✓")
        log.info("Ayarlar kaydedildi (model %s, ses %s).", upd[("xai", "model")], self.cb_voice.get())

    # ======== 3) Hafıza ========
    def notes_path(self):
        return os.path.join(HERE, self.cfg["conversation"].get("notes_file", "notlar.txt"))

    def _build_memory(self, t):
        ctk.CTkLabel(t, text="Kalıcı notlar (robot her konuşmada bunları hatırlar)", anchor="w").pack(fill="x", padx=5)
        self.notes = tk.Listbox(t, bg="#1f1f1f", fg="#e5e7eb", selectbackground="#2563eb", font=("Segoe UI", 11),
                                borderwidth=0, highlightthickness=0, activestyle="none")
        self.notes.pack(fill="both", expand=True, padx=5, pady=5)
        self.notes.bind("<<ListboxSelect>>", self._note_selected)
        self.note_entry = ctk.CTkEntry(t, placeholder_text="Not yaz (ör. Ahmet Fenerbahçeli, her fırsatta laf sok)")
        self.note_entry.pack(fill="x", padx=5, pady=5)
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Ekle", width=110, command=self.note_add).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Seçileni güncelle", width=140, command=self.note_edit).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Seçileni sil", width=110, fg_color="#b91c1c", hover_color="#991b1b",
                      command=self.note_delete).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Sohbet hafızasını temizle", width=180, fg_color="#374151",
                      command=self.clear_history).pack(side="right", padx=5)
        self.load_notes()

    def _read_notes(self):
        try:
            with open(self.notes_path(), encoding="utf-8") as f:
                return [ln.rstrip("\n") for ln in f if ln.strip()]
        except FileNotFoundError:
            return []

    def _write_notes(self, lines):
        with open(self.notes_path(), "w", encoding="utf-8") as f:
            f.write("".join(ln + "\n" for ln in lines))
        self.load_notes()

    def load_notes(self):
        self._notes_lines = self._read_notes()
        self.notes.delete(0, "end")
        for ln in self._notes_lines:
            self.notes.insert("end", ln[2:] if ln.startswith("- ") else ln)
        try:
            self._notes_mtime = os.path.getmtime(self.notes_path())
        except OSError:
            self._notes_mtime = None

    def _sel(self):
        s = self.notes.curselection()
        return s[0] if s else None

    def _note_selected(self, _=None):
        i = self._sel()
        if i is not None:
            self.note_entry.delete(0, "end")
            self.note_entry.insert(0, self.notes.get(i))

    def note_add(self):
        txt = self.note_entry.get().strip()
        if txt:
            self._write_notes(self._read_notes() + [f"- {datetime.date.today().isoformat()}: {txt}"])
            self.note_entry.delete(0, "end")

    def note_edit(self):
        i, txt = self._sel(), self.note_entry.get().strip()
        if i is None or not txt:
            messagebox.showinfo("Hafıza", "Önce listeden bir not seç, kutuda düzelt, sonra Güncelle'ye bas.")
            return
        lines = self._notes_lines
        lines[i] = "- " + txt
        self._write_notes(lines)

    def note_delete(self):
        i = self._sel()
        if i is None:
            return
        lines = self._notes_lines
        del lines[i]
        self._write_notes(lines)
        self.note_entry.delete(0, "end")

    def clear_history(self):
        if self.robot and self.robot.brain:
            self.robot.brain.history.clear()
        log.info("Sohbet hafızası (son konuşmalar) temizlendi. Kalıcı notlar duruyor.")

    # ======== 4) Sohbet ========
    def _build_chat(self, t):
        self.chat = ctk.CTkTextbox(t, wrap="word", font=ctk.CTkFont(size=13))
        self.chat.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat.tag_config("user", foreground="#93c5fd")
        self.chat.tag_config("robot", foreground="#86efac")
        self.chat.tag_config("err", foreground="#fca5a5")
        self.chat.configure(state="disabled")
        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", pady=5)
        self.chat_entry = ctk.CTkEntry(row, placeholder_text="Robota yaz, Enter'a bas...")
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.chat_entry.bind("<Return>", lambda _: self.send_chat())
        self.speak_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(row, text="Sesli cevap ver", variable=self.speak_var).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Gönder", width=90, command=self.send_chat).pack(side="left", padx=5)

    def chat_add(self, who, text, tag):
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{datetime.datetime.now():%H:%M}  {who}: ", tag)
        self.chat.insert("end", text + "\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def send_chat(self):
        txt = self.chat_entry.get().strip()
        if not txt:
            return
        if not self.robot_running() or not self.robot.brain:
            self.chat_add("Panel", "Önce Durum sekmesinden robotu başlat.", "err")
            return
        self.chat_entry.delete(0, "end")
        bg(self.robot.handle, txt, True, self.speak_var.get())

    # ======== 5) Test ========
    def _build_test(self, t):
        def section(title):
            f = ctk.CTkFrame(t)
            f.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(f, text=title, width=110, anchor="w",
                         font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=8)
            return f

        f = section("Kafa")
        for txt, a in (("◀ -60°", -60), ("Orta", 0), ("+60° ▶", 60)):
            ctk.CTkButton(f, text=txt, width=70, command=lambda a=a: self.test_pan(a)).pack(side="left", padx=3)
        self.pan_slider = ctk.CTkSlider(f, from_=-90, to=90, number_of_steps=36, width=220,
                                        command=lambda v: self.test_pan(v))
        self.pan_slider.set(0)
        self.pan_slider.pack(side="left", padx=10)
        self.pause_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(f, text="Takibi duraklat", variable=self.pause_var,
                      command=self._apply_pause).pack(side="left", padx=5)

        f = section("Gözler")
        for txt, m in EYES:
            ctk.CTkButton(f, text=txt, width=72, command=lambda m=m: self.link.eyes(m)).pack(side="left", padx=2)

        f = section("LED")
        for txt, c in COLORS:
            ctk.CTkButton(f, text=txt, width=70, command=lambda c=c: self.test_led(c)).pack(side="left", padx=2)
        self.br_slider = ctk.CTkSlider(f, from_=1, to=20, number_of_steps=19, width=120,
                                       command=lambda v: self.test_led(self._last_led))
        self.br_slider.set(self.cfg["leds"].get("brightness", 12))
        self.br_slider.pack(side="left", padx=10)
        self._last_led = LED_STATES["idle"]

        f = section("Hoparlör")
        ctk.CTkButton(f, text="Bip", width=70, command=lambda: self.link.beep(880, 200)).pack(side="left", padx=3)
        ctk.CTkButton(f, text="Test cümlesi", width=110,
                      command=lambda: bg(self.test_sentence)).pack(side="left", padx=3)
        ctk.CTkLabel(f, text="Ses").pack(side="left", padx=(15, 5))
        self.vol_slider = ctk.CTkSlider(f, from_=0, to=100, number_of_steps=20, width=200, command=self.test_volume)
        self.vol_slider.set(self.cfg["voice"].get("robot_volume", 60))
        self.vol_slider.pack(side="left", padx=5)
        self.lbl_vol = ctk.CTkLabel(f, text=str(int(self.cfg["voice"].get("robot_volume", 60))), width=40)
        self.lbl_vol.pack(side="left")

        self.lbl_test = ctk.CTkLabel(t, text="", anchor="w", text_color="#9ca3af")
        self.lbl_test.pack(fill="x", padx=10, pady=10)

    def _apply_pause(self):
        if self.robot and self.robot.tracker:
            self.robot.tracker.paused = self.pause_var.get()

    def test_pan(self, a):
        if self.robot_running() and not self.pause_var.get():
            self.pause_var.set(True)               # yoksa yüz takibi kafayı geri çevirir
            self._apply_pause()
            self.lbl_test.configure(text="Yüz takibi duraklatıldı (Test bitince anahtarı kapat).")
        self.link.pan_speed(90)
        self.link.pan(float(a))
        if not self.link.connected:
            self.lbl_test.configure(text="Robot bağlı değil.")

    def test_led(self, c):
        self._last_led = c
        self.link.led(*c, int(self.br_slider.get()) if any(c) else 0)

    def test_volume(self, v):
        v = int(v)
        self.lbl_vol.configure(text=str(v))
        self.link.volume(v)
        self.cfg["voice"]["robot_volume"] = v
        if self._vol_job:
            self.after_cancel(self._vol_job)
        self._vol_job = self.after(1000, lambda: self._safe(save_config, {("voice", "robot_volume"): v}))

    def _safe(self, fn, *a):
        try:
            fn(*a)
        except Exception as e:
            log.error("Hata: %s", e)

    def test_sentence(self):
        from audio_io import play_local
        from speech import TTS
        name = self.cfg.get("robot_adi", "Robot")
        self.ev.put(("ui", lambda: self.lbl_test.configure(text="Ses hazırlanıyor...")))
        try:
            pcm = TTS(self.cfg).synth(f"Selam kanka, ben {name}. Ses testi tamam.")
            if self.cfg["voice"].get("output") == "robot" and self.link.connected:
                self.link.play_pcm(pcm)
            else:
                play_local(pcm)
            msg = "Test cümlesi çalındı."
        except Exception as e:
            msg = f"Ses üretilemedi (internet yok olabilir): {e}"
        self.ev.put(("ui", lambda: self.lbl_test.configure(text=msg)))

    # ======== olay döngüsü ========
    def _poll(self):
        try:
            while True:
                kind, data = self.ev.get_nowait()
                if kind == "state":
                    self._set_state(data)
                elif kind == "user":
                    self.chat_add("Sen", data, "user")
                elif kind == "robot":
                    self.chat_add(self.cfg.get("robot_adi", "Robot"), data, "robot")
                elif kind == "error":
                    self.chat_add("Hata", data, "err")
                    if "internet" in data:
                        self.net = ("İnternet yok", RED)
                        self._net_kick.set()
                elif kind == "log":
                    self.logbox.configure(state="normal")
                    self.logbox.insert("end", data + "\n")
                    if int(self.logbox.index("end").split(".")[0]) > 400:
                        self.logbox.delete("1.0", "100.0")
                    self.logbox.configure(state="disabled")
                    self.logbox.see("end")
                elif kind == "stopped":
                    self.btn_run.configure(state="normal", text="▶  Robotu Başlat",
                                           fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"))
                    self._set_state("off")
                    self.preview.configure(image=None, text="Kamera önizlemesi\n(robot çalışınca)")
                elif kind == "ui":
                    data()
        except queue.Empty:
            pass
        except Exception as e:
            log.debug("Panel olay hatası: %s", e)
        now = time.time()
        if now - getattr(self, "_slow_t", 0) > 1:
            self._slow_t = now
            try:
                self._update_status()
                m = os.path.getmtime(self.notes_path()) if os.path.exists(self.notes_path()) else None
                if m != self._notes_mtime:
                    self.load_notes()          # robot "not_al" ile yazdıysa listeye gelsin
            except Exception as e:
                log.debug("Durum güncellenemedi: %s", e)
        if now - getattr(self, "_prev_t", 0) > 0.2:     # önizleme ~5 kare/sn
            self._prev_t = now
            self._update_preview()
        self.after(100, self._poll)

    def on_close(self):
        try:
            if self.robot_running():
                self.robot.stop()
                self.robot_thread.join(timeout=3)
            self.link.close()
        except Exception:
            pass
        self.destroy()


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = Panel(auto_start="--oto" in sys.argv)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        _fatal(traceback.format_exc())
