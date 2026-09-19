"""Transactional, single-host lane registry. No builds, task dispatch or kills."""
from contextlib import contextmanager, nullcontext
import copy
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time
import uuid
import threading
import traceback

from .handoff import GATES, digest, local_path, nonempty, phantom_shared_reviews, require, source_record, validate_handoff
from .processes import identify, probe, DeadIdentityCache

STATES = {'ready', 'running', 'waiting_resource', 'blocked', 'handoff_ready', 'integrating', 'done', 'review_ready', 'reconciling'}
ACTIVE = {'ready', 'running', 'waiting_resource', 'blocked', 'reconciling'}
TRANSITIONS = {
    'ready': {'running', 'blocked'},
    'running': {'waiting_resource', 'blocked'},
    'waiting_resource': {'running', 'blocked'},
    'blocked': {'ready', 'running'},
    'handoff_ready': {'running', 'integrating'},
    'integrating': {'running', 'handoff_ready'},
    'review_ready': {'running', 'integrating', 'blocked'},
    'reconciling': {'running', 'blocked', 'ready'},
    'done': set(),
}
DEFAULTS = dict(max_heavy_builds=2, heartbeat_seconds=300, progress_seconds=1800,
                failure_limit=3, handoff_limit=2, handoff_age_seconds=3600)


def new_id():
    return uuid.uuid4().hex


from .control import ControlMixin
from .remote import RemoteMixin, check_remote_ownership
from .delivery import DeliveryMixin
from .scheduling import SchedulingMixin
from .batching import BatchingMixin


