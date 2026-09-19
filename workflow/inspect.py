"""Read-only answers about the live workflow: what is stuck, why, and what only you can do.

  <python> <checkout>/scripts/workflow_module.py inspect [--root R | --db COPY] <verb> [--json]
  verbs: stuck (default) | needs-you | lane <key> | launches <key> | assignment <lane> | config

The registry is opened with SQLite URI mode=ro plus PRAGMA query_only, decoding only the sections a
verb needs; this module never imports workflow.registry or the writer gate and has no write path, so
it works on a live WAL registry, a backup copy, and while the writer lock is contended. --db reads
any registry file (a copy) without the workspace check."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.parse import quote

from . import storage
from .handoff import Rejected, digest, local_path, require

CONFIG = 'output/workflow/controller/config.json'
REGISTRY = 'output/workflow/registry.sqlite3'
IN_FLIGHT = ('intent', 'spawned', 'running', 'exiting')
TOOLCHAIN = re.compile(r'\b(toolchain|compiler|g\+\+|gcc|cc1(plus)?|mingw\w*|msys\w*|cmake|ninja|linker)\b', re.I)
MACHINE_SECONDS = 72 * 3600  # A machine-wide ask stays listed this long after it was last raised.
NOTICES = ('unsupervised_lane', 'shared_review_target_dead')
STUCK = [('lanes',), ('leases',), ('queue',), ('control', 'launches'), ('control', 'notices'), ('control', 'shepherd'), ('support_actions',),
         ('delivery_contracts',), ('throughput', 'workstreams'), ('throughput', 'workers'), ('throughput', 'assignments')]
LANE = STUCK + [('consumer_verifications',), ('throughput_runtime', 'launch_specs')]


def read(path, sections=None, root=None):
    """One committed registry version through a read-only connection; undeclared sections are sealed."""
    path = Path(path).resolve()
    require(path.is_file(), 'Registry missing: %s' % path)
    only = None if sections is None else storage.declared(sections)[0]
    def once():
        db = sqlite3.connect('file:%s?mode=ro' % quote(path.as_posix(), safe='/:'), uri=True, timeout=storage.BUSY_TIMEOUT)
        try:
            db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN')
            return storage.fetch(db, only)
        finally:
            db.close()
    descriptor, raw = storage.retry(once, 'registry read')
    state = storage.decode(descriptor, raw, only)
    require(state.get('schema') == 1, 'Unknown registry schema')
    require(root is None or state.get('root') == str(Path(root).resolve()), 'Registry belongs to another workspace')
    if only is not None: storage.seal(state, raw, only)
    return state


class View:
    """The registry reads that shared helpers (autofill._workers, consumer_wakeup.gate) need; no writes."""
    def __init__(self, root, probe=None, clock=time.time):
        from .processes import DeadIdentityCache, probe as live
        self.root, self.clock = Path(root).resolve(), clock
        self.probe = probe or DeadIdentityCache(live, unknown_seconds=5)

    @staticmethod
    def scheduling(state):
        data = dict(state.get('throughput') or {})
        for key in ('workstreams', 'workers', 'jobs', 'assignments'): data.setdefault(key, {})
        return data

    def recovery_safe(self, state, lane):
        queued = state['queue'].values() if 'queue' in state else state.get('requests', [])
        return self.probe(lane['process']) == 'dead' and all(
            self.probe(owner['process']) == 'dead'
            for owner in [*state['leases'].values(), *queued] if owner['lane'] == lane['lane'])

    def evidence(self, value):
        require(isinstance(value, dict), 'Hashed evidence required')
        path = local_path(self.root, value.get('path'))
        require(path.is_file() and digest(path) == value.get('sha256'), 'Missing or changed evidence')
        return path

    def refuse(self, *args, **kwargs):
        raise Rejected('workflow.inspect is read-only')
    transaction = notice = plan_launch = event = refuse


def config(root, path=None):
    """The controller config, read-only; {} when absent."""
    path = Path(path) if path else Path(root) / CONFIG
    if not path.is_file(): return {}
    return json.loads(path.read_text(encoding='utf-8-sig'))


def age(now, at):
    return max(0, now - at) if type(at) in (int, float) else None


def downstream(found, state, key):
    """Blocked/waiting lanes that wait on `key`, directly or through other waiting lanes."""
    def names(k):
        lane = state['lanes'].get(k) or {}
        return {'lane:' + k} | ({'issue:%d' % lane['issue']} if type(lane.get('issue')) is int else set())
    result, frontier = set(), {key}
    while frontier:
        wanted = set().union(*map(names, frontier))
        frontier = {k for k, v in found.items() if k not in result and k != key and set(v) & wanted}
        result |= frontier
    return sorted(result)


def asks(state, now, found, table):
    """Open user_decision/user_asset asks, one per lane and kind, plus machine-wide (toolchain) asks."""
    rows, machine = {}, {}
    for identity, action in state.get('support_actions', {}).items():
        details = action.get('details') or {}
        if action.get('action') != 'external' or details.get('owner') != 'user': continue
        key, required = action.get('key'), str(details.get('required') or action.get('reason') or '')
        lane = state['lanes'].get(key) or {}
        if TOOLCHAIN.search(required):
            if age(now, action.get('at')) is not None and age(now, action['at']) <= MACHINE_SECONDS:
                row = machine.setdefault('toolchain', dict(kind='toolchain', lanes=set(), asked=0, first_at=action['at']))
                row.update(asked=row['asked'] + 1, last_at=max(row.get('last_at', 0), action['at']), required=required)
                row['lanes'].add(key)
            continue
        if lane.get('state') == 'done': continue
        row = rows.setdefault((key, details.get('kind')), dict(kind=details.get('kind'), lane=key, asked=0,
                                                                  first_at=action.get('at'), wordings=set()))
        row['asked'] += 1
        row['wordings'].add(' '.join(required.casefold().split()))
        if (action.get('at') or 0) >= (row.get('last_at') or 0):
            row.update(last_at=action.get('at'), required=required, action=identity)
    result = []
    for row in rows.values():
        waiting = downstream(found, state, row['lane'])
        result.append(dict(kind=row['kind'], lane=row['lane'], what=row['required'], asked=row['asked'],
            distinct_wordings=len(row['wordings']), age_seconds=age(now, row['first_at']),
            last_asked_seconds=age(now, row['last_at']), downstream=len(waiting), downstream_lanes=waiting[:10],
            next=('Decide, then give the answer to the lane as hashed evidence it can cite (a reviewer lane records '
                  'approvals; there is no operator write command); retire the lane if the answer is no'
                  if row['kind'] == 'user_decision' else
                  'Supply the asset at a stable path, then record its path and sha256 where the lane can cite it')))
    for row in machine.values():
        result.append(dict(kind='toolchain', lane=None, lanes=sorted(row['lanes']), what=row['required'], asked=row['asked'],
            age_seconds=age(now, row['first_at']), last_asked_seconds=age(now, row['last_at']), machine=True,
            next='Check the toolchain on this machine; native builds and fixture reruns fail until it works'))
    return sorted(result, key=lambda r: (-r.get('downstream', 0), -(r['age_seconds'] or 0)))


def needs_you(state, now, *, cfg=None, base=None, probe=None, found=None, table=None):
    """Everything only the operator can resolve, deduplicated, oldest and widest first."""
    from . import blockers
    if found is None: found, table = blockers.index(state)
    items = asks(state, now, found, table)
    requests = state.get('throughput_runtime', {}).get('autofill', {}).get('prerequisite_requests', {})
    for identity, request in requests.items():
        if not request.get('needs_human') or request.get('status') != 'exhausted': continue
        items.append(dict(kind='prerequisite_needs_human', lane=None, lanes=request.get('lanes', []), scope=request.get('scope'),
            what=request['needs_human'].get('reason'), age_seconds=age(now, request['needs_human'].get('at')), request=identity,
            next='Link a producer through prerequisite_queue resolve, or record the user-owned external_input'))
    notices = state.get('control', {}).get('notices', {})
    seen = {}
    for notice in notices.values():
        if notice.get('status') != 'pending' or notice.get('kind') not in NOTICES: continue
        row = seen.setdefault((notice.get('lane'), notice['kind']), dict(kind=notice['kind'], lane=notice.get('lane'), count=0,
                                                                        first_at=notice.get('at'), detail=notice.get('detail')))
        row['count'] += 1
    for row in seen.values():
        detail = row['detail'] if isinstance(row['detail'], dict) else {}
        items.append(dict(kind=row['kind'], lane=row['lane'], what=detail.get('error') or str(detail)[:200],
            age_seconds=age(now, row['first_at']), count=row['count'],
            next=('Configure its launch (configure-lane-launch) or retire the lane' if row['kind'] == 'unsupervised_lane' else
                  'Supervise the routed shared-review owner or reroute shared_review_routing.files')))
    escalated = [n for n in notices.values() if n.get('status') == 'escalated']
    attention = None
    if base is not None and (Path(base) / 'shepherd-attention.json').is_file():
        path = Path(base) / 'shepherd-attention.json'
        try: attention = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError): attention = dict(reason='shepherd-attention.json unreadable')
        attention = dict(attention if isinstance(attention, dict) else {}, written_at=path.stat().st_mtime)
        active = (state.get('control') or {}).get('shepherd') or {}
        if attention.get('action') and attention['action'] != active.get('id'):
            attention = None  # An uncertain shepherd launch that has since finished or been replaced.
        elif attention.get('events') and not escalated:
            attention = None  # Its escalated notices were resolved since.
    if escalated or attention:
        items.append(dict(kind='shepherd_escalation', lane=None, what=(attention or {}).get('reason') or
            '%d notices escalated after repeated shepherd failures' % len(escalated), escalated_notices=len(escalated),
            escalated_kinds=sorted({n['kind'] for n in escalated}), age_seconds=age(now, (attention or {}).get('written_at')),
            next='Read output/workflow/controller/shepherd-attention.json and the escalated notices; resolve or retire them'))
    for identity, row in state.get('packet_requests', {}).items():
        if row.get('status') == 'refused' and 'integration_lines' in str(row.get('error')):
            items.append(dict(kind='packet_refused', lane=(row.get('requested_by') or {}).get('lane'), request=identity,
                what=row.get('error'), age_seconds=age(now, row.get('decided_at')), packet=row.get('packet'),
                next='Declare integration_lines.root in the controller config, land the packet there, then re-request'))
    return sorted(items, key=lambda r: (r['kind'] in ('shepherd_escalation',), -(r.get('downstream') or 0), -(r['age_seconds'] or 0)))


def machine(state, now, *, cfg=None, probe=None):
    """Machine-wide blockers: controller down, RAM or build pause, undeclared integration lines."""
    result = []
    control = state.get('control', {})
    identity = control.get('controller')
    if probe is not None and identity:
        health = probe(identity)
        if health != 'alive':
            result.append(dict(kind='controller_down', what='Recorded controller %s is %s' % (identity.get('pid'), health),
                               next='service status; deploy or restart with Deploy-WorkflowRelease.ps1'))
    elif not identity:
        result.append(dict(kind='controller_down', what='No controller has claimed this registry', next='Start the controller'))
    if control.get('ram_paused'):
        result.append(dict(kind='ram_paused', what='Launches paused at %s%% RAM' % control.get('ram_percent'),
                           next='Free memory; launches resume below ram_low'))
    capacity = state.get('build_capacity', {})
    if capacity.get('paused'):
        result.append(dict(kind='build_paused', what='New build admission paused (%s%% RAM)' % capacity.get('ram_percent'),
                           next='Free memory; builds resume below build_capacity.ram_low'))
    if cfg is not None and not (cfg.get('integration_lines') or {}).get('root'):
        hooks = sum(bool(l.get('shared_hooks')) for l in state['lanes'].values() if l.get('state') != 'done')
        result.append(dict(kind='integration_lines_undeclared', lanes_with_shared_hooks=hooks,
            what='Controller config declares no integration_lines.root: review packets cannot be re-pinned, requested or '
                 'decided, and landings are checked against any branch', next='Declare integration_lines {root, native} '
                 'as a deploy step (docs/PIKMIN2_WORKFLOW_OPERATOR.md)'))
    return result


def stuck(state, now, *, cfg=None, base=None, probe=None, limit=None, view=None):
    """Needs-you first, then blocked lanes grouped by structured blocker, parked lanes, and circular waits."""
    from . import blockers
    from .no_progress import parked
    from .producer_contract import acceptance_lint
    decisions = tuple((cfg or {}).get('consumer_wakeup', {}).get('umbrella_issues') or blockers.DECISIONS)
    found, table = blockers.index(state, decisions)
    grouped = blockers.groups(state, decisions, limit=limit)
    waiting = sorted(k for k, l in state['lanes'].items() if l.get('state') in blockers.WAITING)
    rest = [dict(p, refs=[blockers.label(r) for r in found.get(p['lane'], [])]) for p in parked(state, now)]
    lint = [dict(lane=k, findings=f) for k in waiting for f in [acceptance_lint(state['lanes'][k].get('acceptance'))] if f]
    result = dict(at=now, needs_you=needs_you(state, now, cfg=cfg, base=base, probe=probe, found=found, table=table),
                  machine=machine(state, now, cfg=cfg, probe=probe), blocked=len(waiting), groups=grouped['groups'],
                  total_groups=grouped['total_groups'], cycles=grouped['cycles'], unstructured=grouped['unstructured'],
                  parked=rest, catch22=lint)
    if view is not None:
        from .autofill import _workers
        result['available_workers'] = len(_workers(view, state))
    return result


def bounded(report, items=20, groups=12, lanes=10):
    """A stuck report cut to a fixed size for the dashboard; counts say what was left out."""
    cut = [dict(g, lanes=g['lanes'][:lanes]) for g in report['groups'][:groups]]
    return dict(report, needs_you=[{k: v for k, v in r.items() if k != 'downstream_lanes'} for r in report['needs_you'][:items]],
                groups=cut, parked=report['parked'][:items], catch22=report['catch22'][:items],
                omitted=dict(needs_you=max(0, len(report['needs_you']) - items), groups=max(0, report['total_groups'] - len(cut)),
                             parked=max(0, len(report['parked']) - items), catch22=max(0, len(report['catch22']) - items)))


def lane(state, key, view, cfg, now=None):
    """One lane: state, refs and their owners, parking, recent launches, open notices and the wake gate."""
    from . import blockers
    from .consumer_wakeup import explain
    from .producer_contract import acceptance_lint
    from .worker_capacity import occupant
    now = view.clock() if now is None else now
    require(key in state['lanes'], 'Unknown lane: ' + key)
    row = state['lanes'][key]
    table = blockers.owners(state)
    decisions = tuple(cfg.get('consumer_wakeup', {}).get('umbrella_issues') or blockers.DECISIONS)
    refs = []
    for ref in blockers.refs(state, key, table, decisions):
        owner, how = blockers.owner(state, ref, table, decisions)
        refs.append(dict(ref=blockers.label(ref), owner=owner, owner_state=how))
    configured = dict(cfg.get('lanes') or {}, **state.get('throughput_runtime', {}).get('launch_specs', {}))
    def available(name):
        entry = configured[name]
        if entry.get('autofill_proof'):
            from .autofill import launch_files_unchanged
            if not launch_files_unchanged(view, entry): return False
        return all(view.probe(o) == 'dead' for o in entry.get('legacy_supervisors', []))
    launches = sorted((x for x in state.get('control', {}).get('launches', {}).values() if x['lane'] == key), key=lambda x: x['created_at'])
    notices = [dict(kind=n['kind'], status=n['status'], age_seconds=age(now, n.get('at')), repeats=n.get('repeats'),
                    detail=n.get('detail')) for n in state.get('control', {}).get('notices', {}).values()
               if n.get('lane') == key and n.get('status') == 'pending']
    result = dict(lane=key, state=row.get('state'), generation=row.get('generation'), issue=row.get('issue'),
        worker=row.get('worker_id'), process=view.probe(row['process']) if row.get('process') else None,
        occupant=occupant(view, state, row) if row.get('worker_id') else None,
        progress_age_seconds=age(now, row.get('progress_at')), progress=row.get('progress_detail'),
        next_action=row.get('next_action'), dependencies=row.get('dependencies', []), refs=refs,
        parked=row.get('parked'), wake_after=row.get('wake_after'), stall_streak=row.get('stall_streak'),
        capacity_parked=row.get('capacity_parked'), acceptance_lint=acceptance_lint(row.get('acceptance')),
        launches=[compact(x, now) for x in launches[-5:]], launch_count=len(launches), notices=notices[-10:],
        worktrees=worktrees(view.root, row))
    if row.get('state') == 'blocked':
        result['wake'] = explain(view, state, key, configured, available, cfg)
    return result


def compact(x, now):
    return dict(id=x['id'][:12], status=x.get('status'), reason=str(x.get('reason'))[:80], generation=x.get('generation'),
                age_seconds=age(now, x.get('created_at')), exit_code=(x.get('result') or {}).get('exit_code'),
                tools_started=(x.get('result') or {}).get('tools_started'), model=x.get('model') or (x.get('models') or [None])[0])


def worktrees(root, row):
    """The lane's recorded source heads beside the canonical checkouts' heads."""
    from .provenance import git
    result = {}
    for name, canonical in (('root', Path(root)), ('native', Path(root) / 'native')):
        source = row.get(name) or {}
        if not source: continue
        head = (git(canonical, 'rev-parse', 'HEAD', timeout=5) or '').strip() or None
        result[name] = dict(worktree=source.get('worktree'), head=source.get('head'), canonical_head=head)
    return result


def topology(root, state, cfg):
    """Canonical root, maintained native tree and its nested research repo, integration lines, releases."""
    from .provenance import claimed, git
    root = Path(root)
    def head(path):
        return ((git(path, 'rev-parse', 'HEAD', timeout=5) or '').strip() or None) if path.is_dir() else None
    release = root / 'output/workflow/release'
    code = claimed(state.get('control') or {}) or {}
    return dict(root=dict(path=str(root), head=head(root)), native=dict(path=str(root / 'native'), head=head(root / 'native')),
        research=dict(path=str(root / 'native/pikmin2-research'), head=head(root / 'native/pikmin2-research')),
        integration_lines=cfg.get('integration_lines'), controller=dict(sha=code.get('sha'), path=code.get('path'),
        dirty=code.get('dirty')), releases=sorted(p.name for p in release.iterdir() if p.is_dir()) if release.is_dir() else [],
        lane_worktrees=['output/dsw/<lane>-root|native', 'output/workflow/autofill/planning-shards/<scope>/prepared/<lane>-root|native'])


def settings(cfg, root, state):
    """Config keys an operator reads most, without the per-lane launch table."""
    keep = ('interval', 'ram_low', 'ram_high', 'launches_per_tick', 'models', 'integration_lines', 'consumer_wakeup',
            'build_capacity', 'shepherd', 'queue_pressure', 'terminal_idle_recovery', 'shared_review_routing')
    return dict(topology=topology(root, state, cfg), lanes_configured=len(cfg.get('lanes') or {}),
                launch_specs=len(state.get('throughput_runtime', {}).get('launch_specs', {})),
                settings=state.get('settings'), config={k: cfg[k] for k in keep if k in cfg},
                autofill={k: v for k, v in (cfg.get('throughput', {}).get('autofill') or {}).items() if k != 'lanes'})


def text(verb, data):
    """Terse human rendering; --json gives everything."""
    out = []
    def mins(s): return '?' if s is None else '%dm' % (s // 60) if s < 7200 else '%.1fh' % (s / 3600)
    if verb in ('stuck', 'needs-you'):
        out.append('== Needs you (%d) ==' % len(data['needs_you']))
        for r in data['needs_you']:
            who = r.get('lane') or ', '.join(r.get('lanes') or []) or '-'
            extra = ''.join(s for s in (' asked %dx' % r['asked'] if r.get('asked') else '',
                                         ' %d downstream' % r['downstream'] if r.get('downstream') else '') if s)
            out.append('- [%s] %s (%s old%s): %s' % (r['kind'], who, mins(r.get('age_seconds')), extra, str(r['what'])[:220]))
            out.append('    Next: ' + r['next'])
        if data.get('machine'):
            out.append('== Machine-wide ==')
            out += ['- [%s] %s\n    Next: %s' % (r['kind'], r['what'], r['next']) for r in data['machine']]
        if verb == 'needs-you': return '\n'.join(out)
        out.append('== Blocked lanes by structured blocker (%d lanes, %d groups%s) ==' % (
            data['blocked'], data['total_groups'], '' if 'available_workers' not in data else
            '; %d workers available' % data['available_workers']))
        for g in data['groups']:
            owner = ' owner %s (%s)' % (g['owner'], g['owner_state']) if g['owner'] else ' (%s)' % g['owner_state']
            out.append('%s: %d lane%s;%s' % (g['label'], g['count'], '' if g['count'] == 1 else 's', owner))
            out.append('    Next [%s]: %s' % (g['accountable'], g['next_action']))
            out.append('    ' + ', '.join(g['lanes'][:12]) + (' ...' if len(g['lanes']) > 12 else ''))
        if data['cycles']: out.append('Circular waits: ' + '; '.join(' -> '.join(c) for c in data['cycles']))
        if data['unstructured']: out.append('No structured reference (prose only): ' + ', '.join(data['unstructured']))
        out.append('== Parked, no progress (%d) ==' % len(data['parked']))
        for p in data['parked']:
            out.append('- %s: streak %s, wakes %s; waits for %s; blockers %s' % (p['lane'], p['stall_streak'],
                'now (due)' if p['due'] else time.strftime('%m-%d %H:%MZ', time.gmtime(p['wake_after'])) if p['wake_after'] else '?',
                p['waiting_for'], ', '.join(p['refs']) or '-'))
        if data['catch22']:
            out.append('== Acceptance criteria only another owner can satisfy ==')
            for r in data['catch22']:
                for f in r['findings']:
                    out.append('- %s #%d (%s -> %s): %s' % (r['lane'], f['index'], f['match'], f['move_to'], f['criterion'][:150]))
        return '\n'.join(out)
    if verb == 'lane':
        d = data
        out.append('%s: %s gen %s, issue #%s, worker %s (process %s)%s' % (d['lane'], d['state'], d['generation'], d['issue'],
                   d['worker'], d['process'], '; worker busy on ' + d['occupant'] if d['occupant'] else ''))
        out.append('Progress %s ago: %s' % (mins(d['progress_age_seconds']), str(d['progress'])[:300]))
        out.append('Next action: %s' % str(d['next_action'])[:300])
        out += ['Blocker %s -> %s (%s)' % (r['ref'], r['owner'] or '-', r['owner_state']) for r in d['refs']]
        if d['parked']: out.append('Parked: %s; wake_after %s' % (d['parked'].get('waiting_for'), d['wake_after']))
        if 'wake' in d: out.append('Prerequisite wake: %s - %s' % (d['wake']['gate'], d['wake']['detail']))
        for name, why in (d.get('wake') or {}).get('skipped', {}).items(): out.append('    %s: %s' % (name, why))
        out += ['Criterion %d needs another owner (%s): %s' % (f['index'], f['move_to'], f['match']) for f in d['acceptance_lint']]
        out.append('Launches (%d, last %d):' % (d['launch_count'], len(d['launches'])))
        out += ['  %s %s %s ago gen %s exit %s tools %s: %s' % (x['id'], x['status'], mins(x['age_seconds']), x['generation'],
                x['exit_code'], x['tools_started'], x['reason']) for x in d['launches']]
        out += ['Notice %s (%s ago, %s repeats)' % (n['kind'], mins(n['age_seconds']), n['repeats'] or 0) for n in d['notices']]
        for name, w in d['worktrees'].items():
            out.append('%s worktree %s at %s (canonical %s)' % (name, w['worktree'], (w['head'] or '?')[:12], (w['canonical_head'] or '?')[:12]))
        return '\n'.join(out)
    return json.dumps(data, indent=2, default=sorted)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('verb', nargs='?', default='stuck', choices=('stuck', 'needs-you', 'lane', 'launches', 'assignment', 'config'))
    parser.add_argument('key', nargs='?', help='lane key for lane, launches and assignment')
    parser.add_argument('--root', type=Path, default=None, help='canonical workspace (default: current directory)')
    parser.add_argument('--db', type=Path, help='read this registry file (e.g. a backup copy) instead; no workspace check')
    parser.add_argument('--config', type=Path, help='controller config (default <root>/%s)' % CONFIG)
    parser.add_argument('--limit', type=int, default=20, help='launches shown by launches; groups shown by stuck')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    root = (args.root or Path.cwd()).resolve()
    try:
        require(args.verb not in ('lane', 'launches', 'assignment') or args.key, args.verb + ' needs a lane key')
        cfg = config(root, args.config)
        sections = {'stuck': STUCK, 'needs-you': STUCK, 'lane': LANE, 'launches': [('lanes',), ('control', 'launches')],
                    'assignment': [('lanes',)], 'config': [('throughput_runtime', 'launch_specs')]}[args.verb]
        state = read(args.db or root / REGISTRY, sections, None if args.db else root)
        view = View(Path(state['root']) if args.db else root)
        now = view.clock()
        base = local_path(view.root, cfg.get('output', 'output/workflow/controller'))
        if args.verb in ('stuck', 'needs-you'):
            data = stuck(state, now, cfg=cfg, base=base, probe=view.probe, limit=args.limit,
                         view=view if args.verb == 'stuck' else None)  # Worker availability probes processes.
        elif args.verb == 'lane':
            data = lane(state, args.key, view, cfg, now)
        elif args.verb == 'launches':
            require(args.key in state['lanes'], 'Unknown lane: ' + args.key)
            rows = sorted((x for x in state.get('control', {}).get('launches', {}).values() if x['lane'] == args.key), key=lambda x: x['created_at'])
            data = dict(lane=args.key, total=len(rows), launches=[compact(x, now) for x in rows[-args.limit:]])
        elif args.verb == 'assignment':
            from .support_actions import assignment
            row = assignment(state, args.key)
            data = dict(lane=args.key, open=bool(row), assignment={k: v for k, v in row.items() if k != 'spec'},
                        spec_lane=(row.get('spec') or {}).get('lane'))
        else:
            data = settings(cfg, view.root, state)
    except (Rejected, OSError, ValueError, sqlite3.Error) as exc:
        print(json.dumps(dict(error=str(exc) or type(exc).__name__)), file=sys.stderr)
        return 2
    if args.json or args.verb in ('launches', 'assignment', 'config'):
        print(json.dumps(data, indent=2, default=sorted))
    else:
        print(text(args.verb, data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
