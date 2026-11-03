"""Optional serial bridge. Lines: SIGNAL:3 or EVENT:my_event."""
import threading
class SerialManager:
    def __init__(self,port,baudrate,emit):self.port=port;self.baudrate=baudrate;self.emit=emit;self.stop_flag=threading.Event();self.thread=None;self.device=None
    def start(self):
        import serial
        self.device=serial.Serial(self.port,self.baudrate,timeout=.2)
        self.thread=threading.Thread(target=self._loop,daemon=True);self.thread.start()
    def _loop(self):
        while not self.stop_flag.is_set():
            try:
                line=self.device.readline().decode(errors="replace").strip()
                if line.startswith("SIGNAL:"):self.emit("signal",{"value":int(line.split(":",1)[1])},"serial")
                elif line.startswith("EVENT:"):self.emit(line.split(":",1)[1],{},"serial")
            except Exception as exc:
                self.emit("communication_error",{"message":str(exc)},"serial");break
    def send(self,message):
        if self.device:self.device.write((str(message)+"\n").encode())
    def close(self):
        self.stop_flag.set()
        if self.thread:self.thread.join(timeout=1)
        if self.device:self.device.close()
