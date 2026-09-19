"""Authenticated shared-file approvals: one registry ledger; producer-written statuses never count.

state['approvals'] maps id -> immutable row. Writers: review_decisions.record and
Registry.dispose_review (kind handoff_review), shared_decisions.record (preflight),
landing_review (landing_review) and shared_hook_decision (shared_hook). Every writer
authenticates the reviewer: a registered lane in state running and alive, with a running
controller launch bound to that generation, whose runner process is an ancestor of the
calling process, and which owns the producer's workstream or holds its exact delegated
assignment. Rows stamp that launch, its models and the code revision.

Handoff and preflight rows pin one file at the producer's root/native base/head plus the
sha256 of that file's base..head diff; a row counts only while the lane holds exactly those
pins. Landing reviews pin reviewed head, landed commit and a git-verified interdiff.
The latest row per subject decides; a repeated decision after a different one is a new row.
packet_decision is the one writer that is not a reviewer lane: the running controller process
re-runs a requested review packet (workflow.review_packet) at its audited pins and records
shared_hook rows with decided_by 'packet:<schema>@<blob>'; agents can only request that.

  <python> <checkout>/scripts/workflow_module.py approvals landing-review --root <root> --request <json>
  <python> <checkout>/scripts/workflow_module.py approvals shared-hook --root <root> --request <json>

landing_audit --approvals lists older approvals without ledger backing, read-only.
"""
import copy
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys

from .control import fingerprint
from .handoff import Rejected, local_path, nonempty, require
from .no_progress import Parked
from .processes import identify
from .provenance import cli

REVIEW_KINDS = ('handoff_review', 'preflight')
LANDING_STATES = ('blocked', 'done', 'handoff_ready', 'integrating')
STATUSES = ('approved', 'rejected')
INSTRUCTION = (' Approvals are registry rows, never handoff fields: a shared_reviews status of approved/rejected '
    'is refused at submit unless the approvals ledger already holds that decision at your exact pins, and '
    'integrate reads only the ledger. Reviewers record decisions from inside their own live launch session '
    '(the CLI authenticates the calling process), passing reviewer (your lane) and reviewer_generation; '
    'free-text reviewers are refused. Landing review of a port: ' + cli('approvals') + ' landing-review --root '
    '<root> --request <json> with reviewer, reviewer_generation, key, producer_generation, reviewed_head, '
    'landed_sha, files (paths inside that repository), interdiff_sha256 (sha256 of git --literal-pathspecs '
    'diff <INTERDIFF options> <reviewed_head> <landed_sha> -- <files sorted>; the refusal prints the value), '
    'status approved|rejected, conditions [..], evidence {path,sha256}; the lander can never review its own '
    'port. Decision on a structured shared_hook dependency: ' + cli('approvals') + ' shared-hook --root <root> '
    '--request <json> with reviewer, reviewer_generation, hook {kind:shared_hook, issue, files|item_id}, '
    'lanes [{key, generation}], commit (for files), status, conditions, evidence. A review packet '
    '(tools/review_packets/) never approves by itself: ' + cli('review_packet') + ' request asks the controller '
    'to evaluate it for the lanes holding a hook, and pins change only through ' + cli('review_packet') + ' repin. ')
PRODUCER = ('; for a #186 decision on files you do not own, blocked also takes shared_hooks '
    '[{kind:"shared_hook",issue:<number>,files:[repository-relative paths]} or {kind:"shared_hook",issue,item_id}] '
    'so a reviewer can record an authenticated decision against it (it holds only at your current pins; '
    'a later blocked finish replaces the list)')


def _controller(reg, control, me):
    require((control or {}).get('controller') == me and reg.probe(me) == 'alive',
            'Packet decisions are recorded only by the running controller process; agents request an evaluation '
            'with review_packet request')


def _refuse(reg, me, request_id, error):
    with reg.transaction() as state:
        _controller(reg, reg.control(state), me)
        row = state['packet_requests'][request_id]
        if row['status'] == 'requested':
            row.update(status='refused', error=error, decided_at=reg.clock())
            reg.event(state, 'packet_evaluation_refused', None, request=request_id, error=error)
        return copy.deepcopy(row)


def _standing(rows, lane, hook_id, records):
    """Why a reviewer's rejection at the lane's pins outranks this packet (no reviewer re-pin since), else None."""
    row = _hook(rows, lane['lane'], hook_id)
    if (row and row.get('source') != 'review_packet' and row['status'] == 'rejected' and row['pins'] == pins(lane) and
            not any(r.get('approval') == 'reviewer' and r.get('at', 0) > row['at'] for r in records)):
        return f"reviewer rejection {row['id']} stands at these pins"
    return None


