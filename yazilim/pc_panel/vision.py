"""Kamera + yüz bulma + kafa takibi (oransal kontrol, ölü bölge, yumuşatma, tarama)."""
import logging
import sys
import threading
import time

import cv2

log = logging.getLogger("kamera")


def find_camera_index(name_hint="C270"):
    """Windows'ta DirectShow cihaz listesinden adında name_hint geçen kamerayı bul."""
    if sys.platform != "win32":
        return None
    try:
        from pygrabber.dshow_graph import FilterGraph
        devices = FilterGraph().get_input_devices()
        log.info("Bulunan kameralar: %s", ", ".join(f"{i}={d}" for i, d in enumerate(devices)) or "yok")
        for i, d in enumerate(devices):
            if name_hint.lower() in d.lower():
                return i
    except Exception as e:
        log.debug("Kamera listesi alınamadı: %s", e)
    return None


def open_camera(cfg):
    idx = cfg.get("index", "auto")
    if str(idx).lower() == "auto":
        idx = find_camera_index(cfg.get("name_hint", "C270"))
        if idx is None:
            log.warning("'%s' adlı kamera bulunamadı, 0 numaralı kamera deneniyor.", cfg.get("name_hint"))
            idx = 0
    idx = int(idx)
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
    cap = cv2.VideoCapture(idx, backend)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.get("width", 640))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.get("height", 480))
    if not cap.isOpened():
        return None, idx
    return cap, idx


class FaceDetector:
    """MediaPipe yüz bulucu; yüklenemezse OpenCV Haar yedek."""

    def __init__(self, kind="mediapipe", min_conf=0.6):
        self.kind = None
        self.last_box = None        # son bulunan yüzün kutusu (x, y, w, h), 0..1 oranında
        if kind == "mediapipe":
            try:
                import mediapipe as mp
                # model_selection=1: 5 metreye kadar (oda içinde arkadaşlar uzakta da olsa)
                self.mp_det = mp.solutions.face_detection.FaceDetection(
                    model_selection=1, min_detection_confidence=min_conf)
                self.kind = "mediapipe"
            except Exception as e:
                log.warning("MediaPipe yüklenemedi (%s), Haar kullanılacak.", e)
        if self.kind is None:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.haar = cv2.CascadeClassifier(path)
            self.kind = "haar"
        log.info("Yüz bulucu: %s", self.kind)

    def detect(self, frame_bgr):
        """En büyük yüzün merkezini (0..1, 0..1) ve alanını döndür; yoksa None."""
        h, w = frame_bgr.shape[:2]
        small = cv2.resize(frame_bgr, (320, int(320 * h / w)))   # zayıf PC için küçült
        faces = []
        if self.kind == "mediapipe":
            res = self.mp_det.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            for d in (res.detections or []):
                b = d.location_data.relative_bounding_box
                faces.append((b.xmin + b.width / 2, b.ymin + b.height / 2, b.width * b.height,
                              (b.xmin, b.ymin, b.width, b.height)))
        else:
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            sh, sw = gray.shape
            for (x, y, fw, fh) in self.haar.detectMultiScale(gray, 1.2, 5, minSize=(30, 30)):
                faces.append(((x + fw / 2) / sw, (y + fh / 2) / sh, fw * fh / (sw * sh),
                              (x / sw, y / sh, fw / sw, fh / sh)))
        if not faces:
            self.last_box = None
            return None
        best = max(faces, key=lambda f: f[2])
        self.last_box = best[3]
        return best[:3]


