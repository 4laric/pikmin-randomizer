"""Registry-side helper for setup-lanes.ps1 (reads only; writes request JSON files) and the kickoff.

  request  : validate one lane and write output/reduced/<lane>/{provision,configure}-request.json
             for `pikmin2_workflow.py provision-pool-lane` / `configure-lane-launch`.
  kickoff  : plan the first launch of configured reduced lanes (Registry.plan_launch with a fresh
             OpenCode session), the same intent record every wake path writes. The controller
             dispatches it when it runs. No other path starts a new ready lane in reduced mode
             (throughput/pool dispatch and the shepherd are off).
  validate : run the controller's own config/launch checks against the merged config.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

RELEASE = Path(__file__).resolve().parents[2]  # the release worktree (or checkout) this toolkit ships in
HERE = Path(__file__).resolve().parent


def release(path):
    sys.path.insert(0, str(path))
    import workflow
    if Path(workflow.__file__).resolve().parent != (path / 'workflow').resolve():
        raise SystemExit('Refused: workflow package resolved outside ' + str(path))


def head(tree):
    out = subprocess.run(['git', '-C', str(tree), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
    dirty = subprocess.run(['git', '-C', str(tree), 'status', '--porcelain'], capture_output=True, text=True, check=True)
    return out.stdout.strip(), dirty.stdout.strip()


def source(tree):
    sha, dirty = head(tree)
    if dirty:
        raise SystemExit(f'Refused: {tree} is dirty')
    return dict(base=sha, head=sha, commits=[], dirty='', worktree=str(tree))


def acceptance(brief):
    text = Path(brief).read_text(encoding='utf-8')
    block = text.split('## Definition of done', 1)[1].split('\n## ', 1)[0]
    items = [l[2:].strip() for l in block.splitlines() if l.startswith('- ')]
    if not items:
        raise SystemExit('No Definition of done bullets in ' + str(brief))
    return items


def pick_previous(reg, state, key, preference, taken):
    from workflow.worker_capacity import reusable, occupant
    workers = state.get('throughput', {}).get('workers', {})
    assignments = state.get('throughput', {}).get('assignments', {}).values()
    launches = state.get('control', {}).get('launches', {}).values()
    for worker in preference:
        if worker in taken or worker not in workers:
            continue
        if any(a['worker_id'] == worker and a['status'] in ('assigned', 'dispatched') for a in assignments):
            continue
        probe = dict(lane=key, worker_id=worker, state='ready')
        if occupant(reg, state, probe) is not None:
            continue
        ok = []
        for l in state['lanes'].values():
            if l['worker_id'] != worker or not l['task_id'].startswith('opencode:') or len(l['task_id']) <= 9:
                continue
            disposed = l['state'] == 'done' and (l.get('integration') or l.get('review_disposition') or
                                                 l.get('cancelled_before_start') or l.get('superseded_planning'))
            if not (disposed or reusable(reg, state, l)):
                continue
            if any(x['lane'] == l['lane'] and x['status'] in ('intent', 'spawned', 'running') for x in launches):
                continue
            if not reg.recovery_safe(state, l):
                continue
            ok.append(l)
        if ok:
            return max(ok, key=lambda l: l.get('created_at') or 0)
    raise SystemExit('Refused: no free authorized pool worker left in worker_preference for ' + key)


def cmd_request(a, reg):
    from workflow.remote import check_remote_ownership
    from workflow.handoff import Rejected
    m = json.loads(a.manifest.read_text(encoding='utf-8'))
    spec = m['lanes'][a.lane]
    issue = a.issue or spec.get('issue')
    if type(issue) is not int or issue <= 0:
        raise SystemExit(f'Refused: {a.lane} has no issue in lanes.json (suggested: {spec.get("suggested_issue")})')
    lane_dir = reg.root / 'output/reduced' / a.lane
    state = reg.snapshot()
    configure = dict(key=a.lane, root=f'output/reduced/{a.lane}/root', output=f'output/reduced/{a.lane}/run',
                     brief=f'output/reduced/{a.lane}/brief.md', config=f'output/reduced/{a.lane}/opencode.json',
                     legacy_supervisors=[])
    (lane_dir / 'configure-request.json').write_text(json.dumps(configure, indent=1), encoding='utf-8')
    if a.lane in state['lanes']:
        (lane_dir / 'provision-request.json').unlink(missing_ok=True)
        print(json.dumps(dict(lane=a.lane, registered=True, worker=state['lanes'][a.lane]['worker_id'])))
        return 0
    owned = spec['owned_files']
    problems = []
    for other in state['lanes'].values():
        if other['state'] == 'done':
            continue
        if other['issue'] == issue:
            problems.append(f'issue #{issue} held by unfinished lane {other["lane"]}')
        clash = {f.casefold() for f in other['owned_files']} & {f.casefold() for f in owned}
        if clash:
            problems.append(f'owned files {sorted(clash)} held by unfinished lane {other["lane"]} ({other["state"]})')
    try:
        check_remote_ownership(state, issue, owned)
    except Rejected as e:
        problems.append(str(e))
    if problems:
        raise SystemExit('Refused ' + a.lane + ':\n  ' + '\n  '.join(problems))
    taken = {l['worker_id'] for l in state['lanes'].values() if l['lane'].startswith('rd-') and l['state'] != 'done'}
    prev = pick_previous(reg, state, a.lane, m['worker_preference'], taken)
    record = dict(lane=a.lane, issue=issue, owner=prev['owner'], scope=spec['scope'],
                  target_level=m['target_level'], milestone=m['milestone'],
                  next_action=f'Read output/reduced/{a.lane}/brief.md and start the slice',
                  owned_files=owned, acceptance=acceptance(lane_dir / 'brief.md'),
                  root=source(lane_dir / 'root'),
                  native=source(lane_dir / 'native') if spec['kind'] == 'native' else None)
    request = dict(previous_lane=prev['lane'], record=record)
    (lane_dir / 'provision-request.json').write_text(json.dumps(request, indent=1), encoding='utf-8')
    print(json.dumps(dict(lane=a.lane, previous_lane=prev['lane'], worker=prev['worker_id'], issue=issue,
                          acceptance=len(record['acceptance']))))
    return 0


INSTRUCTION = ('Reduced-mode trial slice. Read your brief (it is authoritative for scope, branches, tests and '
               'finish), then `inspect lane <key>` for your registered owned_files and acceptance; the handoff '
               'slice_acceptance criteria must equal the registered acceptance strings exactly.')


def cmd_kickoff(a, reg):
    config = json.loads(a.config.read_text(encoding='utf-8-sig'))
    specs = reg.snapshot(sections=[('throughput_runtime', 'launch_specs')]).get('throughput_runtime', {}).get('launch_specs', {})
    rc = 0
    for key in a.lanes:
        if key not in specs and key not in config.get('lanes', {}):
            print(f'{key}: refused, no launch config/spec'); rc = 2; continue
        if a.dry_run:
            print(f'{key}: would plan operator-start launch'); continue
        try:
            item = reg.plan_launch(key, 'operator-start:reduced-mode', INSTRUCTION, config['models'],
                                   carry=dict(fresh_session=True))
            print(f'{key}: intent {item["id"]} status={item["status"]} fresh_session={item.get("fresh_session")}')
        except Exception as e:  # Rejected / Parked: report and continue with the others.
            print(f'{key}: refused: {e}'); rc = 2
    return rc


def cmd_validate(a, reg):
    """Controller-side checks: pikmin2_controller.main's config checks, Controller construction,
    launch-spec merge, Controller.available(), managed_config.output_access for every reduced lane."""
    from workflow.controller import Controller
    from workflow.managed_config import output_access
    from workflow.handoff import local_path
    config = json.loads(a.config.read_text(encoding='utf-8-sig'))
    interval = max(1, min(30, config.get('interval', 15)))
    spacing = config.get('min_tick_seconds', 5)
    assert type(spacing) in (int, float) and 0 <= spacing <= interval, 'min_tick_seconds'
    assert type(config.get('wake_on_registry_events', False)) is bool
    c = Controller(reg, config, spawn=lambda d: (_ for _ in ()).throw(RuntimeError('no spawn in validate')))
    specs = reg.snapshot(sections=[('throughput_runtime', 'launch_specs')]).get('throughput_runtime', {}).get('launch_specs', {})
    c.config['lanes'].update(specs)
    state = reg.snapshot()
    bad = 0
    for key in sorted(k for k in c.config['lanes']):
        e = c.config['lanes'][key]
        lane = state['lanes'].get(key)
        paths = {f: local_path(reg.root, e[f]) for f in ('root', 'output', 'brief', 'config')}
        checks = dict(registered=lane is not None,
                      root_matches=lane is not None and paths['root'] == local_path(reg.root, lane['root']['worktree']),
                      files=paths['root'].is_dir() and paths['brief'].is_file() and paths['config'].is_file(),
                      managed_config=output_access(str(paths['config']), str(paths['output']), reg.root, str(paths['brief'])) is not None,
                      available=c.available(key))
        bad += not all(checks.values())
        print(key, 'OK' if all(checks.values()) else 'FAIL', checks)
    print('configured lanes:', len(c.config['lanes']))
    return 1 if bad else 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('command', choices=('request', 'kickoff', 'validate'))
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--db', type=Path)
    p.add_argument('--release', type=Path, default=RELEASE)
    p.add_argument('--manifest', type=Path, help='default: <root>/output/reduced/lanes.json')
    p.add_argument('--config', type=Path)
    p.add_argument('--lane')
    p.add_argument('--issue', type=int)
    p.add_argument('--lanes', nargs='*', default=[])
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args(argv)
    release(a.release.resolve())
    from workflow.registry import Registry
    root = a.root.resolve()
    a.manifest = a.manifest or root / 'output/reduced/lanes.json'
    a.config = a.config or root / 'output/workflow/controller/config.json'
    reg = Registry((a.db or root / 'output/workflow/registry.sqlite3').resolve(), root)
    return dict(request=cmd_request, kickoff=cmd_kickoff, validate=cmd_validate)[a.command](a, reg)


if __name__ == '__main__':
    raise SystemExit(main())