def packet_decision(reg, request_id, directory=None, final=False):
    """Controller only: re-run a requested packet's verify at its audited pins and record the outcome.

    The packet must still be on the reviewed root line and cover the hook: an item_id hook is decided
    on that item only. APPROVED is an approved and CHANGES_REQUIRED a rejected shared_hook row
    (conditions: the missing changes) for each requested lane that still holds the hook at that
    generation, is a declared consumer, approved none of the pins used and has no standing reviewer
    rejection at its pins. A drifted, unpinned or uncovered packet (or any failure when final) marks
    the request refused and records nothing. The evaluation JSON written under
    output/workflow/review-packets/ is the rows' hashed evidence."""
    from .handoff import digest
    from .provenance import stamp
    from .review_packet import DECISIONS, DriftError, audited, evaluate, load, scope
    from .storage import read_record
    me = identify(os.getpid())
    _controller(reg, (read_record(reg, (), '') or {}).get('control'), me)
    request = reg.snapshot(section=('packet_requests',)).get(request_id)
    require(isinstance(request, dict) and request.get('status') == 'requested', 'No open packet request: ' + str(request_id))
    try:
        packet, blob, commit = load(reg.root, request['packet'], request['commit'], line=True)
        if blob != request['blob']:
            raise DriftError('Packet blob differs from the request')
        hook = next((h for t in request['lanes'] for h in (read_record(reg, ('lanes',), t['key']) or {}).get('shared_hooks') or []
                     if h.get('id') == request['hook_id']), None)
        if hook is None:
            raise DriftError('No requested lane still holds hook ' + request['hook_id'])
        ids = scope(reg.root, packet, hook)
        result = evaluate(reg.root, packet, blob, audited(reg.snapshot(section=('packet_pins',)), packet))
    except (Rejected, OSError, ValueError) as exc:
        if not (isinstance(exc, DriftError) or final):
            raise
        return _refuse(reg, me, request_id, str(exc) or type(exc).__name__)
    chosen = [i for i in result['items'] if i['id'] in ids]
    decision = 'APPROVED' if all(i['status'] == 'APPROVED' for i in chosen) else 'CHANGES_REQUIRED'
    result = dict(result, hook=hook, scope=ids, hook_decision=decision)
    folder = Path(directory or reg.root / 'output/workflow') / 'review-packets'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (request_id + '.json')
    path.write_text(json.dumps(result, indent=1, sort_keys=True), encoding='utf-8')
    evidence = dict(path=str(path), sha256=digest(path))
    reg.evidence(evidence)
    status = DECISIONS[decision]
    conditions = [f"{i['id']}: {i['missing_change']}" for i in chosen if i['status'] != 'APPROVED']
    used = {k: v['record'] for k, v in result['pins'].items() if 'record' in v}
    code = stamp()
    with reg.transaction() as state:
        _controller(reg, reg.control(state), me)
        row = state.get('packet_requests', {}).get(request_id)
        require(row and row['status'] == 'requested', 'Packet request already closed: ' + request_id)
        now = audited(state.get('packet_pins', {}), packet)
        require({k: (now.get(k) or {}).get('id') for k in used} == used, 'Audited pins changed during evaluation')
        records = [now[k] for k in used]
        approvers = {(r.get('actor') or {}).get('lane') for r in records if r.get('approval') == 'reviewer'}
        identity = dict(decided_by=result['decided_by'], controller=me, request=request_id, requested_by=row['requested_by'])
        written, skipped = [], []
        for target in row['lanes']:
            lane = state['lanes'].get(target['key'])
            held = next((h for h in (lane or {}).get('shared_hooks') or [] if h.get('id') == row['hook_id']), None)
            reason = ('lane or generation changed' if not lane or lane['generation'] != target['generation'] else
                      'no longer holds the hook' if held is None else
                      'not a declared consumer of the packet' if lane['lane'] not in packet['consumers'] else
                      'approved a pin this decision uses' if lane['lane'] in approvers else
                      _standing(ledger(state), lane, row['hook_id'], records))
            if reason:
                skipped.append(dict(lane=target['key'], reason=reason)); continue
            item = write(reg, state, dict(kind='shared_hook', source='review_packet', lane=lane['lane'],
                                          generation=lane['generation'], hook_id=row['hook_id'], hook=held,
                                          pins=pins(lane), subject=dict(packet=row['packet'], commit=commit, blob=blob,
                                          inputs=result['pins'], scope=ids, decision=decision), status=status,
                                          conditions=conditions, evidence=evidence, reviewer=identity,
                                          decided_by=result['decided_by']), code)
            reg.event(state, 'shared_hook_decided', lane['lane'], approval=item['id'], hook=row['hook_id'], status=status,
                      decided_by=result['decided_by'])
            written.append(item['id'])
        row.update(status='decided' if written else 'stale', decision=decision, decided_by=result['decided_by'],
                   approvals=written, skipped=skipped, evidence=evidence, decided_at=reg.clock())
        return copy.deepcopy(row)


