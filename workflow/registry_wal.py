"""Operator-run switch of the registry journal to WAL (or back); never run by the controller.

  <python> <checkout>/scripts/workflow_module.py registry_wal --root <root> [--mode wal|delete] [--apply]

Without --apply it only reports the current mode and whether the registry is quiesced.
With --apply: refuse unless quiesced (the recorded controller is confirmed stopped and no
other connection holds the database), set PRAGMA journal_mode, then verify that a full
snapshot is byte-identical, a mode=ro reader and the wake-up waiter still read it, and
quick_check passes. Any failed check restores the previous mode and refuses.
WAL keeps BEGIN IMMEDIATE writer fencing; readers stop blocking commits. The mode is
persistent in the file, so every process (including older releases) uses it after reopen.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from .handoff import Rejected, require


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
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    try:
        report = switch(Registry(root / 'output/workflow/registry.sqlite3', root), args.mode, apply=args.apply)
    except (Rejected, OSError, sqlite3.Error) as exc:
        print('Refused: ' + str(exc))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
