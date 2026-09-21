"""Registry journal handling: operator-run mode switch plus bounded WAL maintenance.

Mode switch (operator only; not a scheduler action):

  <python> <checkout>/scripts/workflow_module.py registry_wal --root <root> [--mode wal|delete] [--apply]

Without --apply it only reports the current mode and whether the registry is quiesced.
With --apply: refuse unless quiesced (the recorded controller is confirmed stopped and no
other connection holds the database), set PRAGMA journal_mode, then verify that a full
snapshot is byte-identical, a mode=ro reader and the wake-up waiter still read it, and
quick_check passes. Any failed check restores the previous mode and refuses.
WAL keeps BEGIN IMMEDIATE writer fencing; readers stop blocking commits. The mode is
persistent in the file, so every process (including older releases) uses it after reopen.

Bounded WAL maintenance (safe during live operation):

  <python> <checkout>/scripts/workflow_module.py registry_wal --root <root> --maintain [--limit-bytes N]

A continuously-written WAL whose automatic checkpoint is starved by concurrent readers
never resets and grows without bound; every later commit and read then pays WAL read
amplification, which is the dominant registry writer-lock cost. maintain() is a
bounded, fail-closed housekeeping pass: when the WAL exceeds the limit it runs PASSIVE
then TRUNCATE checkpoints with a bounded busy timeout and reports the outcome. It never
raises on SQLITE_BUSY and never deletes rows, so it is safe to run from the controller's
independent monitor thread (start_monitor) as well as by hand.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time

from .handoff import Rejected, require

DEFAULT_LIMIT_BYTES = 64 * 1024 * 1024
DEFAULT_BUSY_TIMEOUT_MS = 2000


def sizes(path):
    """Main database and WAL byte sizes without opening a connection or taking a lock."""
    path = Path(path)
    wal = path.with_name(path.name + '-wal')
    return dict(main=path.stat().st_size if path.exists() else 0,
                wal=wal.stat().st_size if wal.exists() else 0)


def maintain(reg, *, limit_bytes=DEFAULT_LIMIT_BYTES, busy_timeout_ms=DEFAULT_BUSY_TIMEOUT_MS):
    """Bounded WAL housekeeping. Returns a report; never raises on SQLITE_BUSY.

    A WAL at or below limit_bytes is left untouched. Above it, PASSIVE checkpoint first
    (always safe, never blocks readers or writers), then TRUNCATE to release the file when
    no reader is pinning an old snapshot. The result records forced bytes moved and, when
    the file could not be truncated because a reader was busy, that outcome as data, not
    an error: the next pass will retry.
    """
    require(type(limit_bytes) is int and limit_bytes > 0, 'WAL limit must be a positive integer')
    require(type(busy_timeout_ms) is int and 1 <= busy_timeout_ms <= 60000, 'WAL busy timeout must be 1-60000 ms')
    before = sizes(reg.path)
    report = dict(at=reg.clock(), path=str(reg.path), journal=journal(reg.path),
                  limit_bytes=limit_bytes, before=before, after=None, action='none',
                  passive=None, truncate=None)
    if report['journal'] != 'wal' or before['wal'] <= limit_bytes:
        report['after'] = before
        return report
    db = sqlite3.connect(reg.path, timeout=busy_timeout_ms / 1000.0)
    try:
        db.execute('PRAGMA busy_timeout=%d' % busy_timeout_ms)
        passive = db.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
        report['passive'] = list(passive)
        report['action'] = 'passive'
        if sizes(reg.path)['wal'] > limit_bytes:
            truncate = db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            report['truncate'] = list(truncate)
            report['action'] = 'truncate'
    except sqlite3.Error as exc:  # A busy or locked WAL is a report, never a failure.
        report['error'] = str(exc)
    finally:
        db.close()
    report['after'] = sizes(reg.path)
    return report


def start_monitor(controller):
    """Independent bounded-cadence WAL maintenance; never dispatches, launches or kills."""
    existing = getattr(controller, '_wal_monitor', None)
    if existing is not None:
        return existing
    stop = threading.Event()
    controller._wal_monitor = stop
    options = controller.config.get('registry_wal', {})
    interval = max(30, float(options.get('interval_seconds', 60)))
    limit = options.get('limit_bytes', DEFAULT_LIMIT_BYTES)
    busy_timeout_ms = options.get('busy_timeout_ms', DEFAULT_BUSY_TIMEOUT_MS)
    require(type(limit) is int and limit > 0, 'registry_wal.limit_bytes must be a positive integer')

    def monitor():
        from .runner import write
        while not stop.is_set():
            started = time.monotonic()
            try:
                report = maintain(controller.reg, limit_bytes=limit, busy_timeout_ms=busy_timeout_ms)
                if report['action'] != 'none':
                    write(controller.base / 'registry-wal.json', report, durable=False)
            except Exception as exc:  # Maintenance must never end the controller.
                write(controller.base / 'registry-wal-error.json',
                      dict(at=controller.reg.clock(), error=str(exc), type=type(exc).__name__))
            stop.wait(max(1, interval - (time.monotonic() - started)))

    thread = threading.Thread(target=monitor, name='registry-wal-monitor', daemon=True)
    thread.start()
    return stop


def fingerprint(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def journal(path):
    db = sqlite3.connect(path, timeout=5)
    try: return db.execute('PRAGMA journal_mode').fetchone()[0]
    finally: db.close()


def quiesced(reg, probe=None):
    """None when no process can be using the registry; otherwise the refusal reason."""
    from .storage import read_record
    from .processes import probe as default
    meta = read_record(reg, (), '') or {}
    controller = (meta.get('control') or {}).get('controller')
    if controller and (probe or default)(controller) != 'dead':
        return 'Recorded controller %s is not confirmed stopped; stop it (and its restart wrapper) first' % (
            controller.get('pid'),)
    db = sqlite3.connect(reg.path, timeout=2)
    try:
        db.execute('BEGIN EXCLUSIVE'); db.rollback()
    except sqlite3.OperationalError as exc:
        return 'Another connection holds the registry (%s); stop workers and CLIs first' % exc
    finally:
        db.close()
    return None


def verify(reg, expected):
    """Every client kind still reads the same committed state."""
    from .wakeup import EventWaiter
    require(fingerprint(reg.snapshot()) == expected, 'Snapshot changed across the journal switch')
    ro = sqlite3.connect(reg.path.as_uri() + '?mode=ro', uri=True, timeout=5)
    try:
        require(json.loads(ro.execute('SELECT body FROM registry WHERE id=1').fetchone()[0]).get('root') == str(reg.root),
                'Read-only client cannot read the header')
        require(ro.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'quick_check failed')
    finally:
        ro.close()
    EventWaiter(reg.path).token()


def switch(reg, mode='wal', *, apply=False, probe=None):
    require(mode in ('wal', 'delete'), 'Journal mode must be wal or delete')
    before = journal(reg.path)
    reason = quiesced(reg, probe)
    report = dict(path=str(reg.path), journal_mode=before, target=mode, quiesced=reason is None, reason=reason, applied=False)
    if not apply or before == mode:
        return report
    require(reason is None, 'Refused: ' + str(reason))
    expected = fingerprint(reg.snapshot())
    db = sqlite3.connect(reg.path, timeout=5)
    try:
        result = db.execute('PRAGMA journal_mode=' + mode).fetchone()[0]
    finally:
        db.close()
    try:
        require(result == mode and journal(reg.path) == mode, 'Journal mode did not change (got %s)' % result)
        verify(reg, expected)
    except (Rejected, OSError, sqlite3.Error) as exc:
        db = sqlite3.connect(reg.path, timeout=5)
        try: db.execute('PRAGMA journal_mode=' + before)
        finally: db.close()
        raise Rejected('Journal switch verification failed; restored %s: %s' % (before, exc))
    return dict(report, journal_mode=mode, previous=before, applied=True, verified=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=('wal', 'delete'), default='wal')
    parser.add_argument('--apply', action='store_true', help='Switch; without it only report')
    parser.add_argument('--maintain', action='store_true',
                        help='Run one bounded WAL checkpoint pass over the live registry')
    parser.add_argument('--limit-bytes', type=int, default=DEFAULT_LIMIT_BYTES,
                        help='WAL size above which maintenance checkpoints (default %d)' % DEFAULT_LIMIT_BYTES)
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    if args.maintain:
        print(json.dumps(maintain(reg, limit_bytes=args.limit_bytes), indent=2))
        return 0
    try:
        report = switch(reg, args.mode, apply=args.apply)
    except (Rejected, OSError, sqlite3.Error) as exc:
        print('Refused: ' + str(exc))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
