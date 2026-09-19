"""Read-only answers about the live workflow: what is stuck, why, and what only you can do.

  <python> <checkout>/scripts/workflow_module.py inspect [--root R | --db COPY] <verb> [--json]
  verbs: stuck (default) | needs-you | lane <key> | launches <key> | assignment <lane> | config
         delivery | delivery-suggest | promotion-plan root|native [--line REF --target REF --out output/<stem> [--force]]

The registry is opened with SQLite URI mode=ro plus PRAGMA query_only, decoding only the sections a
verb needs; this module never imports workflow.registry or the writer gate and never calls a write
path (it shares pure helpers with modules that also hold writers; View refuses every write), so it
works on a live WAL registry, a backup copy, and while the writer lock is contended. --db reads any
registry file (a copy) without the workspace check, with the config of the registry's own root.
The delivery verbs (workflow.shipping) also read the root and native git repositories through bounded,
non-fetching git calls; promotion-plan --out writes only the two named plan files below output/ (never
output/workflow/, never over an existing file without --force)."""
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
TOOLCHAIN = re.compile(r'\b(toolchain|compiler|g\+\+(?!\w)|gcc|cc1(plus)?|mingw\w*|msys\w*|cmake|ninja|linker)(?!\w)', re.I)
MACHINE_SECONDS = 72 * 3600  # A toolchain asset ask whose lane moved on stays listed this long after it was raised.
NOTICES = ('unsupervised_lane', 'shared_review_target_dead')
STUCK = [('lanes',), ('leases',), ('queue',), ('control', 'launches'), ('control', 'notices'), ('control', 'shepherd'), ('support_actions',),
         ('delivery_contracts',), ('throughput', 'workstreams'), ('throughput', 'workers'), ('throughput', 'assignments'),
         ('throughput_runtime', 'launch_specs')]
LANE = STUCK + [('consumer_verifications',)]


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
    """The controller config, read-only; None when absent (callers say so rather than read it as empty)."""
    path = Path(path) if path else Path(root) / CONFIG
    if not path.is_file(): return None
    return json.loads(path.read_text(encoding='utf-8-sig'))


def umbrella(cfg):
    """Decision issues no producer owns: consumer_wakeup.umbrella_issues when set (even []), else the default."""
    from .blockers import DECISIONS
    settings = (cfg or {}).get('consumer_wakeup', {})
    return tuple(settings['umbrella_issues']) if 'umbrella_issues' in settings else DECISIONS