def pins(lane):
    """Exact root/native base and head a decision is bound to."""
    return {k: {'base': (lane.get(k) or {}).get('base'), 'head': (lane.get(k) or {}).get('head')}
            if lane.get(k) else None for k in ('root', 'native')}


def _parents():
    """{pid: parent pid} from one Toolhelp snapshot (Windows) or /proc (POSIX)."""
    if os.name != 'nt':
        result = {}
        for entry in Path('/proc').iterdir():
            if entry.name.isdigit():
                try:
                    result[int(entry.name)] = int((entry / 'stat').read_text().rsplit(')', 1)[1].split()[1])
                except (OSError, ValueError, IndexError):
                    pass
        return result
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_wchar * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if not handle or handle == wintypes.HANDLE(-1).value:
        raise OSError('Process snapshot unavailable')
    try:
        entry, result = Entry(), {}
        entry.dwSize = ctypes.sizeof(Entry)
        ok = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            result[entry.th32ProcessID] = entry.th32ParentProcessID
            ok = kernel.Process32NextW(handle, ctypes.byref(entry))
        return result
    finally:
        kernel.CloseHandle(handle)


def ancestry(limit=32):
    """Identities of this process's live ancestors, nearest first; [] when unreadable.

    A parent created after its child is a recycled PID, so the walk stops there."""
    try:
        parents, child = _parents(), identify(os.getpid())
    except (OSError, ValueError, AttributeError):
        return []
    chain, pid = [], os.getpid()
    for _ in range(limit):
        pid = parents.get(pid)
        if not pid or pid == os.getpid():
            break
        try:
            parent = identify(pid)
            if int(parent['started']) > int(child['started']):
                break
        except (OSError, ValueError):
            break
        chain.append(parent)
        child = parent
    return chain


def launch_of(state, lane):
    """The running controller launch bound to this lane's current generation and process, else None."""
    return next((x for x in state.get('control', {}).get('launches', {}).values()
                 if x.get('lane') == lane['lane'] and x.get('status') == 'running' and
                 x.get('bound_generation') == lane['generation'] and x.get('process') == lane['process']), None)


def nearest(launches, chain):
    """(ancestor process, running launches it runs) for the caller's nearest ancestor that runs any launch.

    A process started under another launch's session belongs to the nearer launch, never to an outer one."""
    for process in chain:
        found = [x for x in launches.values() if x.get('status') == 'running' and x.get('process') == process]
        if found:
            return process, found
    return None, []


def _identity(lane, launch):
    return dict(lane=lane['lane'], generation=lane['generation'], launch=launch['id'],
                models=list(launch.get('models') or []), model=launch.get('model'), session=launch.get('session'))


def authenticate(reg, state, reviewer, generation, chain):
    """Reviewer identity; refuses unless the caller runs inside that lane's live launch session."""
    require(nonempty(reviewer) and type(generation) is int,
            'Reviewer lane and reviewer_generation required; free-text reviewers are refused')
    owner = reg.lane(state, reviewer, generation)
    require(owner['state'] == 'running' and reg.probe(owner['process']) == 'alive', 'Live integration reviewer required')
    launch = launch_of(state, owner)
    require(launch is not None, 'Reviewer has no running controller launch bound to generation ' + str(generation))
    require(owner['process'] in chain, "Caller is not running inside the reviewer lane's live launch session; "
            'record decisions from your own session')
    process, found = nearest(state.get('control', {}).get('launches', {}), chain)
    require(process == owner['process'], 'Caller runs inside a nearer live launch session (' +
            ', '.join(sorted({str(x.get('lane')) for x in found})) + ') than the reviewer lane; record decisions from '
            'your own session')
    return _identity(owner, launch)


def session(reg, chain):
    """Authenticated identity of the nearest live launch the caller runs inside, else None; reads committed records."""
    if not chain:
        return None
    from .storage import read_record
    _, found = nearest(reg.snapshot(section=('control', 'launches')), chain)
    if len(found) != 1:
        return None
    item = found[0]
    lane = read_record(reg, ('lanes',), item.get('lane'))
    if (isinstance(lane, dict) and lane.get('state') == 'running' and lane.get('generation') == item.get('bound_generation')
            and lane.get('process') == item['process'] and reg.probe(lane['process']) == 'alive'):
        return _identity(lane, item)
    return None


def still(state, identity):
    """The authenticated session is still the lane's running launch."""
    lane = state['lanes'].get(identity['lane'], {})
    launch = launch_of(state, lane) if lane.get('generation') == identity['generation'] else None
    return bool(launch and launch['id'] == identity['launch'] and lane.get('state') == 'running')


