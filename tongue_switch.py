# Tongue-present detector (threaded) with continuous state (no flashing)
# and annotated preview (mouth ROI + tongue mask boxes).
#
# Public API:
#   - start(), stop()
#   - get_state() -> bool                 # continuous TRUE while tongue present
#   - consume_rising_edge() -> bool       # one-shot TRUE on False->True (debounced)
#   - get_preview_rgb() -> np.ndarray|None  # annotated RGB frame
#
# Deps: opencv-python, mediapipe, numpy
import sys, time, threading
import numpy as np
import cv2
import mediapipe as mp

# Mediapipe FaceMesh inner-lip ring
INNER_LIPS = [78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95]

def _open_camera():
    candidates = []
    if sys.platform == "darwin":
        candidates = [(0, cv2.CAP_AVFOUNDATION), (1, cv2.CAP_AVFOUNDATION), (0, 0)]
    elif sys.platform.startswith("win"):
        candidates = [(0, cv2.CAP_DSHOW), (0, cv2.CAP_MSMF), (1, cv2.CAP_DSHOW)]
    else:
        candidates = [(0, 0), (1, 0)]
    for idx, be in candidates:
        cap = cv2.VideoCapture(idx, be)
        if cap.isOpened():
            return cap
    raise RuntimeError("No camera could be opened. Close other apps or grant permission.")

def _poly_from_landmarks(lms, idxs, w, h):
    arr = np.array([[int(lms[i].x*w), int(lms[i].y*h)] for i in idxs], dtype=np.int32)
    return np.ascontiguousarray(arr)

def _mouth_open_amount(lms, w, h):
    up = (int(lms[13].x*w), int(lms[13].y*h))
    lo = (int(lms[14].x*w), int(lms[14].y*h))
    return abs(lo[1]-up[1])

def _tongue_mask(bgr_roi, mouth_mask):
    if bgr_roi.size == 0 or mouth_mask.size == 0:
        return np.zeros_like(mouth_mask)
    hsv = cv2.cvtColor(bgr_roi, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 60, 70), (12, 255, 255))
    m2 = cv2.inRange(hsv, (160, 60, 70), (179, 255, 255))
    m = (m1 | m2)
    m = cv2.bitwise_and(m, mouth_mask)
    m = cv2.medianBlur(m, 5)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), 1)
    return m

class TongueSwitch:
    def __init__(self,
                 show_window: bool = False,
                 frac_threshold: float = 0.06,
                 min_open_px: int = 8,
                 debounce_s: float = 0.12,
                 preview_size=(900, 260)):
        self._show = show_window
        self._frac_th = frac_threshold
        self._min_open = min_open_px
        self._debounce = debounce_s
        self._size = tuple(preview_size)

        self._state = False          # continuous detection (no debounce)
        self._prev_state = False     # for rising-edge
        self._last_event_time = 0.0  # debounce timer

        self._preview = None

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ---- API ----
    def start(self): self._thread.start()
    def stop(self):
        self._stop.set()
        self._thread.join(timeout=1.0)

    def get_state(self) -> bool:
        with self._lock:
            return self._state

    def consume_rising_edge(self) -> bool:
        now = time.time()
        with self._lock:
            if self._state and not self._prev_state and (now - self._last_event_time) > self._debounce:
                self._prev_state = True
                self._last_event_time = now
                return True
            self._prev_state = self._state
            return False

    def get_preview_rgb(self):
        with self._lock:
            return None if self._preview is None else self._preview.copy()

    # ---- worker ----
    def _run(self):
        try:
            cap = _open_camera()
        except Exception as e:
            print("[TongueSwitch] Camera error:", e)
            return

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as mesh:
            if self._show:
                cv2.namedWindow("Tongue Debug", cv2.WINDOW_AUTOSIZE)

            while not self._stop.is_set():
                ok, frame_bgr = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue

                h, w = frame_bgr.shape[:2]
                res = mesh.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

                tongue_present = False
                annotated = frame_bgr.copy()

                if res.multi_face_landmarks:
                    lms = res.multi_face_landmarks[0].landmark
                    inner = _poly_from_landmarks(lms, INNER_LIPS, w, h)

                    x, y, ww, hh = cv2.boundingRect(inner)
                    pad = 6
                    x0, y0 = max(0, x-pad), max(0, y-pad)
                    x1, y1 = min(w, x+ww+pad), min(h, y+hh+pad)

                    if x1 > x0 and y1 > y0:
                        roi = frame_bgr[y0:y1, x0:x1]
                        inner_roi = np.ascontiguousarray(inner - np.array([x0, y0], dtype=np.int32))
                        mouth_mask = np.zeros(roi.shape[:2], np.uint8)

                        if mouth_mask.size and inner_roi.size >= 6:
                            try:
                                cv2.fillPoly(mouth_mask, [inner_roi], 255)
                                open_px = _mouth_open_amount(lms, w, h)
                                tongue_mask = _tongue_mask(roi, mouth_mask)
                                tongue_px = int(tongue_mask.sum() // 255)
                                mouth_px = int(mouth_mask.sum() // 255)
                                frac = tongue_px / max(1, mouth_px)

                                # Continuous state
                                tongue_present = (open_px >= self._min_open) and (frac >= self._frac_th)

                                # --- Annotations ---
                                # Mouth ROI box (green)
                                cv2.rectangle(annotated, (x0, y0), (x1, y1), (0, 200, 0), 2)
                                # Tongue contours / red boxes
                                if tongue_px > 0:
                                    contours, _ = cv2.findContours(tongue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                                    for cnt in contours:
                                        if cv2.contourArea(cnt) < 12:
                                            continue
                                        rx, ry, rww, rhh = cv2.boundingRect(cnt)
                                        cv2.rectangle(annotated, (x0+rx, y0+ry), (x0+rx+rww, y0+ry+rhh), (0, 60, 255), 2)
                                # Text metrics
                                txt = f"open={open_px}px  frac={frac:.2f}  tongue={'True' if tongue_present else 'False'}"
                                cv2.putText(annotated, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

                            except cv2.error:
                                pass

                small = cv2.resize(annotated, self._size, interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

                with self._lock:
                    self._state = bool(tongue_present)
                    self._preview = rgb

                if self._show:
                    try:
                        cv2.imshow("Tongue Debug", annotated)
                        if cv2.waitKey(1) & 0xFF == 27:
                            self._stop.set(); break
                    except Exception:
                        pass

        cap.release()
        if self._show:
            try: cv2.destroyAllWindows()
            except: pass