def configured(cfg, state):
    """Lanes the controller can launch: config lanes plus autofill launch specs (as lane() and the wake gate see them)."""
    return dict((cfg or {}).get('lanes') or {}, **state.get('throughput_runtime', {}).get('launch_specs', {}))


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
    """Open user_decision/user_asset asks, one per lane and kind, plus machine-wide (toolchain) asset asks.

    An ask is open while its lane still waits at the generation it was asked about (blockers.asked);
    a relaunched lane's older asks are superseded. Rewordings of one lane's ask merge into one row
    that keeps its distinct wordings. A toolchain user_asset ask is machine-wide: listed while its
    lane waits on it, and for MACHINE_SECONDS after it was raised once that lane moved on."""
    from .blockers import asked
    rows, machine = {}, {}
    def note(row, at, required, identity):
        if type(at) in (int, float):
            row['first_at'] = at if row.get('first_at') is None else min(row['first_at'], at)
        row['asked'] += 1
        wording = ' '.join(required.casefold().split())
        if (at or 0) >= row['wordings'].get(wording, (-1,))[0]: row['wordings'][wording] = (at or 0, required)
        if (at or 0) >= (row.get('last_at') or 0): row.update(last_at=at, required=required, action=identity)
    for identity, action in state.get('support_actions', {}).items():
        details = action.get('details') or {}
        if action.get('action') != 'external' or details.get('owner') != 'user': continue
        key, required = action.get('key'), str(details.get('required') or action.get('reason') or '')
        current = asked(action, state['lanes'].get(key))
        if details.get('kind') == 'user_asset' and TOOLCHAIN.search(required):
            recent = age(now, action.get('at')) is not None and age(now, action['at']) <= MACHINE_SECONDS
            if current or recent:
                row = machine.setdefault('toolchain', dict(lanes=set(), waiting=set(), asked=0, wordings={}))
                note(row, action.get('at'), required, identity)
                row['lanes'].add(key)
                if current: row['waiting'].add(key)
            continue
        if not current: continue
        row = rows.setdefault((key, details.get('kind')), dict(kind=details.get('kind'), lane=key, asked=0, wordings={}))
        note(row, action.get('at'), required, identity)
    def wordings(row):  # Distinct wordings, newest first, bounded.
        return [w for _, w in sorted(row['wordings'].values(), key=lambda p: -p[0])][:3]
    result = []
    for row in rows.values():
        waiting = downstream(found, state, row['lane'])
        result.append(dict(kind=row['kind'], lane=row['lane'], what=row['required'], asked=row['asked'],
            distinct_wordings=len(row['wordings']), wordings=wordings(row), age_seconds=age(now, row.get('first_at')),
            last_asked_seconds=age(now, row['last_at']), downstream=len(waiting), downstream_lanes=waiting[:10],
            next=('Decide, then give the answer to the lane as hashed evidence it can cite (a reviewer lane records '
                  'approvals; there is no operator write command); retire the lane if the answer is no'
                  if row['kind'] == 'user_decision' else
                  'Supply the asset at a stable path, then record its path and sha256 where the lane can cite it')))
    for row in machine.values():
        result.append(dict(kind='toolchain', lane=None, lanes=sorted(row['lanes']), waiting_lanes=sorted(row['waiting']),
            what=row['required'], asked=row['asked'], distinct_wordings=len(row['wordings']), wordings=wordings(row),
            age_seconds=age(now, row.get('first_at')), last_asked_seconds=age(now, row['last_at']), machine=True,
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
    launchable = configured(cfg, state) if cfg is not None else None  # Unknown without a config: keep the notice.
    def settled(notice):
        """The condition the notice reported is gone: the lane is done, launch-configured, or (owner) alive."""
        subject = state['lanes'].get(notice.get('lane')) or {}
        if subject.get('state') == 'done': return True
        if launchable is not None and notice.get('lane') in launchable: return True
        return (notice['kind'] == 'shared_review_target_dead' and probe is not None and bool(subject.get('process'))
                and probe(subject['process']) == 'alive')
    seen = {}
    for notice in notices.values():
        if notice.get('status') != 'pending' or notice.get('kind') not in NOTICES or settled(notice): continue
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
        try: attention, written = json.loads(path.read_text(encoding='utf-8-sig')), path.stat().st_mtime
        except (OSError, ValueError): attention, written = dict(reason='shepherd-attention.json unreadable'), None
        attention = dict(attention if isinstance(attention, dict) else {}, written_at=written)
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
    # review_packet.request refuses before recording anything while integration_lines.root is undeclared, so
    # that case is machine()'s integration_lines_undeclared item; a refused row appears only when the line was
    # removed between request and decision.
    for identity, row in state.get('packet_requests', {}).items():
        if row.get('status') == 'refused' and 'integration_lines' in str(row.get('error')):
            items.append(dict(kind='packet_refused', lane=(row.get('requested_by') or {}).get('lane'), request=identity,
                what=row.get('error'), age_seconds=age(now, row.get('decided_at')), packet=row.get('packet'),
                next='Declare integration_lines.root in the controller config, land the packet there, then re-request'))
    return sorted(items, key=lambda r: (r['kind'] in ('shepherd_escalation',), -(r.get('downstream') or 0), -(r['age_seconds'] or 0)))


def machine(state, now, *, cfg=None, probe=None, config_path=None, root=None):
    """Machine-wide blockers: controller down, RAM or build pause, undeclared integration lines; cfg None
    (no config read) is itself an item, and nothing config-derived is claimed. With root, release_target
    is read as workflow.shipping reads it (the canonical config, on every call), not from cfg."""
    result = []
    if cfg is None:
        result.append(dict(kind='config_unread', what='Controller config not found%s: integration lines, launch configs '
            'and umbrella issues are unknown to this view' % (' at %s' % config_path if config_path else ''),
            next='Pass --root <canonical root> or --config <path>'))
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
    declared = cfg.get('integration_lines') if cfg is not None else None  # A malformed value is not a crash.
    if cfg is not None and not (isinstance(declared, dict) and isinstance(declared.get('root'), dict)):
        hooks = sum(bool(l.get('shared_hooks')) for l in state['lanes'].values() if l.get('state') != 'done')
        result.append(dict(kind='integration_lines_undeclared', lanes_with_shared_hooks=hooks,
            what='Controller config declares no integration_lines.root: review packets cannot be re-pinned, requested or '
                 'decided, and landings are checked against any branch', next='Declare integration_lines {root, native} '
                 'as a deploy step (docs/PIKMIN2_WORKFLOW_OPERATOR.md)'))
    declared, malformed = cfg.get('release_target') if cfg is not None else None, None
    if cfg is not None and root is not None:
        from .shipping import targets
        try:
            declared = targets(root)
        except Rejected as exc:
            malformed = str(exc)
    elif declared is not None and not isinstance(declared, dict):
        malformed = 'release_target must map root/native to {repo, ref[, remote]}'
    if malformed:
        result.append(dict(kind='release_target_malformed', what=malformed, next='Fix release_target in '
                           'output/workflow/controller/config.json (docs/PIKMIN2_WORKFLOW_OPERATOR.md)'))
    elif cfg is not None and not isinstance((declared or {}).get('root'), dict):
        result.append(dict(kind='release_target_undeclared', what='Controller config declares no release_target.root: '
            'shipped work cannot be told from integrated work and no promotion can be planned from config',
            next='Run inspect delivery-suggest, choose the lines and target, and declare release_target beside '
                 'integration_lines (docs/PIKMIN2_WORKFLOW_OPERATOR.md)'))
    return result


def stuck(state, now, *, cfg=None, base=None, probe=None, limit=None, view=None, config_path=None, root=None):
    """Needs-you first, then blocked lanes grouped by structured blocker, parked lanes, and circular waits.

    cfg None means no controller config was read (a machine item says so)."""
    from . import blockers
    from .no_progress import parked
    from .producer_contract import acceptance_lint
    decisions = umbrella(cfg)
    found, table = blockers.index(state, decisions)
    grouped = blockers.groups(state, decisions, limit=limit)
    waiting = sorted(k for k, l in state['lanes'].items() if l.get('state') in blockers.WAITING)
    rest = [dict(p, refs=[blockers.label(r) for r in found.get(p['lane'], [])]) for p in parked(state, now)]
    lint = [dict(lane=k, findings=f) for k in waiting for f in [acceptance_lint(state['lanes'][k].get('acceptance'))] if f]
    result = dict(at=now, needs_you=needs_you(state, now, cfg=cfg, base=base, probe=probe, found=found, table=table),
                  machine=machine(state, now, cfg=cfg, probe=probe, config_path=config_path, root=root), blocked=len(waiting), groups=grouped['groups'],
                  total_groups=grouped['total_groups'], cycles=grouped['cycles'], unstructured=grouped['unstructured'],
                  parked=rest, catch22=lint)
    if view is not None:
        from .autofill import _workers
        result['available_workers'] = len(_workers(view, state))
    return result


def bounded(report, items=20, groups=12, lanes=10, chars=400):
    """A stuck report cut to a fixed size for the dashboard: every list and text is capped; counts say what was left out."""
    def small(row):
        return {k: (v[:lanes] if isinstance(v, list) else v[:chars] if isinstance(v, str) else v)
                for k, v in row.items() if k != 'downstream_lanes'}
    def cut(name):
        return [small(r) for r in report.get(name, [])[:items]], max(0, len(report.get(name, [])) - items)
    result, omitted = dict(report), {}
    for name in ('needs_you', 'machine', 'parked', 'catch22'):
        result[name], omitted[name] = cut(name)
    result['groups'] = [small(g) for g in report['groups'][:groups]]
    omitted['groups'] = max(0, report['total_groups'] - len(result['groups']))
    for name in ('unstructured', 'cycles'):
        result[name] = [c[:lanes] if isinstance(c, list) else c for c in report.get(name, [])[:items]]
        omitted[name] = max(0, len(report.get(name, [])) - items)
    return dict(result, omitted=omitted)


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
    decisions = umbrella(cfg)
    refs = []
    for ref in blockers.refs(state, key, table, decisions):
        owner, how = blockers.owner(state, ref, table, decisions)
        refs.append(dict(ref=blockers.label(ref), owner=owner, owner_state=how))
    launchable = configured(cfg, state)
    def available(name):
        entry = launchable[name]
        if entry.get('autofill_proof'):
            from .autofill import launch_files_unchanged
            if not launch_files_unchanged(view, entry): return False
        return all(view.probe(o) == 'dead' for o in entry.get('legacy_supervisors', []))
    launches, archived = history(view.root, state, key)
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
        launches=[compact(x, now) for x in launches[-5:]], launch_count=len(launches), archived_launches=archived,
        notices=notices[-10:], worktrees=worktrees(view.root, row))
    if row.get('state') == 'blocked':
        result['wake'] = (explain(view, state, key, launchable, available, cfg) if cfg is not None else
                          dict(gate='config_unread', detail='No controller config read; pass --root or --config'))
    return result


def history(root, state, key):
    """(the lane's launches, hot and archived, oldest first; how many came from the registry archive)."""
    from . import registry_archive  # Opens the archive mode=ro; empty without one.
    hot = {i: x for i, x in state.get('control', {}).get('launches', {}).items() if x['lane'] == key}
    old = {i: x for i, x in registry_archive.history(root, lane=key, state=state)['launches'].items()
           if i not in hot and x.get('lane') == key}
    return sorted([*hot.values(), *old.values()], key=lambda x: x.get('created_at') or 0), len(old)


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
        integration_lines=cfg.get('integration_lines'), release_target=cfg.get('release_target'), controller=dict(sha=code.get('sha'), path=code.get('path'),
        dirty=code.get('dirty')), releases=sorted(p.name for p in release.iterdir() if p.is_dir()) if release.is_dir() else [],
        lane_worktrees=['output/dsw/<lane>-root|native', 'output/workflow/autofill/planning-shards/<scope>/prepared/<lane>-root|native'])


