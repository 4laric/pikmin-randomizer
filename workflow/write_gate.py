"""FIFO admission for writers sharing a process; SQLite still fences all clients."""
from collections import deque
from pathlib import Path
import threading

_lock=threading.Lock()
_gates={}


class Gate:
    def __init__(self):
        self.condition=threading.Condition()
        self.waiters=deque()

    def acquire(self):
        identity=threading.get_ident()
        with self.condition:
            if identity in self.waiters:raise RuntimeError('Nested registry writer gate')
            self.waiters.append(identity)
            try:
                while self.waiters[0]!=identity:self.condition.wait()
            except BaseException:
                self.waiters.remove(identity);self.condition.notify_all();raise

    def release(self):
        with self.condition:
            if not self.waiters or self.waiters[0]!=threading.get_ident():
                raise RuntimeError('Registry writer gate ownership changed')
            self.waiters.popleft();self.condition.notify_all()


def gate(path):
    key=str(Path(path).resolve()).casefold()
    with _lock:return _gates.setdefault(key,Gate())
