"""Shared runtime state."""
class StateManager:
    def __init__(self): self.values={"scene":"", "camera":False, "ai":False, "ble":False, "serial":False}
    def set(self,key,value): self.values[key]=value
    def get(self,key,default=None): return self.values.get(key,default)
    def matches(self,conditions): return all(self.get(k)==v for k,v in conditions.items())
