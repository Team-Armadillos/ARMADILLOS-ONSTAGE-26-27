"""Receive LEGO/Pybricks manufacturer advertisements using Bleak.

Sending manufacturer advertisements is not supported by Bleak; for Windows
transmission use a separately configured serial BLE bridge instead.
"""
import asyncio,threading
class BLEManager:
    def __init__(self,emit,channel=4,company_id=0x0397):
        self.emit=emit;self.channel=channel;self.company_id=company_id;self.thread=None;self.loop=None;self.stop_event=None
    def start(self):
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def _run(self):
        try:asyncio.run(self._scan())
        except Exception as exc:self.emit("communication_error",{"message":str(exc)},"ble")
    async def _scan(self):
        from bleak import BleakScanner
        self.loop=asyncio.get_running_loop();self.stop_event=asyncio.Event()
        def callback(device,advertisement):
            payload=advertisement.manufacturer_data.get(self.company_id)
            if payload and len(payload)>=4 and payload[:3]==bytes([self.channel,0,0x61]):
                self.emit("signal",{"value":int.from_bytes(payload[3:4],"little",signed=True),"device":device.address},"ble")
        async with BleakScanner(detection_callback=callback):await self.stop_event.wait()
    def close(self):
        if self.loop and self.stop_event:self.loop.call_soon_threadsafe(self.stop_event.set)
        if self.thread:self.thread.join(timeout=2)
