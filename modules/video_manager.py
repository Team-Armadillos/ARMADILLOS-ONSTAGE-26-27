"""Decode video in a worker thread; publish only the newest RGB frame.

The display thread never decodes MP4 frames. When decoding falls behind, late
frames are skipped so playback tracks elapsed time instead of growing a queue.
OpenCV does not reproduce audio embedded in MP4 files.
"""
import logging
import threading
import time

import cv2


class VideoManager:
    def __init__(self):
        self.capture = None
        self.frame = None
        self.fps = 30.0
        self.finished = False
        self.paused = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker = None
        self._started = 0.0
        self._pause_started = 0.0
        self._next_frame = 0

    def play(self, path):
        self.stop()
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not 1 <= fps <= 240:
            fps = 30.0
        self.capture = capture
        self.fps = float(fps)
        self.finished = False
        self.paused = False
        self._started = time.monotonic()
        self._next_frame = 0
        self._stop.clear()
        self._worker = threading.Thread(target=self._decode_loop, daemon=True, name="VideoDecoder")
        self._worker.start()

    def _decode_loop(self):
        capture = self.capture
        try:
            while not self._stop.is_set():
                with self._lock:
                    paused = self.paused
                    start = self._started
                    frame_number = self._next_frame
                if paused:
                    self._stop.wait(0.015)
                    continue
                elapsed = time.monotonic() - start
                target = max(0, int(elapsed * self.fps))
                if target < frame_number:
                    self._stop.wait(min((frame_number / self.fps) - elapsed, 0.015))
                    continue
                # Skip delayed frames without converting or drawing them.
                skipped = min(max(0, target - frame_number), 120)
                for _ in range(skipped):
                    if self._stop.is_set() or not capture.grab():
                        self.finished = True
                        return
                    frame_number += 1
                if self._stop.is_set():
                    return
                ok, bgr = capture.read()
                if not ok:
                    self.finished = True
                    return
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                with self._lock:
                    self.frame = rgb
                    self._next_frame = frame_number + 1
        except Exception:
            logging.exception("Video decoder failed")
            self.finished = True

    def update(self):
        with self._lock:
            return self.frame

    def pause(self):
        with self._lock:
            if self.capture is not None and not self.paused:
                self.paused = True
                self._pause_started = time.monotonic()

    def resume(self):
        with self._lock:
            if self.paused:
                self._started += time.monotonic() - self._pause_started
                self.paused = False

    def stop(self, keep_frame=False):
        self._stop.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=2)
        # If a decoder is still active, do not release a capture it is using.
        if worker is None or not worker.is_alive():
            if self.capture is not None:
                self.capture.release()
        else:
            logging.warning("Video decoder still active after stop request")
        self.capture = None
        self._worker = None
        with self._lock:
            self.paused = False
            if not keep_frame:
                self.frame = None
        self.finished = False
