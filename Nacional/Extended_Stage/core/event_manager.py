"""Thread-safe event bus; callbacks execute on the application thread."""
from dataclasses import dataclass, field
from queue import Queue, Empty
from time import monotonic

@dataclass
class Event:
    name: str
    data: dict = field(default_factory=dict)
    source: str = "internal"
    priority: int = 0
    timestamp: float = field(default_factory=monotonic)

class EventManager:
    def __init__(self):
        self.queue = Queue()
        self.history = []
        self.listeners = []

    def emit(self, name, data=None, source="internal", priority=0):
        self.queue.put(Event(name, data or {}, source, priority))

    def subscribe(self, callback):
        self.listeners.append(callback)

    def drain(self, limit=100):
        batch=[]
        for _ in range(limit):
            try: batch.append(self.queue.get_nowait())
            except Empty: break
        for event in sorted(batch, key=lambda e: (-e.priority,e.timestamp)):
            self.history.append(event)
            self.history=self.history[-100:]
            for callback in list(self.listeners):
                try: callback(event)
                except Exception:
                    import logging
                    logging.exception("Event listener failed: %s",event.name)