class Tracker(threading.Thread):
    """Kameradan kare alır, yüzü bulur, ESP32'ye PAN ve LOOK komutları yollar."""

    def __init__(self, cfg, link):
        super().__init__(daemon=True, name="takip")
        self.cam_cfg = cfg["camera"]
        self.t = cfg["tracking"]
        self.link = link
        self.stop_event = threading.Event()
        self.last_face_time = 0.0
        self.face_visible = False
        self.pan_cmd = 0.0          # gönderilen son kafa açısı
        self.mode = "start"
        self._fx = 0.5
        self._fy = 0.5
        self.paused = False
        self.last_frame = None      # kontrol paneli önizlemesi için son kare
        self.last_frame_t = 0.0
        self.last_box = None

    def seen_recently(self, seconds=5):
        return time.time() - self.last_face_time < seconds

    def _set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        log.info({"track": "Yüz görüldü, takip ediliyor.",
                  "scan": "Kimse yok, etrafı tarıyorum...",
                  "idle": "Uzun süredir kimse yok, dinleniyorum."}.get(mode, mode))
        if mode == "track":
            self.link.pan_speed(self.t.get("track_speed", 90))
        elif mode == "scan":
            self.link.pan_speed(self.t.get("scan_speed", 25))
        elif mode == "idle":
            self.link.pan_speed(30)
            self.pan_cmd = 0.0
            self.link.pan(0)
            self.link.look(0, 0)

    def run(self):
        cap = None
        det = FaceDetector(self.t.get("detector", "mediapipe"), self.t.get("min_confidence", 0.6))
        hfov = float(self.cam_cfg.get("hfov_deg", 48))
        vfov = hfov * 0.75
        limit = float(self.t.get("pan_limit_deg", 90))
        sign = -1.0 if self.t.get("pan_invert", False) else 1.0
        scan_dir = 1.0
        last_cmd_t = 0.0
        last_sent_pan = None
        self.last_face_time = time.time()
        while not self.stop_event.is_set():
            if cap is None:
                cap, idx = open_camera(self.cam_cfg)
                if cap is None:
                    log.warning("Kamera açılamadı (index %s). 3 sn sonra tekrar denenecek.", idx)
                    time.sleep(3)
                    continue
                log.info("Kamera açıldı (index %s).", idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                log.warning("Kameradan görüntü alınamadı, yeniden açılıyor...")
                cap.release()
                cap = None
                time.sleep(1)
                continue
            if self.paused:
                time.sleep(0.05)
                continue

            face = det.detect(frame)
            now = time.time()
            self.last_frame, self.last_box, self.last_frame_t = frame, det.last_box, now
            if face:
                fx, fy, _ = face
                a = float(self.t.get("smoothing", 0.5))
                if not self.face_visible:          # yeni görünen yüzde yumuşatmayı sıfırla
                    self._fx, self._fy = fx, fy
                self._fx = a * self._fx + (1 - a) * fx
                self._fy = a * self._fy + (1 - a) * fy
                self.face_visible = True
                self.last_face_time = now
                self._set_mode("track")
                err_x = self._fx - 0.5            # -0.5..0.5, + = görüntünün sağı
                err_y = self._fy - 0.5
                err_deg = err_x * hfov
                # Gözler yüze baksın (görüntünün solundaki kişi -> ekranda sola bakış)
                if now - last_cmd_t > 0.1:
                    self.link.look(max(-100, min(100, err_x * 200)), max(-100, min(100, err_y * 200)))
                    if abs(err_deg) > float(self.t.get("deadband_deg", 4)):
                        step = float(self.t.get("kp", 0.45)) * err_deg
                        mx = float(self.t.get("max_step_deg", 8))
                        step = max(-mx, min(mx, step))
                        self.pan_cmd = max(-limit, min(limit, self.pan_cmd + sign * step))
                    last_cmd_t = now
            else:
                self.face_visible = False
                gone = now - self.last_face_time
                if gone > float(self.t.get("idle_after_s", 60)):
                    self._set_mode("idle")
                elif gone > float(self.t.get("scan_after_s", 8)):
                    self._set_mode("scan")
                    rng = float(self.t.get("scan_range_deg", 60))
                    if now - last_cmd_t > 0.2:
                        self.pan_cmd += scan_dir * float(self.t.get("scan_speed", 25)) * 0.2
                        if abs(self.pan_cmd) >= rng:
                            self.pan_cmd = max(-rng, min(rng, self.pan_cmd))
                            scan_dir = -scan_dir
                        self.link.look(scan_dir * sign * 50, 0)
                        last_cmd_t = now

            if last_sent_pan is None or abs(self.pan_cmd - last_sent_pan) >= 1.0:
                self.link.pan(self.pan_cmd)
                last_sent_pan = self.pan_cmd

            if self.cam_cfg.get("show_window"):
                if face:
                    h, w = frame.shape[:2]
                    cv2.circle(frame, (int(self._fx * w), int(self._fy * h)), 10, (0, 255, 0), 2)
                cv2.imshow("Robot kamerasi (q = kapat)", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.cam_cfg["show_window"] = False
                    cv2.destroyAllWindows()
        if cap is not None:
            cap.release()
