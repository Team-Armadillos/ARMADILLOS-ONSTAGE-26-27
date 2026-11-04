"""Camera frame acquisition on the application thread."""
import cv2
from PIL import Image
class CameraManager:
    def __init__(self,index=0):self.index=index;self.capture=None
    def start(self):
        if self.capture is not None:return
        cap=cv2.VideoCapture(self.index)
        if not cap.isOpened():cap.release();raise RuntimeError(f"Camera {self.index} unavailable")
        self.capture=cap
    def frame(self):
        if self.capture is None:return None
        ok,frame=self.capture.read()
        return Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGBA)) if ok else None
    def stop(self):
        if self.capture is not None:self.capture.release();self.capture=None