def descends(state, handoff, target):
    """handoff is the delegated one, or was reached from it only through recorded dispositions."""
    if handoff == target:
        return True
    if not handoff or not target:
        return False
    parents = {(d.get('snapshot') or {}).get('handoff', {}).get('sha256'): (d.get('request') or {}).get('handoff_sha256')
               for d in state.get('throughput', {}).get('dispositions', {}).values()}
    sha, seen = handoff.get('sha256'), set()
    while sha in parents and sha not in seen:
        seen.add(sha); sha = parents[sha]
        if sha == target.get('sha256'):
            return True
    return False


def delegated(state, reviewer, lane):
    """Only the live cycle's exact frozen assignment grants decision authority; the handoff may have
    moved since only through recorded dispositions (sequential per-file decisions)."""
    if reviewer == lane['lane']:return False
    scopes=state.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool',{}).get('scopes',{})
    for row in scopes.values():
        if row.get('review_authority') != 'shared-files-v1' or 'completed_at' in row:continue
        if row.get('spec',{}).get('lane',{}).get('lane') != reviewer:continue
        for target in row.get('support_targets',[]):
            if (target.get('lane')==lane['lane'] and target.get('generation')==lane['generation'] and
                    descends(state,lane.get('handoff'),target.get('handoff')) and target.get('root')==lane.get('root') and
                    target.get('native')==lane.get('native')):return True
    return False


def authorize(state, reviewer, lane):
    require(reviewer != lane['lane'] and (any(
        w.get('owner_lane') == reviewer and lane['lane'] in w.get('lanes', [])
        for w in state.get('throughput', {}).get('workstreams', {}).values()) or delegated(state, reviewer, lane)),
        'Reviewer must own producer workstream or hold exact delegated assignment')


def split(lane, file):
    """(repo, path inside it) of a workspace-relative shared file."""
    if file.startswith('native/') and lane.get('native'):
        return 'native', file[len('native/'):]
    return 'root', file


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def diff(root, lane, file):
    """(repo, path, sha256 of the lane's base..head diff of one file), from git in the maintained repository."""
    from .landing import INTERDIFF, SHA, git, lines, repository
    name, path = split(lane, file)
    source = lane.get(name) or {}
    require(all(SHA.fullmatch(str(source.get(k, ''))) for k in ('base', 'head')), f'Lane {name} source lacks base/head')
    repo = repository(root, name, lines(root))
    return name, path, _sha(git(repo, '--literal-pathspecs', *INTERDIFF, source['base'], source['head'], '--', path)[1])


def ledger(state):
    return state.setdefault('approvals', {})


META = ('id', 'at', 'seq', 'code_revision', 'supersedes')


def _subject(rows, value):
    """Latest rows deciding what this value decides (one per file for landing reviews)."""
    if value['kind'] in REVIEW_KINDS:
        found = [_review(rows, value['lane'], value['file'], value['pins'])]
    elif value['kind'] == 'landing_review':
        found = [_landing(rows, value['lane'], value['repo'], value['reviewed_head'], value['landed_sha'], f)
                 for f in value['files']]
    else:
        found = [_hook(rows, value['lane'], value['hook_id'])]
    return list({r['id']: r for r in found if r}.values())


def write(reg, state, value, code):
    """Insert one immutable row. An identical decision replays only while it is still the latest for its
    subject; after a different decision it is a new row naming the rows it supersedes."""
    rows = ledger(state)
    latest = _subject(rows, value)
    if len(latest) == 1 and {k: v for k, v in latest[0].items() if k not in META} == value:
        return latest[0]
    identity = fingerprint(value)
    if identity in rows:
        value = dict(value, supersedes=sorted(r['id'] for r in latest))
        identity = fingerprint(value)
        require(identity not in rows, 'Approval row already superseded; record fresh evidence')
    rows[identity] = dict(copy.deepcopy(value), id=identity, at=reg.clock(), seq=len(rows) + 1, code_revision=code)
    reg.event(state, 'approval_recorded', value['lane'], approval=identity, approval_kind=value['kind'],
              status=value['status'])
    return rows[identity]


def review_row(reg, state, source, lane, file, digest, status, evidence, reviewer, code, **extra):
    """Ledger row for one handoff or preflight file decision at the lane's current pins."""
    repo, path, sha = digest
    return write(reg, state, dict(kind='preflight' if source == 'shared_decisions' else 'handoff_review', source=source,
                                  lane=lane['lane'], generation=lane['generation'], file=file, repo=repo, path=path,
                                  pins=pins(lane), diff_sha256=sha, status=status, evidence=evidence,
                                  reviewer=reviewer, **extra), code)


