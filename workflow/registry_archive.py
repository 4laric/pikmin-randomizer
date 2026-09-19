"""Operator-run archive of long-done lanes' history; never run by the controller.

  <python> <checkout>/scripts/workflow_module.py registry_archive --root <root> --done-days N [--apply] [--no-vacuum]

Moves events, control.launches and actions of lanes done for more than N (>= 1) days into
output/workflow/registry-archive.sqlite3, then VACUUMs the registry. Without --apply it
only reports what would move. Every record is preserved: it is copied with its sha256,
committed and re-read from the archive before one registry transaction removes it, and
that transaction refuses unless each record is still byte-identical. Each archived lane
keeps a tombstone (lane.archived) naming the run, so an interrupted run is settled later
(resolve()): tombstoned runs count as moved, the others are discarded because their
records never left the registry. A lane is skipped while anything could still act on it:
an in-flight launch, a claimed action, a lease or queued request, an open assignment or a
pending consumer verification. --apply requires a quiesced registry (registry_wal.quiesced).
Readers needing the full history use history()/merged().
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from .handoff import Rejected, require

IN_FLIGHT = ('intent', 'spawned', 'running', 'exiting')
SCHEMA = ('CREATE TABLE IF NOT EXISTS archive (section TEXT NOT NULL, key TEXT NOT NULL, lane TEXT, run TEXT NOT NULL, '
          'body TEXT NOT NULL, sha256 TEXT NOT NULL, source_index INTEGER, PRIMARY KEY(section, key))',
          'CREATE TABLE IF NOT EXISTS archive_runs (run TEXT PRIMARY KEY, at REAL NOT NULL, root TEXT NOT NULL, '
          'cutoff REAL NOT NULL, lanes TEXT NOT NULL, counts TEXT NOT NULL, status TEXT NOT NULL)')


def default_path(root):
    return Path(root) / 'output/workflow/registry-archive.sqlite3'


def sha(body):
    return hashlib.sha256(body.encode()).hexdigest()


def done_at(lane, latest):
    """Latest recorded activity of a done lane; the age test uses the newest, never the oldest."""
    stamps = [lane.get(k) for k in ('integrated_at', 'progress_at', 'heartbeat_at', 'handoff_at', 'created_at')]
    return max((s for s in stamps + [latest] if type(s) in (int, float)), default=None)


def plan(state, cutoff):
    """{lanes, skipped, events[(index, event)], launches{id: record}, actions{id: record}}."""
    launches, actions = state.get('control', {}).get('launches', {}), state.get('actions', {})
    busy = {}
    for item in launches.values():
        if item.get('status') in IN_FLIGHT: busy.setdefault(item['lane'], 'launch in flight')
    for action in actions.values():
        if action.get('status') == 'claimed': busy.setdefault(action['lane'], 'claimed action')
    for collection in ('leases', 'queue'):
        for row in state.get(collection, {}).values(): busy.setdefault(row.get('lane'), collection + ' entry')
    for row in state.get('throughput', {}).get('assignments', {}).values():
        if row.get('status') in ('assigned', 'dispatched', 'parked'): busy.setdefault(row.get('lane'), 'open assignment')
    pending = {v.get('launch') for v in state.get('consumer_verifications', {}).values() if v.get('status') == 'pending'}
    for key in {launches[i]['lane'] for i in pending if i in launches}: busy.setdefault(key, 'pending consumer verification')
    latest = {}
    for event in state['events']:
        if type(event.get('at')) in (int, float):
            latest[event.get('lane')] = max(event['at'], latest.get(event.get('lane'), event['at']))
    lanes, skipped = set(), {}
    for key, lane in state['lanes'].items():
        if lane.get('state') != 'done': continue
        at = done_at(lane, latest.get(key))
        if at is None or at > cutoff: continue
        if key in busy: skipped[key] = busy[key]; continue
        lanes.add(key)
    events = [(i, e) for i, e in enumerate(state['events']) if e.get('lane') in lanes]
    launches = {k: v for k, v in launches.items() if v.get('lane') in lanes}
    actions = {k: v for k, v in actions.items() if v.get('lane') in lanes}
    held = {e.get('lane') for _, e in events} | {v.get('lane') for v in [*launches.values(), *actions.values()]}
    return dict(lanes=sorted(lanes & held), skipped=skipped, events=events, launches=launches, actions=actions)


def rows(selection, run):
    """(section, key, lane, body, source index) for every record of a plan."""
    result = [('events', '%s:%d' % (run, i), e.get('lane'), json.dumps(e), i) for i, e in selection['events']]
    result += [('control.launches', k, v.get('lane'), json.dumps(v), None) for k, v in selection['launches'].items()]
    result += [('actions', k, v.get('lane'), json.dumps(v), None) for k, v in selection['actions'].items()]
    return result


def summary(selection):
    return dict(lanes=len(selection['lanes']), skipped=selection['skipped'], events=len(selection['events']),
                launches=len(selection['launches']), actions=len(selection['actions']))


def committed(state):
    """Runs whose removal committed in the registry: their lanes carry the tombstones."""
    return {t.get('run') for lane in state['lanes'].values() for t in lane.get('archived') or ()}


def resolve(db, state):
    """Settle interrupted runs: tombstoned ones moved, the rest never left the registry."""
    for (run,) in db.execute("SELECT run FROM archive_runs WHERE status='copied'").fetchall():
        if run in committed(state):
            db.execute("UPDATE archive_runs SET status='moved' WHERE run=?", (run,))
        else:
            db.execute('DELETE FROM archive WHERE run=?', (run,))
            db.execute("UPDATE archive_runs SET status='abandoned' WHERE run=?", (run,))


def mark(path, run, status):
    db = sqlite3.connect(path, timeout=30)
    try:
        if status == 'abandoned': db.execute('DELETE FROM archive WHERE run=?', (run,))
        db.execute('UPDATE archive_runs SET status=? WHERE run=?', (status, run)); db.commit()
    finally:
        db.close()


def copy_out(path, root, run, now, cutoff, selection, state):
    """Phase 1: commit the copies, then re-read every one and compare its hash."""
    records = rows(selection, run)
    db = sqlite3.connect(path, timeout=30)
    try:
        for statement in SCHEMA: db.execute(statement)
        db.execute('BEGIN IMMEDIATE')
        resolve(db, state)
        for section, key, lane, body, index in records:
            old = db.execute('SELECT run FROM archive WHERE section=? AND key=?', (section, key)).fetchone()
            require(old is None, 'Archive already holds %s record %s (run %s)' % (section, key, old and old[0]))
            db.execute('INSERT INTO archive VALUES (?,?,?,?,?,?,?)', (section, key, lane, run, body, sha(body), index))
        db.execute('INSERT INTO archive_runs VALUES (?,?,?,?,?,?,?)', (run, now, str(root), cutoff,
                   json.dumps(selection['lanes']), json.dumps(summary(selection)), 'copied'))
        db.commit()
        for section, key, lane, body, index in records:
            row = db.execute('SELECT body, sha256 FROM archive WHERE section=? AND key=?', (section, key)).fetchone()
            require(row is not None and row[0] == body and sha(row[0]) == row[1],
                    'Archive copy of %s %s did not verify' % (section, key))
    except BaseException:
        if db.in_transaction: db.rollback()
        raise
    finally:
        db.close()
    return len(records)


def remove(reg, run, now, path, cutoff, selection):
    """Phase 2, one registry transaction: remove only records still identical to their copies."""
    with reg.transaction() as state:
        current = plan(state, cutoff)
        require(current['lanes'] == selection['lanes'] and summary(current) == summary(selection) and
                all(json.dumps(state['events'][i]) == json.dumps(e) for i, e in selection['events']) and
                all(json.dumps(state['control']['launches'].get(k)) == json.dumps(v) for k, v in selection['launches'].items()) and
                all(json.dumps(state['actions'].get(k)) == json.dumps(v) for k, v in selection['actions'].items()),
                'Registry changed since the archive copy; nothing was removed, rerun')
        state['wake_revision'] = state.get('wake_revision', len(state['events']))
        drop = {i for i, _ in selection['events']}
        state['events'] = [e for i, e in enumerate(state['events']) if i not in drop]
        for key in selection['launches']: del state['control']['launches'][key]
        for key in selection['actions']: del state['actions'][key]
        for key in selection['lanes']:
            state['lanes'][key].setdefault('archived', []).append(dict(run=run, at=now, archive=str(path),
                events=sum(e.get('lane') == key for _, e in selection['events']),
                launches=sum(v.get('lane') == key for v in selection['launches'].values()),
                actions=sum(v.get('lane') == key for v in selection['actions'].values())))


def archive(reg, done_days, *, path=None, apply=False, vacuum=True, now=None, probe=None):
    require(type(done_days) in (int, float) and done_days >= 1, 'done-days must be at least 1')
    now = reg.clock() if now is None else now
    cutoff = now - done_days * 86400
    path = Path(path) if path else default_path(reg.root)
    state = reg.snapshot()
    selection = plan(state, cutoff)
    report = dict(archive=str(path), cutoff=cutoff, applied=False, **summary(selection))
    if not apply or not selection['lanes']:
        return report
    from .registry_wal import quiesced
    reason = quiesced(reg, probe)
    require(reason is None, 'Refused: ' + str(reason))
    run = uuid.uuid4().hex
    copied = copy_out(path, reg.root, run, now, cutoff, selection, state)
    try:
        remove(reg, run, now, path, cutoff, selection)
    except Rejected:
        mark(path, run, 'abandoned')  # The removal rolled back: every record is still in the registry.
        raise
    mark(path, run, 'moved')
    before = reg.path.stat().st_size
    if vacuum:
        db = sqlite3.connect(reg.path, timeout=30)
        try: db.execute('VACUUM')
        finally: db.close()
    return dict(report, applied=True, run=run, copied=copied, bytes_before=before, bytes_after=reg.path.stat().st_size)


def history(root, *, path=None, lane=None, state=None):
    """Archived records as {events: [...], launches: {...}, actions: {...}}; empty without an archive.

    Only moved runs count, plus interrupted runs the given registry state tombstones."""
    path = Path(path) if path else default_path(root)
    result = dict(events=[], launches={}, actions={})
    if not path.is_file():
        return result
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=30)
    try:
        runs = {r for (r,) in db.execute("SELECT run FROM archive_runs WHERE status='moved'")}
        runs |= committed(state) if state is not None else set()
        query = 'SELECT section, key, body, sha256, run FROM archive' + (' WHERE lane=?' if lane else '') + ' ORDER BY rowid'
        for section, key, body, digest, run in db.execute(query, (lane,) if lane else ()):
            if run not in runs: continue
            require(sha(body) == digest, 'Archived %s record %s fails its hash' % (section, key))
            value = json.loads(body)
            if section == 'events': result['events'].append(value)
            else: result['launches' if section == 'control.launches' else 'actions'][key] = value
    finally:
        db.close()
    return result


def merged(root, state, *, path=None):
    """A copy of state with archived events (ordered by time), launches and actions restored."""
    old = history(root, path=path, state=state)
    if not any(old.values()):
        return state
    result = dict(state, events=sorted(old['events'] + list(state['events']), key=lambda e: e.get('at') or 0),
                  actions={**old['actions'], **state.get('actions', {})})
    control = dict(state.get('control', {}))
    control['launches'] = {**old['launches'], **control.get('launches', {})}
    result['control'] = control
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--done-days', type=float, required=True)
    parser.add_argument('--archive', type=Path, help='Defaults to <root>/output/workflow/registry-archive.sqlite3')
    parser.add_argument('--apply', action='store_true', help='Move and vacuum; without it only report')
    parser.add_argument('--no-vacuum', action='store_true')
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    try:
        report = archive(Registry(root / 'output/workflow/registry.sqlite3', root), args.done_days,
                         path=args.archive, apply=args.apply, vacuum=not args.no_vacuum)
    except (Rejected, OSError, sqlite3.Error) as exc:
        print('Refused: ' + str(exc))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
