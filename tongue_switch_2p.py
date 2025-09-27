#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# MultiTongueSwitch: two-face tongue detector (opencv + mediapipe).
# Left-most face -> index 0 (P1), right-most -> index 1 (P2).
#
# Public API:
#   start(), stop()
#   get_state(i=0) -> bool
#   consume_rising_edge(i=0) -> bool
#   get_preview_rgb() -> RGB frame (H,W,3) or None
#   get_direction(i=0) -> "UP"/"DOWN"/"LEFT"/"RIGHT"/"CENTER" or None
#
# Graceful fallback: if deps unavailable or camera fails, states stay False and
# preview is None so your game can still run with keyboard.

import sys, time, threading
import numpy as np

try:
    import cv2
    import mediapipe as mp
    TONGUE_DEPS_OK = True
except Exception as e:
    print("[WARN] Tongue deps unavailable:", e)
    TONGUE_DEPS_OK = False

INNER_LIPS = [78,191,80,81,82,13,312,311,310,415,308,324,318,402,317,14,87,178,88,95]

def _open_camera():
    if not TONGUE_DEPS_OK:
        raise RuntimeError("OpenCV/Mediapipe unavailable.")
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

def _classify_direction(cx, cy, mx, my, dead_px):
    dx, dy = cx - mx, cy - my
    if abs(dx) < dead_px and abs(dy) < dead_px:
        return "CENTER"
    if abs(dx) >= abs(dy):
        return "RIGHT" if dx > 0 else "LEFT"
    else:
        return "DOWN" if dy > 0 else "UP"

class MultiTongueSwitch:
    def __init__(self,
                 show_window: bool = False,
                 frac_threshold: float = 0.06,
                 min_open_px: int = 8,
                 debounce_s: float = 0.12,
                 preview_size=(900, 260),
                 dir_dead_frac: float = 0.10,
                 show_metrics: bool = True,
                 mirror: bool = True,
                 max_players: int = 2):
        self._enabled = TONGUE_DEPS_OK
        self._show = show_window
        self._frac_th = frac_threshold
        self._min_open = min_open_px
        self._debounce = debounce_s
        self._size = tuple(preview_size)
        self._dead_frac = dir_dead_frac
        self._show_metrics = show_metrics
        self._mirror = mirror
        self._maxp = max_players

        self._state = [False]*self._maxp
        self._prev_state = [False]*self._maxp
        self._last_event_time = [0.0]*self._maxp
        self._direction = [None]*self._maxp
        self._preview = None

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ---- API ----
    def start(self):
        if self._enabled:
            self._thread.start()

    def stop(self):
        if not self._enabled: return
        self._stop.set()
        self._thread.join(timeout=1.0)

    def get_state(self, i=0) -> bool:
        if not self._enabled: return False
        with self._lock:
            return self._state[i]

    def get_direction(self, i=0):
        if not self._enabled: return None
        with self._lock:
            return self._direction[i]

    def consume_rising_edge(self, i=0) -> bool:
        if not self._enabled: return False
        now = time.time()
        with self._lock:
            if self._state[i] and not self._prev_state[i] and (now - self._last_event_time[i]) > self._debounce:
                self._prev_state[i] = True
                self._last_event_time[i] = now
                return True
            self._prev_state[i] = self._state[i]
            return False

    def get_preview_rgb(self):
        if not self._enabled: return None
        with self._lock:
            return None if self._preview is None else self._preview.copy()

    # ---- worker ----
    def _run(self):
        try:
            cap = _open_camera()
        except Exception as e:
            print("[MultiTongueSwitch] Camera error:", e)
            return

        mp_face = mp.solutions.face_mesh
        with mp_face.FaceMesh(
            static_image_mode=False,
            max_num_faces=self._maxp,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as mesh:
            if self._show:
                cv2.namedWindow("Tongue Debug", cv2.WINDOW_AUTOSIZE)

            while not self._stop.is_set():
                ok, frame_bgr = cap.read()
                if not ok:
                    time.sleep(0.01); continue

                if self._mirror:
                    frame_bgr = cv2.flip(frame_bgr, 1)

                h, w = frame_bgr.shape[:2]
                res = mesh.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                annotated = frame_bgr.copy()

                faces = []  # {mx,my,tongue,dir}
                if res.multi_face_landmarks:
                    for face in res.multi_face_landmarks[:self._maxp]:
                        lms = face.landmark
                        inner = _poly_from_landmarks(lms, INNER_LIPS, w, h)
                        x, y, ww, hh = cv2.boundingRect(inner)
                        pad = 6
                        x0, y0 = max(0, x-pad), max(0, y-pad)
                        x1, y1 = min(w, x+ww+pad), min(h, y+hh+pad)
                        tongue_present = False
                        direction = None
                        mx = my = None
                        if x1 > x0 and y1 > y0:
                            roi = frame_bgr[y0:y1, x0:x1]
                            inner_roi = np.ascontiguousarray(inner - np.array([x0, y0], dtype=np.int32))
                            mouth_mask = np.zeros(roi.shape[:2], np.uint8)
                            if mouth_mask.size and inner_roi.size >= 6:
                                try:
                                    cv2.fillPoly(mouth_mask, [inner_roi], 255)
                                    open_px = _mouth_open_amount(lms, w, h)
                                    tmask = _tongue_mask(roi, mouth_mask)
                                    tongue_px = int(tmask.sum() // 255)
                                    mouth_px = int(mouth_mask.sum() // 255)
                                    frac = tongue_px / max(1, mouth_px)
                                    tongue_present = (open_px >= self._min_open) and (frac >= self._frac_th)
                                    mx = (x0 + x1)//2
                                    my = (y0 + y1)//2
                                    if tongue_present and tongue_px > 0:
                                        m = cv2.moments(tmask, binaryImage=True)
                                        if m["m00"] > 0:
                                            cx = x0 + int(m["m10"]/m["m00"])
                                            cy = y0 + int(m["m01"]/m["m00"])
                                            dead_px = int(self._dead_frac * max(1, max(x1-x0, y1-y0)))
                                            direction = _classify_direction(cx, cy, mx, my, dead_px)
                                            if self._show_metrics:
                                                cv2.arrowedLine(annotated, (mx, my), (cx, cy), (255,255,0), 2, tipLength=0.25)
                                                cv2.circle(annotated, (mx, my), 3, (0,255,255), -1)
                                    if self._show_metrics:
                                        cv2.rectangle(annotated, (x0,y0), (x1,y1), (0,200,0), 2)
                                except cv2.error:
                                    pass
                        if mx is not None:
                            faces.append(dict(mx=mx, my=my, tongue=tongue_present, direction=direction))

                faces.sort(key=lambda d: d["mx"])  # left->right
                with self._lock:
                    for i in range(self._maxp):
                        if i < len(faces):
                            self._state[i] = bool(faces[i]["tongue"])
                            self._direction[i] = faces[i]["direction"]
                        else:
                            self._state[i] = False
                            self._direction[i] = None
                    small = cv2.resize(annotated, self._size, interpolation=cv2.INTER_AREA)
                    self._preview = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

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

if __name__ == "__main__":
    ts = MultiTongueSwitch(show_window=True, mirror=True)
    ts.start()
    try:
        while True:
            time.sleep(0.25)
            print("P1:", ts.get_state(0), ts.get_direction(0), " | P2:", ts.get_state(1), ts.get_direction(1))
    except KeyboardInterrupt:
        pass
    finally:
        ts.stop()