def _latest(rows):
    """Recording order: clock, then the ledger sequence (rows written in one tick), then id."""
    return max(rows, key=lambda r: (r.get('at', 0), r.get('seq', 0), r['id']), default=None)


def _review(rows, key, file, current):
    return _latest([r for r in rows.values() if r.get('kind') in REVIEW_KINDS and r.get('lane') == key
                    and r.get('file') == file and r.get('pins') == current])


def _landing(rows, key, repo, head, commit, file):
    return _latest([r for r in rows.values() if r.get('kind') == 'landing_review' and r.get('lane') == key and
                    r.get('repo') == repo and r.get('reviewed_head') == head and r.get('landed_sha') == commit and
                    file in r.get('files', [])])


def _hook(rows, key, hook_id):
    return _latest([r for r in rows.values() if r.get('kind') == 'shared_hook' and r.get('lane') == key
                    and r.get('hook_id') == hook_id])


def decision(rows, lane, file):
    """Latest handoff/preflight decision on this file at the lane's exact pins, else None."""
    return _review(rows, lane['lane'], file, pins(lane))


def statuses(rows, lane, reviews):
    """{file: {status, approval}} from the ledger; a handoff's own status field is ignored."""
    result = {}
    for review in reviews:
        if isinstance(review, dict) and nonempty(review.get('file')):
            row = decision(rows, lane, review['file'])
            result[review['file']] = dict(status=row['status'], approval=row['id'], reviewer=row['reviewer']['lane']) \
                if row else dict(status='requested', approval=None, reviewer=None)
    return result


def apply(rows, lane, data, result, strict=False):
    """Replace pending_reviews with ledger truth; strict refuses unbacked producer-written statuses."""
    reviews = data.get('shared_reviews', []) if isinstance(data, dict) else []
    found = statuses(rows, lane, reviews)
    if strict:
        for review in reviews:
            if review['status'] in STATUSES:
                require(found[review['file']]['status'] == review['status'],
                        f"shared_reviews {review['file']}: status {review['status']} has no matching authenticated "
                        'decision in the approvals ledger at these pins; submit it as requested')
    result = dict(result, pending_reviews=[f for f, v in found.items() if v['status'] != 'approved'])
    if found:
        result['reviews'] = found
    return result


def landing_approval(rows, key, repo, head, commit, file, interdiff):
    """The latest landing review naming this file at these pins, if it is approved at this interdiff."""
    row = _landing(rows, key, repo, head, commit, file)
    return row if row and row['status'] == 'approved' and row['file_interdiffs'].get(file) == interdiff else None


def _conditions(value):
    require(isinstance(value, list) and all(nonempty(c) for c in value), 'conditions must be a list of strings')
    return list(value)


def landing_review(reg, reviewer, reviewer_generation, key, producer_generation, reviewed_head, landed_sha,
                   interdiff_sha256, files, status, evidence, conditions=()):
    """Authenticated decision on landed bytes that differ from the reviewed head (a port)."""
    from .landing import INTERDIFF, HEX64, SHA, changes, git, lines, objects, repository
    from .provenance import stamp
    from .storage import read_record
    require(status in STATUSES, 'Explicit approved/rejected landing review required')
    require(isinstance(files, list) and files and all(nonempty(f) for f in files) and len(set(files)) == len(files),
            'Nonempty distinct landing review files required')
    conditions = _conditions(list(conditions))
    require(all(isinstance(v, str) and SHA.fullmatch(v) for v in (reviewed_head, landed_sha)),
            'Full reviewed_head and landed_sha required')
    require(isinstance(interdiff_sha256, str) and HEX64.fullmatch(interdiff_sha256), 'interdiff_sha256 required')
    reg.evidence(evidence)
    chain = ancestry()
    lane = read_record(reg, ('lanes',), key)
    require(isinstance(lane, dict), 'Unknown lane: ' + str(key))
    require(lane['generation'] == producer_generation, 'Stale ownership generation')
    require(lane['state'] in LANDING_STATES, 'Landing reviews need a blocked, done, handoff_ready or integrating producer')
    names = [n for n in ('root', 'native') if (lane.get(n) or {}).get('head') == reviewed_head]
    require(len(names) == 1, "reviewed_head must be the producer's current root or native head")
    name, source = names[0], lane[names[0]]
    repo = repository(reg.root, name, lines(reg.root))
    found = objects(repo, [c + '^{commit}' for c in (source['base'], reviewed_head, landed_sha)])
    require(all(found.values()), f'Reviewed base/head and landed_sha must exist in {repo}')
    changed = {p for _, p in changes(repo, source['base'], reviewed_head)}
    require(set(files) <= changed, 'Landing review names files the lane did not change: ' +
            ', '.join(sorted(set(files) - changed)))
    per = {f: _sha(git(repo, '--literal-pathspecs', *INTERDIFF, reviewed_head, landed_sha, '--', f)[1]) for f in files}
    whole = _sha(git(repo, '--literal-pathspecs', *INTERDIFF, reviewed_head, landed_sha, '--', *sorted(files))[1])
    require(interdiff_sha256 == whole, f'interdiff_sha256 must be {whole} (sha256 of git --literal-pathspecs '
            f"{' '.join(INTERDIFF)} {reviewed_head} {landed_sha} -- {' '.join(sorted(files))})")
    code = stamp()
    with reg.transaction() as state:
        identity = authenticate(reg, state, reviewer, reviewer_generation, chain)
        current = reg.lane(state, key, producer_generation)
        require(current['state'] in LANDING_STATES and current.get(name) == source,
                'Producer source changed while verifying the interdiff')
        authorize(state, reviewer, current)
        row = write(reg, state, dict(kind='landing_review', source='landing_review', lane=key, generation=producer_generation,
                                     repo=name, reviewed_head=reviewed_head, landed_sha=landed_sha, interdiff_sha256=whole,
                                     file_interdiffs=per, files=sorted(files), status=status, conditions=conditions,
                                     evidence=evidence, reviewer=identity), code)
        return copy.deepcopy(row)


