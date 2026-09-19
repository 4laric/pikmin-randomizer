"""Bounded read-only input cache; metadata changes invalidate, full reread at 5m.

Publication and dispatch still hash bytes independently at their trust boundary.
"""
import hashlib
import json
import threading
import time
from collections import OrderedDict

_entries = OrderedDict()
_lock = threading.Lock()


def read(path, now=None):
    now = time.monotonic() if now is None else now
    path = path.resolve()
    stat = path.stat()
    stamp = (stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size)
    with _lock:
        old = _entries.get(str(path))
        if old and old[0] == stamp and 0 <= now-old[1] < 300:
            _entries.move_to_end(str(path));return old[2],old[3]
    raw = path.read_bytes()
    value, sha = json.loads(raw.decode('utf-8-sig')),hashlib.sha256(raw).hexdigest()
    with _lock:
        _entries[str(path)] = (stamp,now,value,sha)
        while len(_entries)>2048:_entries.popitem(last=False)
    return value,sha
