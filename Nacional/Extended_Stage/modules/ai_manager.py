"""Optional YOLO model inference. Requires a separately supplied trained model."""
from concurrent.futures import ThreadPoolExecutor
class AIManager:
    def __init__(self,model_path=None,confidence=.65):
        self.model_path=model_path;self.confidence=confidence;self.model=None
        self.pool=ThreadPoolExecutor(max_workers=1);self.pending=None
    def load(self):
        if not self.model_path:raise RuntimeError("No trained AI model configured")
        from ultralytics import YOLO
        self.model=YOLO(str(self.model_path))
    def submit(self,frame):
        if self.model is None or self.pending is not None:return
        self.pending=self.pool.submit(self._predict,frame.copy())
    def _predict(self,frame):
        import numpy as np
        result=self.model.predict(np.array(frame.convert("RGB")),verbose=False,conf=self.confidence)[0]
        return [{"class_id":int(box.cls[0]),"confidence":float(box.conf[0]),"label":result.names[int(box.cls[0])]} for box in result.boxes]
    def poll(self):
        if self.pending is None or not self.pending.done():return None
        future=self.pending;self.pending=None
        return future.result()
    def close(self):self.pool.shutdown(wait=False,cancel_futures=True)