def hooks(value):
    """Validated structured shared_hook dependencies, each with a stable id."""
    require(isinstance(value, list), 'shared_hooks must be a list')
    result = []
    for hook in value:
        require(isinstance(hook, dict) and hook.get('kind') == 'shared_hook' and type(hook.get('issue')) is int and
                hook['issue'] > 0 and set(hook) - {'id'} in ({'kind', 'issue', 'files'}, {'kind', 'issue', 'item_id'}),
                'shared_hook needs kind "shared_hook", issue and exactly one of files or item_id')
        spec = {k: hook[k] for k in ('kind', 'issue', 'files', 'item_id') if k in hook}
        if 'files' in spec:
            files = spec['files']
            require(isinstance(files, list) and files and len(set(files)) == len(files) and all(
                nonempty(f) and '\\' not in f and str(PurePosixPath(f)) == f and not f.startswith('/') and
                '..' not in PurePosixPath(f).parts for f in files), 'shared_hook files must be repository-relative paths')
            spec['files'] = sorted(files)
        else:
            require(nonempty(spec['item_id']), 'shared_hook item_id required')
        result.append(dict(spec, id=fingerprint(spec)[:16]))
    require(len({h['id'] for h in result}) == len(result), 'Duplicate shared_hook dependency')
    return result


def hook_state(rows, lane, hook):
    """(satisfied, latest decision); satisfied only while the lane holds the pins the decision recorded."""
    row = _hook(rows, lane['lane'], hook['id'])
    return bool(row and row['status'] == 'approved' and row['pins'] == pins(lane)), row


def hook_status(rows, lane):
    """[{id, hook, satisfied, decision, status}] for the lane's structured shared_hooks, from the ledger."""
    result = []
    for hook in lane.get('shared_hooks') or []:
        satisfied, row = hook_state(rows, lane, hook)
        result.append(dict(id=hook['id'], hook=hook, satisfied=satisfied, decision=row and row['id'],
                           status=row and row['status']))
    return result


def shared_hook_decision(reg, reviewer, reviewer_generation, hook, lanes, status, evidence, conditions=(), commit=None):
    """Decision on non-owned shared files or a hook item, recorded against each named lane holding that hook."""
    from .landing import SHA, lines, objects, repository
    from .provenance import stamp
    require(status in STATUSES, 'Explicit approved/rejected shared-hook decision required')
    spec = hooks([hook])[0]
    conditions = _conditions(list(conditions))
    require(isinstance(lanes, list) and lanes and all(isinstance(t, dict) and set(t) == {'key', 'generation'}
            for t in lanes) and len({t['key'] for t in lanes}) == len(lanes), 'lanes [{key, generation}] required')
    reg.evidence(evidence)
    subject = None
    if 'files' in spec:
        require(isinstance(commit, str) and SHA.fullmatch(commit), 'A files hook decision pins the full commit reviewed')
        repos = {'native' if f.startswith('native/') else 'root' for f in spec['files']}
        require(len(repos) == 1, 'A shared_hook decision covers files of one repository')
        name = repos.pop()
        paths = [f[len('native/'):] if name == 'native' else f for f in spec['files']]
        found = objects(repository(reg.root, name, lines(reg.root)), [commit + ':' + p for p in paths])
        require(all(found.values()), f'Hook files missing at {commit}')
        subject = dict(repo=name, commit=commit, blobs={p: found[commit + ':' + p][0] for p in paths})
    else:
        require(commit is None, 'commit applies to files hooks only')
    chain = ancestry()
    code = stamp()
    with reg.transaction() as state:
        identity = authenticate(reg, state, reviewer, reviewer_generation, chain)
        result = []
        for target in lanes:
            lane = reg.lane(state, target['key'], target['generation'])
            require(spec['id'] in [h.get('id') for h in lane.get('shared_hooks', [])],
                    target['key'] + ' holds no matching shared_hook dependency')
            authorize(state, reviewer, lane)
            row = write(reg, state, dict(kind='shared_hook', source='shared_hook', lane=lane['lane'],
                                         generation=lane['generation'], hook_id=spec['id'], hook=spec, pins=pins(lane),
                                         subject=subject, status=status, conditions=conditions, evidence=evidence,
                                         reviewer=identity), code)
            reg.event(state, 'shared_hook_decided', lane['lane'], approval=row['id'], hook=spec['id'], status=status)
            result.append(copy.deepcopy(row))
        return result


