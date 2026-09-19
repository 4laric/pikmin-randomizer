"""Bounded event waits for controllers and integration mailboxes; never dispatches."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from contextlib import closing


class EventWaiter:
    def __init__(self, database, paths=(), stop=None, *, clock=time.monotonic, sleep=time.sleep):
        self.database = Path(database)
        self.paths = tuple(Path(p) for p in paths)
        self.stop = Path(stop) if stop else None
        self.clock, self.sleep = clock, sleep

    def token(self):
        # Read-only connection: waiting must not contend for a writer lease or wake itself.
        with closing(sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)) as db:
            db.execute('BEGIN')
            schema = db.execute("SELECT json_extract(body,'$.schema') FROM registry WHERE id=1").fetchone()
            if schema and schema[0] == 2:  # documents-v1: wake_revision lives in the meta document.
                row = db.execute("SELECT coalesce(json_extract(body,'$.wake_revision'),(SELECT sum(json_array_length(body)) "
                                 "FROM registry_documents WHERE section='[\"events\"]')) FROM registry_documents "
                                 "WHERE section='' AND key=''").fetchone()
            else:
                row = db.execute("SELECT coalesce(json_extract(body,'$.wake_revision'),"
                                 "json_array_length(body,'$.events')) FROM registry WHERE id=1").fetchone()
        files = []
        for path in self.paths:
            children = sorted(path.iterdir()) if path.is_dir() else [path]
            for child in children:
                try:
                    stat = child.stat()
                    files.append((str(child), stat.st_mtime_ns, stat.st_size))
                except FileNotFoundError:
                    files.append((str(child), None, None))
        return hashlib.sha256(json.dumps([row, files], sort_keys=True).encode()).hexdigest()

    def wait(self, timeout=15, cursor=None):
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 <= timeout <= 60:
            raise ValueError('Event wait timeout must be between 0 and 60 seconds')
        cursor = cursor or self.token()
        deadline = self.clock() + timeout
        while True:
            if self.stop and self.stop.exists():
                return {'reason': 'stopped', 'cursor': cursor}
            latest = self.token()
            if latest != cursor:
                return {'reason': 'changed', 'cursor': latest}
            remaining = deadline - self.clock()
            if remaining <= 0:
                return {'reason': 'timeout', 'cursor': latest}
            self.sleep(min(.5, remaining))
