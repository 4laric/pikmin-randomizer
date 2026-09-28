"""Retire every non-reduced lane from controller supervision before a reduced-mode trial.

Why this is enough (read from release d82fa4ebd44c):
  * Every wake path plans a launch only for a lane present in controller.config['lanes']
    (consumer_wakeup.gate -> 'not_configured', integration_wakeup/owner, approvals.tick,
    outcome_recovery, provider_recovery.recover, resource_wakeup, action_routing,
    handoff_representation, integration_repair, shared_decisions, blocked_followup,
    setup_healing, Controller.dependencies, shepherd 'Unknown lane').
  * controller.config['lanes'] = config.json 'lanes' (now {}) updated each tick with
    registry throughput_runtime.launch_specs.  So removing the launch_specs entries is the
    retirement: there is no lane field ("parked", "capacity_parked", "wake_after") that the
    wakes honour more strongly.  PIKMIN2_CONTROLLER.md: "Lanes without a controller launch
    config have no wake path."
  * A still-pending launch intent of a retired lane would crash every tick
    (Controller.dispatch_pending -> available() -> KeyError), so never-started intents are
    cancelled exactly the way workflow/planner_reclaim.py cancels a never-launched helper
    (launch/assignment/job status 'cancelled' + cancellation reason).  Anything that ever
    started (process, attempts, bound generation, spawn/runner/start/child file) is refused.
Lane records themselves are NOT modified (states stay blocked/ready/handoff_ready; retired
lanes still hold their issues and owned files in the registry).

Writes only through Registry.transaction (sections API).  Requires the controller STOP file.
Usage:
  py -3.12 retire_old_lanes.py --root <workspace> [--db <registry>] [--dry-run]
  py -3.12 retire_old_lanes.py --root <workspace> --undo <undo.json> [--dry-run]
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time

RELEASE = Path(__file__).resolve().parents[2]  # the release worktree (or checkout) this toolkit ships in
HERE = Path(__file__).resolve().parent
IN_FLIGHT = ('intent', 'spawned', 'running', 'exiting')
OPEN_ASSIGNMENT = ('assigned', 'dispatched')
SECTIONS = [('throughput_runtime', 'launch_specs'), ('control', 'launches'),
            ('throughput', 'assignments'), ('throughput', 'jobs')]
STARTED_FILES = ('spawn.json', 'runner.json', 'start.json', 'child.json', 'session.json', 'result.json')


def load_release(release):
    sys.path.insert(0, str(release))
    import workflow
    if Path(workflow.__file__).resolve().parent != (release / 'workflow').resolve():
        raise SystemExit('Refused: workflow package resolved outside ' + str(release))
    from workflow.registry import Registry
    return Registry


def plan(state, keep, launch_dir):
    specs = state.get('throughput_runtime', {}).get('launch_specs', {})
    remove = sorted(k for k in specs if k not in keep)
    launches = state.get('control', {}).get('launches', {})
    pool = state.get('throughput', {})
    cancel, refuse = [], []
    for identity, item in launches.items():
        if item['lane'] in keep or item['status'] not in IN_FLIGHT:
            continue
        directory = launch_dir / identity
        started = [f for f in STARTED_FILES if (directory / f).exists()]
        if (item['status'] != 'intent' or item.get('process') or item.get('attempts', 0) or
                item.get('bound_generation') or started):
            refuse.append(dict(launch=identity, lane=item['lane'], status=item['status'], started_files=started))
            continue
        cancel.append(identity)
    lanes_of = {launches[i]['lane'] for i in cancel}
    assignments = sorted(a for a, v in pool.get('assignments', {}).items()
                         if v['lane'] in lanes_of and v['status'] in OPEN_ASSIGNMENT)
    jobs = sorted(j for j, v in pool.get('jobs', {}).items()
                  if v['lane'] in lanes_of and v['status'] in ('queued', 'assigned', 'dispatched'))
    lanes = state.get('lanes', {})
    open_lanes = sorted((k, l['state']) for k, l in lanes.items() if l['state'] != 'done' and k not in keep)
    return dict(remove_specs=remove, cancel_launches=cancel, cancel_assignments=assignments,
                cancel_jobs=jobs, refuse=refuse, open_lanes_left_unsupervised=open_lanes,
                kept_specs=sorted(k for k in specs if k in keep))


def backup(db, target):
    if target.exists():
        raise SystemExit(f'Refused: backup {target} already exists; move it aside deliberately first.')
    src = sqlite3.connect(f'file:{db.as_posix()}?mode=ro', uri=True)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
        ok = dst.execute('PRAGMA integrity_check').fetchone()[0]
        if ok != 'ok':
            raise SystemExit('Backup integrity_check failed: ' + ok)
    finally:
        dst.close(); src.close()
    print('Backup written:', target)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--db', type=Path, help='Default <root>/output/workflow/registry.sqlite3')
    p.add_argument('--release', type=Path, default=RELEASE)
    p.add_argument('--keep-from', type=Path, default=HERE / 'reduced-lanes.patch.json',
                   help='JSON whose "lanes" keys are kept (the reduced lanes)')
    p.add_argument('--controller-output', default='output/workflow/controller')
    p.add_argument('--backup', type=Path, help='Default <db dir>/registry.before-reduced-mode.sqlite3')
    p.add_argument('--undo-file', type=Path, help='Default <db dir>/reduced-mode-retire-undo-<stamp>.json')
    p.add_argument('--undo', type=Path, help='Reverse a previous run from its undo JSON')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(argv)
    root = a.root.resolve()
    db = (a.db or root / 'output/workflow/registry.sqlite3').resolve()
    base = root / a.controller_output
    if not (base / 'STOP').exists():
        raise SystemExit(f'Refused: {base / "STOP"} missing; stop the controller first.')
    Registry = load_release(a.release.resolve())
    reg = Registry(db, root)
    if a.undo:
        return undo(reg, a.undo, a.dry_run)
    keep = set(json.loads(a.keep_from.read_text(encoding='utf-8-sig'))['lanes'])
    result = plan(reg.snapshot(sections=SECTIONS + [('lanes',)]), keep, base / 'launches')
    print(json.dumps(dict(keep=sorted(keep), remove_specs_count=len(result['remove_specs']),
                          **{k: v for k, v in result.items() if k != 'remove_specs'}), indent=1))
    print('launch_specs to remove (%d): %s' % (len(result['remove_specs']), ', '.join(result['remove_specs'])))
    if result['refuse']:
        print('Refused: launches of retired lanes that already started; reconcile them first:', json.dumps(result['refuse']))
        return 2
    if a.dry_run:
        print('Dry run: nothing written.')
        return 0
    if not (result['remove_specs'] or result['cancel_launches']):
        print('Nothing to retire (already applied).')
        return 0
    backup(db, (a.backup or db.with_name('registry.before-reduced-mode.sqlite3')))
    record = dict(at=time.time(), db=str(db), keep=sorted(keep), specs={}, launches={}, assignments={}, jobs={})
    stamp = time.strftime('%Y%m%d-%H%M%S')
    undo_file = a.undo_file or db.with_name(f'reduced-mode-retire-undo-{stamp}.json')
    with reg.transaction(sections=SECTIONS + [('lanes',)], append=[('events',)]) as state:
        again = plan(state, keep, base / 'launches')  # Re-check under the writer.
        if again['refuse'] or again['remove_specs'] != result['remove_specs'] or \
                again['cancel_launches'] != result['cancel_launches']:
            raise SystemExit('Refused: registry changed since the preview; rerun.')
        specs = state['throughput_runtime']['launch_specs']
        for key in again['remove_specs']:
            record['specs'][key] = specs.pop(key)
        reason = dict(at=reg.clock(), summary='Reduced-mode trial: lane retired from controller supervision')
        launches = state['control']['launches']
        for i in again['cancel_launches']:
            record['launches'][i] = dict(launches[i])
            launches[i].update(status='cancelled', cancellation=reason)
        pool = state['throughput']
        for i in again['cancel_assignments']:
            record['assignments'][i] = dict(pool['assignments'][i])
            pool['assignments'][i].update(status='cancelled', cancellation=reason)
        for i in again['cancel_jobs']:
            record['jobs'][i] = dict(pool['jobs'][i])
            pool['jobs'][i].update(status='cancelled', cancellation=reason)
        reg.event(state, 'reduced_mode_retired', 'integration', specs=len(record['specs']),
                  launches=sorted(record['launches']), undo=str(undo_file))
        undo_file.write_text(json.dumps(record, indent=1), encoding='utf-8')  # Before commit: never an unrecorded change.
    print(f'Retired: removed {len(record["specs"])} launch specs, cancelled {len(record["launches"])} launch(es), '
          f'{len(record["assignments"])} assignment(s), {len(record["jobs"])} job(s). Undo: {undo_file}')
    return 0


def undo(reg, path, dry_run):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    with reg.transaction(sections=SECTIONS, append=[('events',)]) as state:
        specs = state.setdefault('throughput_runtime', {}).setdefault('launch_specs', {})
        clash = [k for k, v in record['specs'].items() if k in specs and specs[k] != v]
        if clash:
            raise SystemExit('Refused: specs changed since retirement: ' + ', '.join(clash))
        restored = dict(specs=0, launches=0, assignments=0, jobs=0, skipped=[])
        for k, v in record['specs'].items():
            if k not in specs:
                specs[k] = v; restored['specs'] += 1
        for section, rows in (('launches', state['control']['launches']),
                              ('assignments', state['throughput']['assignments']),
                              ('jobs', state['throughput']['jobs'])):
            for i, old in record[section].items():
                cur = rows.get(i)
                if cur is not None and cur.get('status') == 'cancelled' and 'Reduced-mode' in str(cur.get('cancellation')):
                    rows[i] = old; restored[section] += 1
                else:
                    restored['skipped'].append(section + ':' + i)
        print(json.dumps(restored))
        if dry_run:
            raise SystemExit('Dry run: rolled back.')
        reg.event(state, 'reduced_mode_retire_undone', 'integration', undo=str(path))
    print('Undo applied from', path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