RETRY_SECONDS = 60


def completer(rows, lane):
    """The approval that most recently made every structured shared_hook of the lane satisfied, while it holds."""
    hooks = lane.get('shared_hooks') or []
    if not hooks or not all(hook_state(rows, lane, h)[0] for h in hooks):
        return None
    ids = {h['id'] for h in hooks}
    latest, complete, result = {}, False, None
    for row in sorted((r for r in rows.values() if r.get('kind') == 'shared_hook' and r.get('lane') == lane['lane']
                       and r.get('hook_id') in ids and r.get('pins') == pins(lane)),
                      key=lambda r: (r.get('at', 0), r.get('seq', 0), r['id'])):
        latest[row['hook_id']] = row['status']
        now = all(latest.get(i) == 'approved' for i in ids)
        if now and not complete:
            result = row['id']
        complete = now
    return result


def tick(controller):
    """Wake a blocked lane for a rejected shared_hook decision at its current pins, or for the approval
    that first completes all of its hooks there; other approvals are recorded ledger facts and launch nothing.

    Never writes except through plan_launch, whose reason token is the durable wake marker.
    Reads the ledger, one lane record per lane with an open decision and, only when a lane
    is waiting at decided pins, the launches, leases and queue sections. Decisions that can
    never wake (lane done or past that generation, or already woken) are remembered in
    memory; a lane refused as not recovery-safe is retried after RETRY_SECONDS."""
    from .storage import read_record
    reg, now = controller.reg, controller.reg.clock()
    closed = getattr(controller, '_shared_hook_closed', None)
    if closed is None:
        closed = set(); controller._shared_hook_closed = closed
    retry = getattr(controller, '_shared_hook_retry', None)
    if retry is None:
        retry = {}; controller._shared_hook_retry = retry
    ledger_rows = reg.snapshot(section=('approvals',))
    rows = [r for r in ledger_rows.values() if r.get('kind') == 'shared_hook' and
            r['id'] not in closed and retry.get(r['id'], 0) <= now and r['lane'] in controller.config['lanes']]
    lanes, launches, safety = {}, None, None
    for row in sorted(rows, key=lambda r: (r['at'], r.get('seq', 0))):
        key = row['lane']
        if key not in lanes:
            lanes[key] = read_record(reg, ('lanes',), key) or {}
        lane = lanes[key]
        if not lane or lane.get('state') == 'done' or lane.get('generation', 0) > row['generation']:
            closed.add(row['id']); continue
        if lane.get('state') != 'blocked' or lane.get('generation') != row['generation'] or pins(lane) != row['pins']:
            continue  # Not waiting at the decided pins; the row stays a ledger fact.
        if row['status'] == 'approved' and completer(ledger_rows, lane) != row['id']:
            closed.add(row['id']); continue  # Recorded without a launch: it does not complete the hook set.
        if launches is None:
            launches = reg.snapshot(section=('control', 'launches'))
        token = 'shared-hook-decision:' + row['id']
        if any(x['lane'] == key and x.get('reason') == token for x in launches.values()):
            closed.add(row['id']); continue
        if any(x['lane'] == key and x.get('status') in ('intent', 'spawned', 'running', 'exiting') for x in launches.values()):
            retry[row['id']] = now + RETRY_SECONDS; continue
        if safety is None:
            safety = dict(leases=reg.snapshot(section=('leases',)), queue=reg.snapshot(section=('queue',)))
        if not reg.recovery_safe(safety, lane) or not controller.available(key):
            retry[row['id']] = now + RETRY_SECONDS; continue
        try:
            reg.evidence(row['evidence'])
            reg.plan_launch(key, token,
                'An authenticated decision was recorded on your structured shared_hook dependency. It holds only at '
                'your current root/native pins and only for its exact hook scope; it is not source integration, '
                'runtime acceptance or ADMIT. Read its hashed evidence and conditions, keep every unrelated blocker, '
                'and continue or apply the requested correction. Decision: ' + json.dumps(row), controller.config['models'],
                inputs=['hook:' + fingerprint([row['hook_id'], row['status'], row['pins'],
                                               row.get('conditions') if row['status'] != 'approved' else None])])
            closed.add(row['id'])
        except (Rejected, OSError, ValueError) as exc:
            retry[row['id']] = now + RETRY_SECONDS
            if not isinstance(exc, Parked): reg.notice(key, 'shared_hook_decision_blocked', dict(id=row['id'], error=str(exc)))