class Registry(SchedulingMixin, DeliveryMixin, BatchingMixin, ControlMixin, RemoteMixin):
    def __init__(self, path, root, *, clock=time.time, process_probe=probe):
        self.path, self.root = Path(path).resolve(), Path(root).resolve()
        require(self.path.is_relative_to(self.root / 'output'), 'Registry must be under workspace output/')
        self.clock, self.probe = clock, process_probe
        if process_probe is probe:
            self.probe = DeadIdentityCache(process_probe, unknown_seconds=5)
        self._transaction_local = threading.local()

    def snapshot(self, *, section=None, sections=None):
        """Read one committed registry version; never reserve the writer lock.

        Rows are fetched inside the read transaction and decoded after it ends, so a
        reader holds SQLite's SHARED lock only while copying bytes. sections=(...)
        decodes just those partitions; every other partition is Sealed and refuses use."""
        from . import storage
        require(self.path.is_file(), 'Registry missing; run init first')
        require(section is None or sections is None, 'Pass section or sections, not both')
        only = None
        if sections is not None: only, _ = storage.declared(sections)
        elif section: only = [p for p in storage.PARTS if p[:len(section)] == tuple(section)]
        def read():
            db = sqlite3.connect(self.path, timeout=storage.BUSY_TIMEOUT)
            try:
                db.execute('PRAGMA query_only=ON')
                db.execute('BEGIN')
                return storage.fetch(db, only)
            finally:
                db.close()
        descriptor, raw = storage.retry(read, 'registry read')
        state = storage.decode(descriptor, raw, only)
        require(state['schema'] == 1 and state['root'] == str(self.root), 'Registry workspace/schema mismatch')
        if sections is not None:
            storage.seal(state, raw, only)
        elif section:
            for key in section:state=state.get(key,{})
        return state

    @contextmanager
    def transaction(self, sections=None, append=()):
        """Serialized write. sections=(path, ...) loads and saves only those documents-v1
        partitions plus the meta row; append=(list path, ...) exposes a history as
        append-only. Touching any other partition refuses and rolls back."""
        from . import storage
        require(not getattr(self._transaction_local, 'active', False), 'Nested registry write transaction')
        require(self.path.is_file(), 'Registry missing; run init first')
        if sections is not None: sections, append = storage.declared(sections, append)
        db = sqlite3.connect(self.path, timeout=storage.BUSY_TIMEOUT)
        started = time.monotonic()
        acquired = None
        self._transaction_local.active = True
        from .write_gate import gate
        writer = gate(self.path)
        entered = False
        try:
            writer.acquire(); entered = True
            storage.begin(db)
            acquired = time.monotonic()
            if sections is None:
                state, previous = storage.load(db)
            else:
                state, previous, marks = storage.open_sections(db, sections, append)
            require(state['schema'] == 1 and state['root'] == str(self.root), 'Registry workspace/schema mismatch')
            yield state
            if sections is None: storage.save(db, state, previous)
            else: storage.save_sections(db, state, previous, sections, marks)
            storage.commit(db)
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
            if entered:writer.release()
            self._transaction_local.active = False
            elapsed = time.monotonic() - started
            if elapsed >= 2:
                try:
                    record = dict(at=self.clock(), thread=threading.current_thread().name,
                        elapsed_seconds=elapsed, wait_seconds=(acquired-started) if acquired else elapsed,
                        sections=None if sections is None else ['.'.join(p) for p in sections],
                        stack=traceback.format_stack(limit=8))
                    with self.path.with_name('slow-transactions.jsonl').open('a', encoding='utf-8') as log:
                        log.write(json.dumps(record) + '\n')
                except OSError:
                    pass

    def init(self, settings=None):
        settings = settings or {}
        require(set(settings) <= set(DEFAULTS), 'Unknown setting')
        require(all(type(v) is int and v > 0 for v in settings.values()), 'Settings must be positive integers')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS registry (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            require(db.execute('SELECT id FROM registry').fetchone() is None, 'Registry already initialized')
            state = dict(schema=1, root=str(self.root), settings=DEFAULTS | settings,
                         lanes={}, leases={}, queue={}, actions={}, events=[])
            db.execute('INSERT INTO registry VALUES (1, ?)', (json.dumps(state),))
            db.commit()
            return state['settings']
        finally:
            db.close()

    def event(self, state, kind, lane, **detail):
        state['wake_revision'] = state.get('wake_revision', len(state['events'])) + 1
        state['events'].append(dict(at=self.clock(), kind=kind, lane=lane, **detail))

    def throughput_status(self, window_seconds=3600, ram_percent=None, state=None):
        """Reads the caller's snapshot when given; process checks use the dead-identity cache."""
        from .analytics import throughput_metrics, staffing_recommendations
        with nullcontext(self.snapshot() if state is None else state) as state:
            return dict(at=self.clock(), throughput=state.get('throughput', {}),
                        metrics=throughput_metrics(state, self.clock(), window_seconds=window_seconds),
                        staffing=staffing_recommendations(state, self.clock(), ram_percent=ram_percent,
                                                          process_probe=self.probe))

    def configure_lane_launch(self, key, root, output, brief, config, legacy_supervisors=None):
        """Attach local launch paths to an issue-backed pool lane without restarting service."""
        paths = {name: local_path(self.root, value) for name, value in
                 dict(root=root, output=output, brief=brief, config=config).items()}
        require(paths['root'].is_dir() and paths['brief'].is_file() and paths['config'].is_file(),
                'Prepared worktree, brief and provider config required')
        require(paths['output'].is_relative_to(self.root / 'output'), 'Private output required')
        owners = legacy_supervisors or []
        require(isinstance(owners, list) and all(isinstance(p, dict) and
                set(('host', 'pid', 'started')) <= p.keys() for p in owners), 'Process identities required')
        record = {name: str(path) for name, path in paths.items()} | {'legacy_supervisors': owners}
        with self.transaction() as state:
            lane = self.lane(state, key)
            require(paths['root'] == local_path(self.root, lane['root']['worktree']),
                    'Launch worktree must match issue lane source')
            specs = state.setdefault('throughput_runtime', {}).setdefault('launch_specs', {})
            if specs.get(key) == record:
                return record
            require(self.recovery_safe(state, lane), 'Do not change launch paths of live execution')
            require(not any(i['lane'] == key and i['status'] in ('intent', 'spawned', 'running')
                            for i in self.control(state)['launches'].values()), 'Launch already in flight')
            specs[key] = record
            self.event(state, 'launch_spec_configured', key)
            return record

    def lane(self, state, key, generation=None, revision=None):
        require(key in state['lanes'], 'Unknown lane: ' + key)
        lane = state['lanes'][key]
        if generation is not None:
            require(lane['generation'] == generation, 'Stale ownership generation')
        if revision is not None:
            require(lane['revision'] == revision, 'Stale lane revision; read status before retrying')
        return lane

    def check_wip(self, state, lane):
        from .worker_capacity import reusable
        others = [l for l in state['lanes'].values()
                  if l['lane'] != lane['lane'] and l['worker_id'] == lane['worker_id']]
        if lane['state'] in ACTIVE:
            require(not any(l['state'] in ACTIVE and not reusable(self, state, l) for l in others), 'Worker already has one active slice')
        if lane['state'] in ('handoff_ready', 'review_ready', 'integrating'):
            require(not any(l['state'] in ('handoff_ready', 'review_ready', 'integrating') for l in others),
                    'Worker already has one ready/integrating handoff')

    def register(self, data):
        data = copy.deepcopy(data)
        for key in ('lane', 'owner', 'worker_id', 'task_id', 'scope', 'target_level', 'next_action', 'milestone'):
            require(nonempty(data.get(key)), key + ' required')
        require(re.fullmatch(r'[a-z0-9][a-z0-9_-]*', data['lane']), 'Use a stable lowercase lane ID')
        require(type(data.get('issue')) is int and data['issue'] > 0, 'Issue required before claim')
        for key in ('owned_files', 'acceptance'):
            require(isinstance(data.get(key), list) and data[key] and all(nonempty(v) for v in data[key]),
                    key + ' required')
        require(len(set(data['owned_files'])) == len(data['owned_files']), 'Duplicate owned file')
        require(isinstance(data.get('closes_gates', []), list) and
                all(g in GATES for g in data.get('closes_gates', [])), 'Unknown intended acceptance gate')
        data.setdefault('closes_gates', [])
        for name in data['owned_files']:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name and
                    ':' not in name and str(PurePosixPath(name)) == name,
                    'Owned files use normalized repository-relative paths')
        source_record(data.get('root'), 'root')
        if data.get('native') is not None:
            source_record(data['native'], 'native')
        require(type(data.get('pid')) is int, 'Long-lived worker PID required')
        process = identify(data.pop('pid'))
        data.update(state='ready', revision=1, generation=1, process=process, dependencies=[],
                    created_at=self.clock(), started_at=None, heartbeat_at=self.clock(),
                    progress_at=self.clock(), progress_detail='Registered', handoff_at=None,
                    progress_evidence=None,
                    failure_streak=0, recovery_count=0, failure_fingerprint=None, handoff=None, integrated_at=None)
        with self.transaction() as state:
            require(data['lane'] not in state['lanes'], 'Lane ID already registered')
            check_remote_ownership(state, data['issue'], data['owned_files'])
            for other in state['lanes'].values():
                if other['state'] != 'done':
                    require(other['issue'] != data['issue'], 'Issue already has an unfinished lane')
                    require(not ({f.casefold() for f in other['owned_files']} &
                                 {f.casefold() for f in data['owned_files']}), 'Owned files overlap another lane')
            self.check_wip(state, data)
            state['lanes'][data['lane']] = data
            self.event(state, 'registered', data['lane'])
            return data

    def heartbeat(self, key, generation):
        from .storage import selected
        with selected(self, [(('lanes',),key)]) as rows:
            lane = rows[(('lanes',),key)]
            require(lane is not None, 'Unknown lane: ' + key)
            require(lane['generation'] == generation, 'Stale ownership generation')
            require(lane['state'] != 'done', 'Lane is done')
            lane['heartbeat_at'] = self.clock()
            # Liveness updates do not change revision or progress.
            return {'heartbeat_at': lane['heartbeat_at'], 'revision': lane['revision']}

    def checkpoint(self, key, generation, revision, changes, progress=None):
        require(set(changes) <= {'state', 'next_action', 'dependencies', 'root', 'native', 'shared_hooks'},
                'Unknown checkpoint field')
        if 'shared_hooks' in changes:
            from .approvals import hooks
            changes = dict(changes, shared_hooks=hooks(changes['shared_hooks']))
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            require(lane['state'] != 'done', 'Lane is done')
            target = changes.get('state', lane['state'])
            require(target == lane['state'] or target in TRANSITIONS[lane['state']], 'Invalid state transition')
            if target == 'integrating':
                self.check_handoff(lane, state)
            if 'dependencies' in changes:
                require(isinstance(changes['dependencies'], list) and
                        all(nonempty(x) for x in changes['dependencies']), 'Dependencies must be lane IDs or issue references')
                require(key not in changes['dependencies'], 'Lane cannot depend on itself')
            for repo in ('root', 'native'):
                if repo in changes:
                    require(target in ACTIVE, 'Resume implementation before changing source identity')
                    if changes[repo] is not None or repo == 'root':
                        source_record(changes[repo], repo)
            if 'next_action' in changes:
                require(nonempty(changes['next_action']), 'Next action cannot be empty')
            require('shared_hooks' not in changes or target == 'blocked', 'shared_hooks belong to a blocked lane')
            if target == 'blocked' and lane['state'] != 'blocked' and 'shared_hooks' not in changes:
                lane.pop('shared_hooks', None)  # A new blocked state declares its own structured hooks.
            lane.update(changes)
            if target == 'blocked':
                require(lane['dependencies'], 'Blocked lane needs dependency/issue reference')
            if target == 'waiting_resource':
                require(any(q['lane'] == key and q['generation'] == generation for q in state['queue'].values()),
                        'Waiting resource requires an actual queued request')
            self.check_wip(state, lane)
            if target == 'running' and lane['started_at'] is None:
                lane['started_at'] = self.clock()
            if target in ACTIVE:
                lane['handoff'] = None
                lane['handoff_at'] = None
                lane.pop('handoff_code_revision', None)
            if progress is not None:
                require(isinstance(progress, dict) and nonempty(progress.get('summary')),
                        'Meaningful progress requires a summary and hashed evidence')
                evidence = local_path(self.root, progress.get('path'))
                require(evidence.is_file() and digest(evidence) == progress.get('sha256'), 'Progress evidence missing/changed')
                require(lane['progress_evidence'] is None or lane['progress_evidence']['sha256'] != progress['sha256'],
                        'Unchanged evidence is not new progress')
                lane['progress_at'], lane['progress_detail'] = self.clock(), progress['summary']
                lane['progress_evidence'] = progress
                lane['failure_streak'], lane['failure_fingerprint'] = 0, None
                lane['recovery_count'] = 0
                self.event(state, 'progress', key, evidence=progress)
            lane['revision'] += 1
            self.event(state, 'checkpoint', key, execution_state=target)
            return lane

    def failure(self, key, generation, attempt_id, fingerprint, evidence):
        require(nonempty(attempt_id) and nonempty(fingerprint), 'Attempt ID and stable failure fingerprint required')
        path = local_path(self.root, evidence.get('path'))
        require(path.is_file() and digest(path) == evidence.get('sha256'), 'Failure evidence missing/changed')
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            prior = [e for e in state['events'] if e['kind'] == 'failure' and e['lane'] == key and e['attempt_id'] == attempt_id]
            if prior:
                require(prior[0]['fingerprint'] == fingerprint and prior[0]['evidence'] == evidence,
                        'Attempt ID reused for a different failure')
                return {'duplicate': True, 'failure_streak': lane['failure_streak']}
            lane['failure_streak'] = lane['failure_streak'] + 1 if lane['failure_fingerprint'] == fingerprint else 1
            lane['failure_fingerprint'] = fingerprint
            self.event(state, 'failure', key, attempt_id=attempt_id, fingerprint=fingerprint, evidence=evidence,
                       generation=generation, source_pins={k:(lane.get(k) or {}).get('head') for k in ('root','native')})
            return {'duplicate': False, 'failure_streak': lane['failure_streak']}

    def resource(self, name):
        if name in ('maintained-build-export', 'shared-runtime'):
            return name
        require(name.startswith('build:'), 'Resource must be maintained-build-export, shared-runtime or build:<path>')
        path = local_path(self.root, name[6:])
        require(path.is_relative_to(self.root / 'output') and path != self.root / 'output',
                'Private build must be under output/')
        return 'build:' + str(path).casefold()

    @staticmethod
    def heavy(resource):
        return resource == 'maintained-build-export' or resource.startswith('build:')

    def reap_dead_build_leases(self, state):
        """Caller holds the registry transaction; expiry never proves death."""
        released=[]
        for resource, lease in list(state['leases'].items()):
            if not self.heavy(resource) or self.probe(lease['process'])!='dead':continue
            del state['leases'][resource]
            released.append(resource)
            self.event(state,'lease_reaped',lease['lane'],resource=resource,
                       reason='independent_build_capacity_monitor',process=lease['process'],
                       generation=lease.get('generation'))
        state['build_lease_recovery']=dict(at=self.clock(),released=released,
            remaining=sum(self.heavy(k) for k in state['leases']))
        return released

    def drop_leases(self, state, key, reason):
        """Caller proved the owners stopped; every dropped lease still closes its interval."""
        for resource, lease in list(state['leases'].items()):
            if lease['lane'] != key: continue
            del state['leases'][resource]
            self.event(state, 'lease_reaped', key, resource=resource, reason=reason,
                       process=lease.get('process'), generation=lease.get('generation'))

    def acquire(self, key, generation, resource, pid, ttl=300):
        resource = self.resource(resource)
        require(type(ttl) is int and 1 <= ttl <= 3600, 'Lease TTL must be 1–3600 seconds')
        identity = identify(pid)
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            require(lane['state'] != 'done', 'Lane is done')
            # Exact process death permits release even before TTL, just like
            # release(). Expiry alone never proves the process has stopped.
            for name, lease in list(state['leases'].items()):
                if self.probe(lease['process']) == 'dead':
                    self.event(state, 'lease_reaped', lease['lane'], resource=name)
                    del state['leases'][name]
            existing = state['leases'].get(resource)
            if existing and existing['lane'] == key and existing['generation'] == generation:
                require(existing['process'] == identity, 'Lease already held by a different process')
                return {'acquired': True, 'lease': existing}
            request_id = f'{key}:{generation}:{resource}'
            # A dead waiter must not block the queue forever. Unknown/live waiters
            # retain their place until explicitly cancelled.
            for queued_id, queued in list(state['queue'].items()):
                if self.clock() - queued['requested_at'] > state['settings']['heartbeat_seconds'] and self.probe(queued['process']) == 'dead':
                    self.event(state, 'request_reaped', queued['lane'], resource=queued['resource'], wait_seconds=self.clock() - queued['requested_at'])
                    del state['queue'][queued_id]
            request = state['queue'].setdefault(request_id, dict(id=request_id, lane=key,
                generation=generation, resource=resource, requested_at=self.clock(), process=identity))
            require(request['process'] == identity, 'Cancel previous queued request before changing process')
            # FIFO for an exclusive resource and for the aggregate heavy-build pool.
            earlier = [q for q in state['queue'].values() if q['id'] != request_id and
                       (q['requested_at'], q['id']) < (request['requested_at'], request_id) and
                       q['resource'] not in state['leases'] and
                       (q['resource'] == resource or (self.heavy(resource) and self.heavy(q['resource'])))]
            count = sum(self.heavy(r) for r in state['leases'])
            # Reserve capacity for earlier independent resources without making
            # a live but non-polling waiter serialize the entire build pool.
            # Multiple waiters for one directory need only one reserved slot.
            same_resource_wait = any(q['resource'] == resource for q in earlier)
            reserved = len({q['resource'] for q in earlier if self.heavy(q['resource'])})
            from .build_capacity import admission_paused
            if existing or same_resource_wait or (self.heavy(resource) and
                    (count + reserved >= state['settings']['max_heavy_builds'] or admission_paused(state, self.clock()))):
                return {'acquired': False, 'request': request, 'reason': 'held, earlier request, or build capacity'}
            lease = dict(token=new_id(), lane=key, generation=generation, resource=resource,
                         process=identity, acquired_at=self.clock(), expires_at=self.clock() + ttl)
            state['leases'][resource] = lease
            del state['queue'][request_id]
            self.event(state, 'lease_acquired', key, resource=resource,
                       wait_seconds=self.clock() - request['requested_at'])
            return {'acquired': True, 'lease': lease}

    def renew(self, key, generation, resource, token, ttl=300):
        resource = self.resource(resource)
        require(type(ttl) is int and 1 <= ttl <= 3600, 'Lease TTL must be 1–3600 seconds')
        with self.transaction() as state:
            self.lane(state, key, generation)
            lease = state['leases'].get(resource)
            require(lease and (lease['lane'], lease['generation'], lease['token']) == (key, generation, token),
                    'Lease token/owner mismatch')
            require(self.probe(lease['process']) == 'alive', 'Lease owner is not confirmed alive')
            lease['expires_at'] = self.clock() + ttl
            return lease

    def release(self, key, generation, resource, token):
        resource = self.resource(resource)
        with self.transaction() as state:
            self.lane(state, key, generation)
            lease = state['leases'].get(resource)
            require(lease and (lease['lane'], lease['generation'], lease['token']) == (key, generation, token),
                    'Lease token/owner mismatch')
            require(self.probe(lease['process']) == 'dead', 'Protected process must stop before lease release')
            del state['leases'][resource]
            self.event(state, 'lease_released', key, resource=resource)
            return {'released': resource}

    def cancel_request(self, key, generation, request_id):
        with self.transaction() as state:
            self.lane(state, key, generation)
            request = state['queue'].get(request_id)
            require(request and request['lane'] == key and request['generation'] == generation, 'Request owner mismatch')
            del state['queue'][request_id]
            self.event(state, 'request_cancelled', key, resource=request['resource'], wait_seconds=self.clock() - request['requested_at'])
            return {'cancelled': request_id}

    def recovery_safe(self, state, lane):
        queued = state['queue'].values() if 'queue' in state else state.get('requests', [])
        return self.probe(lane['process']) == 'dead' and all(
            self.probe(owner['process']) == 'dead'
            for owner in [*state['leases'].values(), *queued] if owner['lane'] == lane['lane'])

    def watchdog(self):
        """Persist deduplicated recommendations. Never launch or terminate a task."""
        with self.transaction() as state:
            results = []
            for key, lane in state['lanes'].items():
                if lane['state'] in ('done', 'review_ready', 'reconciling', 'integrating'):
                    continue
                phantom = phantom_shared_reviews(self.root, lane) if lane['state'] == 'handoff_ready' else []
                if lane['state'] == 'handoff_ready' and not phantom:
                    continue  # No mechanism redispatches a legitimately pending review.
                kind, reason = None, None
                settings = state['settings']
                if lane['failure_streak'] >= settings['failure_limit']:
                    kind, reason = 'escalate', 'Repeated failure: ' + str(lane['failure_fingerprint'])
                elif lane['recovery_count'] >= settings['failure_limit']:
                    kind, reason = 'escalate', 'Recovery budget exhausted without meaningful progress'
                elif phantom and any(l['lane'] == key and l['status'] in ('intent', 'spawned', 'running')
                                      for l in state.get('control', {}).get('launches', {}).values()):
                    pass  # A launch is already in flight for this lane; do not double-dispatch.
                elif phantom and self.recovery_safe(state, lane):
                    kind, reason = 'recover', ('Handoff pending review names file(s) never in changed_files: ' +
                                                ', '.join(phantom))
                elif lane['state'] in ('blocked', 'waiting_resource'):
                    if self.clock() - lane['progress_at'] >= settings['progress_seconds']:
                        kind, reason = 'check_dependency', 'Inspect dependency or resource wait; do not restart'
                elif self.recovery_safe(state, lane):
                    kind, reason = 'recover', 'Recorded worker and protected processes confirmed stopped'
                elif self.clock() - lane['progress_at'] >= 2 * settings['progress_seconds']:
                    kind, reason = 'escalate', 'No meaningful progress after the diagnosis budget'
                elif self.clock() - lane['progress_at'] >= settings['progress_seconds']:
                    kind, reason = 'checkpoint', 'No meaningful progress; diagnose before restarting'
                elif self.clock() - lane['heartbeat_at'] >= settings['heartbeat_seconds']:
                    kind, reason = 'checkpoint', 'Missed heartbeat; ownership remains unchanged'
                if kind is None:
                    continue
                # One action of each kind per ownership generation and progress checkpoint.
                dedupe = f'{key}:{lane["generation"]}:{lane["progress_at"]}:{kind}'
                action = next((a for a in state['actions'].values() if a['dedupe'] == dedupe), None)
                if action is None:
                    action = dict(id=new_id(), dedupe=dedupe, lane=key, generation=lane['generation'],
                                  progress_at=lane['progress_at'], kind=kind, reason=reason,
                                  status='pending', created_at=self.clock(), consumer=None)
                    state['actions'][action['id']] = action
                    self.event(state, 'watchdog_action', key, action=action['id'], action_kind=kind)
                results.append(action)
            return results

    def claim_action(self, action_id, consumer):
        require(nonempty(consumer), 'Dispatcher identity required')
        with self.transaction() as state:
            require(action_id in state['actions'], 'Unknown action')
            action = state['actions'][action_id]
            lane = self.lane(state, action['lane'], action['generation'])
            require(action['progress_at'] == lane['progress_at'], 'Action superseded by progress')
            require(action['status'] == 'pending', 'Action already claimed/completed; reconcile instead of redispatching')
            if action['kind'] == 'recover':
                require((lane['state'] in ('ready', 'running') or
                         (lane['state'] == 'handoff_ready' and phantom_shared_reviews(self.root, lane))) and
                        self.recovery_safe(state, lane), 'Recovery no longer safe')
                require(lane['failure_streak'] < state['settings']['failure_limit'] and
                        lane['recovery_count'] < state['settings']['failure_limit'], 'Recovery budget exhausted')
                require(not any(a['lane'] == lane['lane'] and a['kind'] == 'recover' and a['status'] == 'claimed'
                                for a in state['actions'].values()), 'Recovery already in flight')
                require(not any(l['lane'] == lane['lane'] and l['status'] in ('intent', 'spawned', 'running')
                                for l in state.get('control', {}).get('launches', {}).values()),
                        'Launch already in flight')
            action.update(status='claimed', consumer=consumer, claimed_at=self.clock())
            return action

    def complete_action(self, action_id, consumer, outcome, replacement=None):
        require(nonempty(outcome), 'Outcome/checkpoint reference required')
        with self.transaction() as state:
            require(action_id in state['actions'], 'Unknown action')
            action = state['actions'][action_id]
            if action['status'] == 'completed':
                require(action['consumer'] == consumer and action['outcome'] == outcome and
                        action.get('replacement') == replacement, 'Conflicting action replay')
                return action
            require(action['status'] == 'claimed' and action['consumer'] == consumer, 'Claim action before completing')
            lane = self.lane(state, action['lane'], action['generation'])
            if action['kind'] == 'recover':
                require(isinstance(replacement, dict) and nonempty(replacement.get('task_id')) and
                        type(replacement.get('pid')) is int, 'Recovery needs known replacement task ID and PID')
                require((lane['state'] in ('ready', 'running') or
                         (lane['state'] == 'handoff_ready' and phantom_shared_reviews(self.root, lane))) and
                        self.recovery_safe(state, lane), 'Previous execution must remain stopped')
                identity = identify(replacement['pid'])
                lane.update(generation=lane['generation'] + 1, revision=lane['revision'] + 1,
                            task_id=replacement['task_id'], process=identity, state='ready', handoff=None,
                            recovery_count=lane['recovery_count'] + 1,
                            heartbeat_at=self.clock(), progress_at=self.clock(),
                            progress_detail='Recovered from checkpoint: ' + outcome)
                lane.pop('handoff_code_revision', None)
                # Only confirmed-dead old leases can reach here.
                self.drop_leases(state, lane['lane'], 'recovery')
                state['queue'] = {k: v for k, v in state['queue'].items() if v['lane'] != lane['lane']}
            else:
                require(replacement is None, 'Only recover actions may replace execution')
            action.update(status='completed', outcome=outcome, replacement=replacement, completed_at=self.clock())
            self.event(state, 'action_completed', lane['lane'], action=action_id)
            return action

    def submit_handoff(self, key, generation, revision, path):
        from .provenance import stamp
        code = stamp()
        path = local_path(self.root, path)
        observed=self.snapshot()
        before=self.lane(observed,key,generation,revision)
        frozen=None
        if observed['settings'].get('freeze_handoffs_on_submit',False):
            data=json.loads(path.read_text(encoding='utf-8'))
            result=validate_handoff(self.root,data,before)
            require(data.get('kind')!='review' and result['slice_passed'], 'Passing implementation handoff required')
            # Copy/hash large artifacts outside the registry writer lock.
            frozen=self._delivery_freeze(before,data)
            path=Path(frozen['handoff']['path'])
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            require(all(lane.get(k)==before.get(k) for k in ('root','native')), 'Submission source pins changed')
            require(lane['state'] in ('running', 'handoff_ready', 'integrating'),
                    'Only running/ready/integrating slices can submit a handoff')
            data = json.loads(path.read_text(encoding='utf-8'))
            result = validate_handoff(self.root, data, lane)
            require(data.get('kind') != 'review', 'Use finish review-ready for reviews; reviews are not implementation handoffs')
            require(result['slice_passed'], 'Assigned slice criteria must pass before ready handoff')
            from .approvals import apply
            # A producer-written approved/rejected needs a matching authenticated ledger row; the result carries the ledger's.
            result = apply(state.get('approvals', {}), lane, data, result, strict=True)
            lane.update(state='handoff_ready', handoff_at=lane['handoff_at'] or self.clock(), progress_at=self.clock(),
                        revision=revision + 1, handoff=dict(path=str(path), sha256=digest(path), result=result),
                        handoff_code_revision=code)
            from .no_progress import record
            record(self, state, lane)
            if frozen:
                self.delivery(state)['snapshots'][frozen['handoff']['sha256']]=dict(frozen,lane=key,
                    generation=generation,version='submission',created_at=self.clock())
            self.check_wip(state, lane)
            self.event(state, 'handoff_ready', key)
            return lane

    def check_handoff(self, lane, state=None):
        """pending_reviews comes from the approvals ledger at the lane's pins, never from the handoff's own statuses."""
        from .approvals import apply
        require(lane['handoff'], 'Handoff required')
        path = Path(lane['handoff']['path'])
        require(path.is_file() and digest(path) == lane['handoff']['sha256'], 'Handoff changed after submission')
        data = json.loads(path.read_text(encoding='utf-8'))
        result = validate_handoff(self.root, data, lane)
        require(result['slice_passed'], 'Assigned slice criteria no longer pass')
        rows = state.get('approvals', {}) if state is not None else self.snapshot(section=('approvals',))
        return apply(rows, lane, data, result)

    def integrate(self, key, generation, revision, record, lander=None):
        """The receipt stays exactly as submitted (replays compare it); code and landing proof are siblings.

        The landing proof runs git against the lane read outside the writer lock; the
        transaction then refuses if the proven pins moved in between. The lander is the
        live launch session the caller runs inside (process ancestry); a request lander
        that is not that session refuses, and without one shared-file ports refuse."""
        from . import approvals
        from .provenance import stamp
        from .landing import prove, recheck
        from .storage import read_record
        code = stamp()
        require(isinstance(record, dict), 'Integration record required')
        require(lander is None or (isinstance(lander, dict) and set(lander) == {'lane', 'generation'} and
                nonempty(lander['lane']) and type(lander['generation']) is int), 'lander must be {lane, generation}')
        chain = approvals.ancestry()
        before = read_record(self, ('lanes',), key)
        require(before is not None, 'Unknown lane: ' + key)
        require(before['generation'] == generation, 'Stale ownership generation')
        require(before['revision'] == revision, 'Stale lane revision; read status before retrying')
        require(before['state'] == 'integrating', 'Begin integration before recording completion')
        session = approvals.session(self, chain)
        require(lander is None or session is None or (session['lane'], session['generation']) ==
                (lander['lane'], lander['generation']), 'lander does not match the live launch session calling integrate')
        rows = self.snapshot(section=('approvals',)) if record.get('ports') else {}
        landing = prove(self.root, before, record, session, rows)
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            require(lane['state'] == 'integrating', 'Begin integration before recording completion')
            require(all(lane.get(k) == before.get(k) for k in ('root', 'native', 'handoff')),
                    'Lane source or handoff changed while proving the landing')
            if lander is not None:
                require(self.lane(state, lander['lane'], lander['generation'])['state'] != 'done',
                        'Lander lane is done')
            if session is not None:
                require(approvals.still(state, session), 'Lander session ended while proving the landing')
            recheck(state.get('approvals', {}), key, landing)
            result = self.check_handoff(lane, state)
            require(not result['pending_reviews'], 'Resolve shared reviews before integration: no authenticated '
                    'approval in the approvals ledger at these pins for ' + ', '.join(result['pending_reviews']))
            for name in ('root_commit',):
                require(re.fullmatch(r'[0-9a-f]{40}', record.get(name, '')), 'Full integrated root commit required')
            if lane['native'] is not None:
                require(re.fullmatch(r'[0-9a-f]{40}', record.get('native_commit', '')) and
                        isinstance(record.get('native_dirty'), str) and nonempty(record.get('export_evidence')),
                        'Native commit, dirty state and export evidence required')
            path = local_path(self.root, record.get('validation_path'))
            require(path.is_file() and digest(path) == record.get('validation_sha256'), 'Integration validation evidence mismatch')
            if lane['native'] is not None:
                export = local_path(self.root, record['export_evidence'])
                require(export.is_file() and digest(export) == record.get('export_sha256'),
                        'Export evidence missing/changed')
                # A hashed statement that no export happened is not export proof.
                try:
                    export_record = json.loads(export.read_text(encoding='utf-8-sig'))
                except (ValueError, UnicodeError):
                    export_record = None  # Existing text/log evidence remains supported.
                require(not isinstance(export_record, dict) or export_record.get('action') != 'none-performed',
                        'Export evidence explicitly records no export; obtain actual export evidence')
            landing.update(claimed_lander=lander, reviews=result.get('reviews', {}), self_reviewed=sorted(
                f for f, v in result.get('reviews', {}).items() if session and v.get('reviewer') == session['lane']))
            lane.update(state='done', integrated_at=self.clock(), revision=revision + 1, integration=record,
                        integration_code_revision=code, integration_landing=dict(landing, verified_at=self.clock()))
            self.event(state, 'integrated', key, lead_seconds=self.clock() - (lane['started_at'] or lane['created_at']))
            return lane

    def status(self):
        from .batching import isolated_handoff
        with nullcontext(self.snapshot()) as state:
            now = self.clock()
            owners = {s.get('owner_lane') for s in state.get('throughput', {}).get('workstreams', {}).values()}
            handoffs = [l for l in state['lanes'].values() if l['state'] in ('handoff_ready', 'review_ready', 'integrating')
                        and not isolated_handoff(state.get('throughput', {}).get('batches', {}), l['lane'], l)
                        and not (l['lane'] in owners and l['state'] == 'review_ready' and not l.get('handoff'))]
            backlog = (len(handoffs) >= state['settings']['handoff_limit'] or any(
                now - l['handoff_at'] >= state['settings']['handoff_age_seconds'] for l in handoffs))
            waits = [e['wait_seconds'] for e in state['events'] if 'wait_seconds' in e]
            leads = [e['lead_seconds'] for e in state['events'] if e['kind'] == 'integrated']
            milestones = {}
            from .approvals import hook_status
            for lane in state['lanes'].values():
                if lane.get('shared_hooks'):  # Satisfied only at the pins a ledger decision recorded.
                    lane['shared_hook_status'] = hook_status(state.get('approvals', {}), lane)
                result = lane['handoff']['result'] if lane['handoff'] else None
                milestones.setdefault(lane['milestone'], []).append(dict(lane=lane['lane'],
                    state=lane['state'], outstanding_gates=result['outstanding_gates'] if result else 'not_reported'))
            ready = [l for l in state['lanes'].values() if l['state'] == 'ready' and all(
                d in state['lanes'] and state['lanes'][d]['state'] == 'done' for d in l['dependencies'])]
            priority = sorted(ready, key=lambda l: (-sum(l['lane'] in other['dependencies']
                              for other in state['lanes'].values() if other['state'] != 'done'),
                              -len(l['closes_gates']), l['created_at']))
            return dict(lanes=state['lanes'], leases=state['leases'], requests=list(state['queue'].values()),
                        actions=list(state['actions'].values()), settings=state['settings'],
                        metrics=dict(handoff_queue=[dict(lane=l['lane'], age_seconds=now-l['handoff_at']) for l in handoffs],
                            resource_waits=[dict(id=q['id'], age_seconds=now-q['requested_at']) for q in state['queue'].values()],
                            completed_wait_seconds=waits, integrated_lead_seconds=leads,
                            failure_attempts=sum(e['kind'] == 'failure' for e in state['events']),
                            completed_slices=len(leads), milestones=milestones),
                        dispatch=dict(pause_new_slices=backlog,
                            reason='Clear integration backlog' if backlog else 'Prioritize ready dependencies and milestone gates',
                            suggested_lanes=[] if backlog else [l['lane'] for l in priority]))
