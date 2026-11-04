"""LED effect commands delegated to the configured communication transport."""
class LEDManager:
    def __init__(self,send):self.send=send
    def effect(self,signal):self.send(int(signal))