def legacy(state, root):
    """Read-only list of recorded approvals with no ledger row, each marked unauthenticated-legacy."""
    rows = state.get('approvals', {})
    items = []

    def add(category, lane, file, reviewer, **extra):
        text = reviewer if isinstance(reviewer, str) else None
        kind = 'none' if not text else 'registered-lane' if text in state.get('lanes', {}) else 'free-text'
        items.append(dict(category=category, lane=lane, file=file, reviewer=reviewer, reviewer_kind=kind,
                          lane_state=state.get('lanes', {}).get(lane, {}).get('state'), marking='unauthenticated-legacy', **extra))

    for identity, item in sorted(state.get('throughput', {}).get('dispositions', {}).items()):
        if item.get('approval') in rows:
            continue
        request = item.get('request', {})
        add('disposition', _lane_of(root, item), request.get('file'),
            request.get('reviewer'), status=request.get('status'), id=identity, at=item.get('at'))
    for identity, item in sorted(state.get('shared_review_decisions', {}).items()):
        if not item.get('approvals'):
            for d in item.get('decisions', []):
                add('queued_decision', item.get('key'), d.get('file'), item.get('reviewer'), status=d.get('status'),
                    id=identity, decision_status=item.get('status'))
    for identity, item in sorted(state.get('shared_preflight_decisions', {}).items()):
        if item.get('approval') not in rows:
            lane = state.get('lanes', {}).get(item.get('lane'), {})
            current = {k: (lane.get(k) or {}).get('head') for k in ('root', 'native')}
            add('preflight', item.get('lane'), item.get('file'), item.get('reviewer'), status=item.get('status'),
                id=identity, at_current_pins=bool(lane) and item.get('source_pins') == current)
    for key, lane in sorted(state.get('lanes', {}).items()):
        handoff = lane.get('handoff')
        if not handoff:
            continue
        try:
            data = json.loads(local_path(root, handoff['path']).read_text(encoding='utf-8-sig'))
        except (Rejected, OSError, ValueError, KeyError, TypeError):
            continue
        for review in data.get('shared_reviews', []) if isinstance(data, dict) else []:
            if not isinstance(review, dict) or review.get('status') not in STATUSES:
                continue
            if decision(rows, lane, review.get('file')) is not None:
                continue
            via = any(str(e).startswith('disposition_') for e in review.get('evidence') or [])
            add('handoff_status' if not via else 'handoff_status_via_disposition', key, review.get('file'),
                review.get('reviewer'), status=review.get('status'))
    summary = {}
    for item in items:
        summary[item['category']] = summary.get(item['category'], 0) + 1
    done = {i['lane'] for i in items if i['category'] == 'handoff_status' and i['lane_state'] == 'done'}
    free = sum(i['category'] == 'disposition' and i['reviewer_kind'] == 'free-text' for i in items)
    mid = sorted({i['lane'] for i in items if i['lane_state'] in ('handoff_ready', 'integrating', 'blocked') and (
        i['category'].startswith('handoff_status') or (i['category'] == 'preflight' and i['at_current_pins'] and i['status'] == 'approved'))})
    return dict(summary=dict(summary, done_lanes_producer_written=len(done), free_text_dispositions=free,
                             mid_flight_lanes=len(mid)), mid_flight=mid, items=items)


def _lane_of(root, item):
    """Producer named by a disposition's frozen handoff, else None."""
    try:
        return json.loads(local_path(root, item['snapshot']['handoff']['path']).read_text(encoding='utf-8-sig')).get('lane')
    except (Rejected, OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def main(argv=None):
    import argparse
    import sqlite3
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('landing-review', 'shared-hook'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True, help='UTF-8 JSON arguments')
    args = parser.parse_args(argv)
    from .registry import Registry
    root = args.root.resolve()
    try:
        reg = Registry(root / 'output/workflow/registry.sqlite3', root)
        request = json.loads(args.request.read_text(encoding='utf-8-sig'))
        require(isinstance(request, dict), 'Request must be a JSON object')
        result = (landing_review if args.command == 'landing-review' else shared_hook_decision)(reg, **request)
    except (Rejected, OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc) or type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