def settings(cfg, root, state):
    """Config keys an operator reads most, without the per-lane launch table; config_read false when none was found."""
    keep = ('interval', 'ram_low', 'ram_high', 'launches_per_tick', 'models', 'integration_lines', 'release_target', 'consumer_wakeup',
            'build_capacity', 'shepherd', 'queue_pressure', 'terminal_idle_recovery', 'shared_review_routing')
    read, cfg = cfg is not None, cfg or {}
    return dict(config_read=read, topology=topology(root, state, cfg), lanes_configured=len(cfg.get('lanes') or {}),
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
            out += ['    Also worded: ' + w[:160] for w in (r.get('wordings') or [])[1:]]
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
        out.append('Launches (%d%s, last %d):' % (d['launch_count'], ', %d archived' % d['archived_launches'] if d.get('archived_launches') else '',
                                                  len(d['launches'])))
        out += ['  %s %s %s ago gen %s exit %s tools %s: %s' % (x['id'], x['status'], mins(x['age_seconds']), x['generation'],
                x['exit_code'], x['tools_started'], x['reason']) for x in d['launches']]
        out += ['Notice %s (%s ago, %s repeats)' % (n['kind'], mins(n['age_seconds']), n['repeats'] or 0) for n in d['notices']]
        for name, w in d['worktrees'].items():
            out.append('%s worktree %s at %s (canonical %s)' % (name, w['worktree'], (w['head'] or '?')[:12], (w['canonical_head'] or '?')[:12]))
        return '\n'.join(out)
    if verb == 'delivery':
        d = data
        out.append('Done lanes: %d (%d with receipts, %d done-no-code, %d done-unreceipted, %d archived)' % (
            d['lanes']['done'], d['lanes']['receipts'], d['lanes']['done-no-code'], d['lanes']['done-unreceipted'],
            d['lanes']['archived']))
        if d['lanes']['done-unreceipted']:
            out.append('  done-unreceipted (code no receipt tracks): ' + ', '.join(d['lanes']['unreceipted_lanes']) +
                       (', ...' if d['lanes']['done-unreceipted'] > len(d['lanes']['unreceipted_lanes']) else ''))
        for name, r in d['repos'].items():
            if not r['counts'] and not r.get('error'): continue
            out.append('== %s ==' % name)
            if r.get('error'): out.append('  unverifiable: ' + r['error'])
            out.append('  ' + ', '.join('%s %d' % (k, r['counts'][k]) for k in sorted(r['counts'])))
            def at(x): return x if isinstance(x, str) or x is None else '%s at %s' % (x['ref'], x['tip'][:12])
            out.append('  line %s; target %s' % (at(r['line']), at(r['target'])))
            remote = r.get('remote') or {}
            if remote: out.append('  push remote %s %s%s' % (remote['name'], remote.get('url'), '' if remote.get('off_disk') else
                                  ' (not off-disk: never counts as pushed)'))
            u = r['unpushed']
            out.append('  unpushed receipts %d%s%s' % (u['count'], ', oldest %s (%s old)' % (u['oldest']['lane'],
                       mins(u['oldest']['age_seconds'])) if u['oldest'] else '', ': ' + ', '.join(u['lanes']) if u['lanes'] else ''))
            o = r['oldest_unshipped']
            out.append('  oldest unshipped: ' + (str(o) if isinstance(o, str) or o is None else '%s (%s, %s old)' % (
                o['lane'], o['cls'], mins(o['age_seconds']))))
            if r.get('divergence'):
                v = r['divergence']
                out.append('  line vs target: %d ahead, %d behind, conflicts %s' % (v['ahead'], v['behind'],
                           v['conflicts'] if v.get('conflicts') is not None else 'skipped (%s)' % v.get('conflicts_skipped')))
            if r.get('truncated'): out.append('  truncated: %d receipt commits not evaluated (cap)' % r['truncated'])
        return '\n'.join(out)
    if verb == 'delivery-suggest':
        for name, r in data['repos'].items():
            out.append('== %s: %d receipt commits ==' % (name, r['receipts']))
            if r.get('error'):
                out.append('  error: ' + r['error'])
                continue
            out.append('  missing %d, on no ref %s, not on the off-disk %s remote %s' % (r.get('missing', 0), r.get('on_no_ref', '?'),
                       (r.get('remote') or {}).get('name'), r.get('unpushed', '?')))
            if any((r.get('truncated') or {}).values()): out.append('  truncated: ' + ', '.join(k for k, v in r['truncated'].items() if v))
            out += ['  branch %s: %d%s' % (b['ref'], b['receipts'], ' (worktree %s)' % b['worktree'] if b['worktree'] else '')
                    for b in r.get('branches', [])]
            out += ['  remote %s: %d' % (b['ref'], b['receipts']) for b in r.get('remote_refs', [])]
            t = r.get('default_target')
            out.append('  default target: ' + ('%s (%d receipts)' % (t['ref'], t['receipts']) if t else 'none known'))
            for c in r.get('candidates', []):
                v = c.get('vs_target') or {}
                out.append('  candidate %s: %d receipts%s; vs target %s ahead, %s behind, conflicts %s' % (c['ref'], c['receipts'],
                           ' (%d not on the first)' % c['beyond_top'] if 'beyond_top' in c else '',
                           v.get('ahead', '?'), v.get('behind', '?'), v.get('conflicts', 'skipped')))
            if r.get('candidates'): out.append('  candidates together hold %d of %d' % (r['candidates_hold'], r['receipts'] - r.get('missing', 0)))
            if r.get('between'):
                b = r['between']
                out.append('  %s vs %s: %d ahead, %d behind, conflicts %s' % (b['ours'], b['theirs'], b['ahead'], b['behind'],
                           b.get('conflicts', 'skipped')))
        out.append('Suggested config for the top candidates (paste into output/workflow/controller/config.json yourself; '
                   'nothing was written):')
        out += ['WARNING: ' + w for w in data.get('snippet_warnings', ())]
        out.append(json.dumps(data['snippet'], indent=2))
        return '\n'.join(out)
    return json.dumps(data, indent=2, default=sorted)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('verb', nargs='?', default='stuck', choices=('stuck', 'needs-you', 'lane', 'launches', 'assignment', 'config',
                                                                      'delivery', 'delivery-suggest', 'promotion-plan'))
    parser.add_argument('key', nargs='?', help='lane key for lane, launches and assignment; root or native for promotion-plan')
    parser.add_argument('--root', type=Path, default=None, help='canonical workspace (default: current directory)')
    parser.add_argument('--db', type=Path, help='read this registry file (e.g. a backup copy) instead; no workspace check')
    parser.add_argument('--config', type=Path, help='controller config (default <root>/%s)' % CONFIG)
    parser.add_argument('--limit', type=int, default=20, help='launches shown by launches; groups shown by stuck')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--line', help='promotion-plan: the integration line ref (default: config integration_lines)')
    parser.add_argument('--target', help='promotion-plan: the release target ref (default: config release_target)')
    parser.add_argument('--out', type=Path, help='promotion-plan: also write <out>.json and <out>.md (under output/)')
    parser.add_argument('--force', action='store_true', help='promotion-plan: replace existing --out files')
    parser.add_argument('--no-conflicts', action='store_true', help='delivery verbs: skip merge-tree conflict counts')
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):  # Registry prose is not cp1252-safe; a piped Windows stdout would raise.
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    try:
        require(args.verb not in ('lane', 'launches', 'assignment') or args.key, args.verb + ' needs a lane key')
        require(args.verb != 'promotion-plan' or args.key in ('root', 'native'), 'promotion-plan needs root or native')
        root = (args.root or Path.cwd()).resolve()
        sections = {'stuck': STUCK, 'needs-you': STUCK, 'lane': LANE, 'launches': [('lanes',), ('control', 'launches')],
                    'assignment': [('lanes',)], 'config': [('throughput_runtime', 'launch_specs')], 'delivery': [('lanes',)],
                    'delivery-suggest': [('lanes',)], 'promotion-plan': [('lanes',)]}[args.verb]
        state = read(args.db or root / REGISTRY, sections, None if args.db else root)
        if args.db and not args.root: root = Path(state['root'])  # A copy's own workspace, not the caller's directory.
        view = View(Path(state['root']) if args.db else root)
        path = args.config or root / CONFIG
        cfg = config(root, path)
        now = view.clock()
        base = local_path(view.root, (cfg or {}).get('output', 'output/workflow/controller'))
        if args.verb in ('stuck', 'needs-you'):
            data = stuck(state, now, cfg=cfg, base=base, probe=view.probe, limit=args.limit, config_path=path, root=view.root,
                         view=view if args.verb == 'stuck' else None)  # Worker availability probes processes.
        elif args.verb == 'lane':
            data = lane(state, args.key, view, cfg, now)
        elif args.verb == 'launches':
            require(args.key in state['lanes'], 'Unknown lane: ' + args.key)
            rows, archived = history(view.root, state, args.key)
            data = dict(lane=args.key, total=len(rows), archived=archived, launches=[compact(x, now) for x in rows[-args.limit:]])
        elif args.verb == 'assignment':
            from .support_actions import assignment
            require(args.key in state['lanes'], 'Unknown lane: ' + args.key)
            row = assignment(state, args.key)
            data = dict(lane=args.key, open=bool(row), assignment={k: v for k, v in row.items() if k != 'spec'},
                        spec_lane=(row.get('spec') or {}).get('lane'))
        elif args.verb == 'delivery':
            from .shipping import gather, reconcile
            data = reconcile(view.root, state, now, known=gather(view.root, state, not args.no_conflicts))
        elif args.verb == 'delivery-suggest':
            from .shipping import suggest
            data = suggest(view.root, state, conflicts=not args.no_conflicts)
        elif args.verb == 'promotion-plan':
            from .shipping import markdown, plan, write_plan
            data = plan(view.root, state, args.key, line=args.line, target=args.target)
            if args.out: data['written'] = write_plan(view.root, data, args.out, args.force)
            if not args.json:
                print(markdown(data))
                return 0
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
