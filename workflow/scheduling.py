"""Issue-backed reusable worker scheduling; dispatch stays in the controller.

Queue records never transfer lane ownership or manufacture sessions. An assignment
reserves a worker and (where requested) heavy capacity until completed or safely
released. SQLite transactions serialize selectors across controller processes.
"""
from .worker_capacity import reusable
import copy
import math
import uuid

from .handoff import nonempty, require, Rejected, validate_review

ROLES = {'implementation', 'review', 'repair', 'integration', 'qa'}
PRIORITY = {'repair': 0, 'review': 1, 'integration': 2, 'qa': 3, 'implementation': 4}
OPEN = {'assigned', 'dispatched'}
WORK_CLASSES = {'existing': 0, 'expansion': 1}
FOCUS = {'enemy_acceptance': 0, 'existing_content': 1, 'expansion': 2}


def job_priority(job):
    """Finish actionable existing slices before new content, then use role/FIFO."""
    return (WORK_CLASSES[job.get('work_class', 'existing')],
            FOCUS[job.get('focus', 'existing_content')], PRIORITY[job['role']],
            job.get('queued_at', 0), job['id'])


def pending_heavy_lanes(state, pool, process_probe=None):
    """Execution reservations only; real build leases are always counted separately.

    A stopped terminal-for-build slice retains its worker/assignment ownership,
    but must not reserve scarce build capacity while awaiting another producer.
    Unknown execution or protected children remain conservative reservations.
    """
    if process_probe is None:
        from .processes import probe
        process_probe = probe
    pending = set()
    for assignment in pool.get('assignments', {}).values():
        if not assignment.get('heavy') or assignment.get('status') not in OPEN:
            continue
        key = assignment['lane']
        lane = state.get('lanes', {}).get(key, {})
        stopped_terminal = (lane.get('state') in ('blocked', 'review_ready', 'handoff_ready', 'done') and
            process_probe(lane.get('process', {})) == 'dead' and
            all(process_probe(lease.get('process', {})) == 'dead' for lease in state.get('leases', {}).values()
                if lease.get('lane') == key))
        if not stopped_terminal:
            pending.add(key)
    return pending


class SchedulingMixin:
    def integration_assistance(self, state, lane, role):
        """Registered advisory helpers do not require an available integration writer."""
        return (role == 'review' and lane.get('target_level') == 'planning-only'
                and lane.get('lane', '').startswith(('integration-support-', 'planning-', 'publication-review-'))
                and any(i.get('lane') == lane['lane'] and i.get('planner_helper')
                        for i in state.get('throughput_runtime', {}).get('autofill', {}).get('items', {}).values()))

    def integration_owner_available(self, state, owner):
        """A verified parked owner retains authority between integration turns."""
        if owner['state'] == 'done':
            return False
        if self.probe(owner['process']) == 'alive':
            return True
        if owner['state'] != 'review_ready' or not self.recovery_safe(state, owner):
            return False
        if not any(s.get('owner_lane') == owner['lane'] for s in state.get('throughput', {}).get('workstreams', {}).values()):
            return False
        if any(b.get('integrator') == owner['lane'] and b.get('state') == 'claimed'
               for b in state.get('throughput', {}).get('batches', {}).values()):
            return False
        try:
            validate_review(self.root, owner.get('review'), owner)
        except (Rejected, OSError, ValueError, TypeError, KeyError):
            return False
        return True

    @staticmethod
    def scheduling(state):
        data = state.setdefault('throughput', {})
        for key in ('workstreams', 'workers', 'jobs', 'assignments'):
            data.setdefault(key, {})
        return data

    def scheduling_status(self):
        return self.scheduling(self.snapshot())

    def set_workstream(self, name, owner_lane, lanes=None):
        require(nonempty(name), 'Workstream name required')
        with self.transaction() as state:
            data = self.scheduling(state)
            lane = self.lane(state, owner_lane)
            old = data['workstreams'].get(name)
            members = (old or {}).get('lanes', []) if lanes is None else lanes
            require(isinstance(members, list) and all(nonempty(k) for k in members), 'Explicit lane membership required')
            for key in members:
                self.lane(state, key)
            if old and old['owner_lane'] == owner_lane:
                old['lanes'] = sorted(set(members))
                return old
            if old:
                previous = self.lane(state, old['owner_lane'])
                require(self.probe(previous['process']) == 'dead',
                        'Existing integration owner is live or unknown; reconcile explicitly')
            require(lane['state'] != 'done' and self.probe(lane['process']) == 'alive',
                    'Integration owner must be explicitly confirmed alive')
            record = dict(name=name, owner_lane=owner_lane, owner=lane['owner'],
                          issue=lane['issue'], lanes=sorted(set(members)), registered_at=self.clock())
            data['workstreams'][name] = record
            self.event(state, 'workstream_owned', owner_lane, workstream=name)
            return record

    def register_pool_worker(self, worker_id, roles, capabilities, authorized_by):
        require(nonempty(worker_id) and nonempty(authorized_by), 'Worker and authorization required')
        require(isinstance(roles, list) and roles and set(roles) <= ROLES, 'Explicit known roles required')
        require(isinstance(capabilities, list) and all(nonempty(c) for c in capabilities),
                'Capabilities must be explicit strings')
        record = dict(worker_id=worker_id, roles=sorted(set(roles)),
                      capabilities=sorted(set(capabilities)), authorized_by=authorized_by)
        with self.transaction() as state:
            data = self.scheduling(state)
            require(any(l['worker_id'] == worker_id for l in state['lanes'].values()),
                    'Worker must own a registered lane')
            old = data['workers'].get(worker_id)
            require(old is None or old == record or not any(
                a['worker_id'] == worker_id and a['status'] in OPEN for a in data['assignments'].values()),
                'Cannot change authorizations during an assignment')
            data['workers'][worker_id] = record
            return record

    def reassign_pool_worker(self, worker_id, roles, capabilities, authorized_by, reason):
        """Change an idle worker's role/capability contract in place.

        Reassignment is explicit and fenced: the worker must already be
        registered, own a live lane, and have no open assignment. This lets an
        operator promote idle capacity without manufacturing a duplicate
        worker identity or stealing an active job.
        """
        require(nonempty(reason), 'Reassignment reason required')
        with self.transaction() as state:
            data = self.scheduling(state)
            old = data['workers'].get(worker_id)
            require(old is not None, 'Unknown pool worker')
            require(not any(a['worker_id'] == worker_id and a['status'] in OPEN
                            for a in data['assignments'].values()),
                    'Cannot reassign worker with an open assignment')
            lane = next((l for l in state['lanes'].values() if l['worker_id'] == worker_id), None)
            require(lane is not None, 'Worker lane is not registered')
            require(lane['state'] != 'done' and self.probe(lane['process']) == 'alive',
                    'Worker lane must be live for reassignment')
            record = dict(worker_id=worker_id, roles=sorted(set(roles)),
                          capabilities=sorted(set(capabilities)), authorized_by=authorized_by)
            require(record['roles'] and set(record['roles']) <= ROLES, 'Explicit known roles required')
            require(all(nonempty(c) for c in record['capabilities']), 'Explicit capability strings required')
            data['workers'][worker_id] = record
            self.event(state, 'pool_worker_reassigned', lane['lane'], worker_id=worker_id,
                       reason=reason, roles=record['roles'], capabilities=record['capabilities'])
            return record

    def enqueue_job(self, record):
        record = copy.deepcopy(record)
        for key in ('id', 'lane', 'workstream', 'role', 'instruction'):
            require(nonempty(record.get(key)), key + ' required')
        require(type(record.get('issue')) is int and record['issue'] > 0, 'Issue-backed scope required')
        require(record['role'] in ROLES, 'Unknown job role')
        record.setdefault('capabilities', [])
        record.setdefault('heavy', False)
        record.setdefault('work_class', 'existing')
        if 'focus' in record:
            require(isinstance(record['focus'], str) and record['focus'] in FOCUS, 'Unknown job focus')
            require((record['focus'] == 'expansion') == (record['work_class'] == 'expansion'), 'Focus/work class mismatch')
        require(isinstance(record['work_class'], str) and record['work_class'] in WORK_CLASSES, 'work_class must be existing or expansion')
        require(type(record['heavy']) is bool, 'heavy must be boolean')
        require(isinstance(record['capabilities'], list) and all(nonempty(c) for c in record['capabilities']),
                'Capabilities must be strings')
        require(set(record) <= {'id', 'lane', 'issue', 'workstream', 'role', 'instruction', 'capabilities', 'heavy', 'work_class', 'focus'},
                'Unknown job fields')
        with self.transaction() as state:
            data = self.scheduling(state)
            old = data['jobs'].get(record['id'])
            if old:
                require(all(old.get(k, 'existing' if k == 'work_class' else None) == v for k, v in record.items()), 'Job ID already has different scope')
                return old
            lane = self.lane(state, record['lane'])
            require(lane['issue'] == record['issue'], 'Job must match registered issue scope')
            require(lane['task_id'].startswith('opencode:') and len(lane['task_id']) > 9,
                    'Pre-registered resumable session required')
            require(lane['state'] in ('ready', 'running', 'blocked', 'reconciling'), 'Lane cannot resume')
            require(record['workstream'] in data['workstreams'], 'Named integration owner required')
            worker = data['workers'].get(lane['worker_id'])
            require(worker is not None and record['role'] in worker['roles'] and
                    set(record['capabilities']) <= set(worker['capabilities']), 'Worker lacks job authorization')
            require(not any(j['lane'] == lane['lane'] and j['status'] != 'completed'
                            for j in data['jobs'].values()), 'Lane already has queued work')
            record.update(worker_id=lane['worker_id'], generation=lane['generation'],
                          status='queued', queued_at=self.clock())
            data['jobs'][record['id']] = record
            self.event(state, 'job_queued', lane['lane'], job=record['id'])
            return record

    def assign_job(self, worker_id, ram_percent):
        require(type(ram_percent) in (int, float) and math.isfinite(ram_percent) and 0 <= ram_percent <= 100,
                'Fresh measured RAM percentage required')
        with self.transaction() as state:
            data = self.scheduling(state)
            worker = data['workers'].get(worker_id)
            require(worker is not None, 'Worker is not authorized for pool work')
            existing = next((a for a in data['assignments'].values()
                             if a['worker_id'] == worker_id and a['status'] in OPEN), None)
            if existing:
                return existing
            if ram_percent >= state['settings'].get('ram_ceiling_percent', 90):
                return None
            jobs = sorted(data['jobs'].values(), key=job_priority)
            for job in jobs:
                if job['status'] != 'queued' or job['worker_id'] != worker_id:
                    continue
                if job['role'] not in worker['roles'] or not set(job['capabilities']) <= set(worker['capabilities']):
                    continue
                lane = self.lane(state, job['lane'])
                owner = self.lane(state, data['workstreams'][job['workstream']]['owner_lane'])
                if not (self.integration_assistance(state, lane, job['role']) or self.integration_owner_available(state, owner)):
                    continue
                if lane['generation'] != job['generation'] or lane['worker_id'] != worker_id:
                    continue
                if lane['state'] not in ('ready', 'running', 'blocked', 'reconciling') or not self.recovery_safe(state, lane):
                    continue
                if lane.get('dependencies'):
                    continue  # Dependency controller must consume an explicit ready version.
                if any(l['lane'] != lane['lane'] and l['worker_id'] == worker_id and
                       l['state'] in ('ready', 'running', 'waiting_resource', 'blocked', 'reconciling') and not reusable(self, state, l)
                       for l in state['lanes'].values()):
                    continue
                launches = state.get('control', {}).get('launches', {})
                if any(l['lane'] == lane['lane'] and l['status'] in ('intent', 'spawned', 'running') for l in launches.values()):
                    continue
                # Count each assigned lane once even after it acquires its build lease.
                if job['heavy'] and not state.get('build_capacity', {}).get('lease_only'):
                    heavy_leases = [v for r, v in state['leases'].items() if self.heavy(r)]
                    heavy_lanes = {v['lane'] for v in heavy_leases}
                    pending = pending_heavy_lanes(state, data, self.probe)
                    pending.difference_update(heavy_lanes)
                    if lane['lane'] not in heavy_lanes and len(heavy_leases) + len(pending) >= state['settings']['max_heavy_builds']:
                        continue
                item = dict(id=uuid.uuid4().hex, job=job['id'], lane=lane['lane'], worker_id=worker_id,
                            generation=lane['generation'], revision=lane['revision'], instruction=job['instruction'],
                            heavy=job['heavy'], status='assigned', assigned_at=self.clock(), launch_id=None)
                data['assignments'][item['id']] = item
                job.update(status='assigned', assignment=item['id'])
                self.event(state, 'job_assigned', lane['lane'], job=job['id'], assignment=item['id'])
                return item
            return None

    def bind_assignment_launch(self, assignment_id, launch_id):
        with self.transaction() as state:
            item = self.scheduling(state)['assignments'][assignment_id]
            if item['launch_id']:
                require(item['launch_id'] == launch_id, 'Assignment already bound')
                return item
            require(item['status'] == 'assigned', 'Assignment is no longer dispatchable')
            launch = state.get('control', {}).get('launches', {}).get(launch_id)
            require(launch is not None and launch['lane'] == item['lane'] and
                    launch['generation'] == item['generation'], 'Launch must match assigned lane and generation')
            item.update(launch_id=launch_id, status='dispatched')
            return item

    def complete_assignment(self, assignment_id, evidence):
        self.evidence(evidence)
        with self.transaction() as state:
            data = self.scheduling(state)
            item = data['assignments'][assignment_id]
            if item['status'] == 'completed':
                require(item['evidence'] == evidence, 'Conflicting completion evidence')
                return item
            require(item['status'] == 'dispatched', 'Assignment must have a recorded dispatch')
            launch = state.get('control', {}).get('launches', {}).get(item['launch_id'], {})
            lane = self.lane(state, item['lane'])
            require(launch.get('bound_generation') == lane['generation'], 'Completion belongs to another execution')
            require(lane['state'] == 'done' and (lane.get('integration') or lane.get('review_disposition')),
                    'Finish includes applied disposition and verified integration receipt')
            require(self.recovery_safe(state, lane), 'Worker or protected child remains live/unknown')
            item.update(status='completed', completed_at=self.clock(), evidence=copy.deepcopy(evidence))
            data['jobs'][item['job']]['status'] = 'completed'
            self.event(state, 'job_completed', lane['lane'], job=item['job'])
            return item

    def release_assignment(self, assignment_id, reason):
        require(nonempty(reason), 'Release reason required')
        with self.transaction() as state:
            data = self.scheduling(state)
            item = data['assignments'][assignment_id]
            if item['status'] == 'released':
                return item
            require(item['status'] == 'assigned' and item['launch_id'] is None,
                    'Dispatched assignments require outcome reconciliation')
            lane = self.lane(state, item['lane'], item['generation'])
            require(self.recovery_safe(state, lane), 'Lane is live or unknown')
            require(not any(l['lane'] == lane['lane'] and l['status'] in ('intent', 'spawned', 'running')
                            for l in state.get('control', {}).get('launches', {}).values()), 'Launch already in flight')
            item.update(status='released', reason=reason)
            data['jobs'][item['job']].update(status='queued', assignment=None)
            return item

    def supersede_planning_assignment(self, assignment_id, stopped_child):
        """Retire an interrupted old planning cycle without accepting its output."""
        with self.transaction() as state:
            data = self.scheduling(state)
            item = data['assignments'][assignment_id]
            if item['status'] == 'superseded':
                return item
            lane = self.lane(state, item['lane'])
            prefix, separator, cycle = lane['lane'].rpartition('-cycle-')
            require(separator and cycle.isdigit() and prefix.startswith('planning-shard-'), 'Partition planner required')
            require(item['status'] == 'dispatched' and lane['state'] == 'done' and
                    lane.get('target_level') == 'planning-only' and not lane.get('integration') and
                    not lane.get('review_disposition') and (lane.get('outcome') or {}).get('outcome') == 'reconcile',
                    'Only interrupted unaccepted planning completion can be superseded')
            require(data['jobs'][item['job']]['role'] == 'review', 'Planning review assignment required')
            require(self.recovery_safe(state, lane) and self.probe(stopped_child) == 'dead',
                    'Planner or protected child remains live/unknown')
            launches = state.get('control', {}).get('launches', {})
            launch = launches.get(item['launch_id'], {})
            require(launch.get('status') == 'exited' and launch.get('bound_generation') == lane['generation'] and
                    self.probe(launch.get('process')) == 'dead', 'Original launch must be confirmed exited')
            require(not any(x['lane'] == lane['lane'] and x['status'] in ('intent', 'spawned', 'running', 'exiting')
                            for x in launches.values()), 'Planning dispatch still in flight')
            require(not any(v['lane'] == lane['lane'] for v in state.get('planning_claims', {}).values()),
                    'Planning claims require coordinator disposition')
            successors = []
            for candidate in state['lanes'].values():
                other_prefix, _, other_cycle = candidate['lane'].rpartition('-cycle-')
                if other_prefix != prefix or not other_cycle.isdigit() or int(other_cycle) <= int(cycle):
                    continue
                if candidate['state'] != 'done' or not candidate.get('review_disposition'):
                    continue
                if all(candidate.get(k) == lane.get(k) for k in ('issue', 'scope', 'owned_files', 'target_level')):
                    successors.append((int(other_cycle), candidate))
            require(successors, 'Accepted same-scope successor required')
            successor = max(successors, key=lambda pair: pair[0])[1]
            disposition = successor['review_disposition']
            proof = self.archive_evidence(disposition.get('archived_evidence') or disposition['evidence'])
            record = dict(successor=successor['lane'], evidence=proof, previous_outcome=lane['outcome'],
                          summary='Interrupted planning attempt superseded by reviewed later cycle; no output accepted')
            lane['superseded_planning'] = record
            lane['outcome'] = dict(outcome='superseded', summary=record['summary'], evidence=proof)
            item.update(status='superseded', superseded_at=self.clock(), supersession=record)
            data['jobs'][item['job']]['status'] = 'superseded'
            self.event(state, 'planning_assignment_superseded', lane['lane'], successor=successor['lane'])
            return item

    def validate_assignment(self, assignment_id, ram_percent):
        """Read-only preflight; plan_assignment also performs it under the launch lock."""
        with self.transaction() as state:
            return self._validate_assignment(state, assignment_id, ram_percent)

    def _validate_assignment(self, state, assignment_id, ram_percent):
        ceiling = state['settings'].get('ram_ceiling_percent', 90)
        require(type(ram_percent) in (int, float) and math.isfinite(ram_percent) and 0 <= ram_percent < ceiling,
                f'Fresh RAM measurement must be below {ceiling} percent')
        data = self.scheduling(state)
        item = data['assignments'][assignment_id]
        require(item['status'] == 'assigned', 'Assignment is no longer awaiting dispatch')
        lane = self.lane(state, item['lane'], item['generation'], item['revision'])
        job = data['jobs'][item['job']]
        worker = data['workers'][item['worker_id']]
        require(lane['worker_id'] == item['worker_id'] and job['assignment'] == item['id'], 'Assignment superseded')
        require(job['role'] in worker['roles'] and set(job['capabilities']) <= set(worker['capabilities']),
                'Worker authorization changed')
        owner = self.lane(state, data['workstreams'][job['workstream']]['owner_lane'])
        require(self.integration_assistance(state, lane, job['role']) or
                self.integration_owner_available(state, owner), 'Integration owner is unavailable')
        require(lane['state'] in ('ready', 'running', 'blocked', 'reconciling') and not lane.get('dependencies'),
                'Lane state or dependency changed')
        require(self.recovery_safe(state, lane), 'Lane or protected child is live/unknown')
        self.check_wip(state, lane)
        if item['heavy'] and not state.get('build_capacity', {}).get('lease_only'):
            leases = [v for r, v in state['leases'].items() if self.heavy(r)]
            pending = pending_heavy_lanes(state, data, self.probe)
            pending.add(lane['lane'])  # This validation intends to resume heavy work.
            pending.difference_update(v['lane'] for v in leases)
            require(len(leases) + len(pending) <= state['settings']['max_heavy_builds'], 'Heavy-build capacity exhausted')
        return item

    def plan_assignment(self, assignment_id, models, ram_percent):
        """Atomic validation + existing controller launch-intent schema, never spawn."""
        from .control import fingerprint
        from .provenance import stamp
        require(models and all(nonempty(m) and '/' in m for m in models), 'Provider/model chain required')
        code = stamp()
        with self.transaction() as state:
            data = self.scheduling(state)
            item = data['assignments'][assignment_id]
            if item['launch_id']:
                return state['control']['launches'][item['launch_id']]
            self._validate_assignment(state, assignment_id, ram_percent)
            c = self.control(state)
            require(not any(l['lane'] == item['lane'] and l['status'] in ('intent', 'spawned', 'running')
                            for l in c['launches'].values()), 'Dispatch already in flight')
            lane = self.lane(state, item['lane'])
            require(lane['task_id'].startswith('opencode:') and len(lane['task_id']) > 9,
                    'Known OpenCode session required')
            identity = fingerprint(['pool', item['id'], item['generation']])
            launch = dict(id=identity, lane=lane['lane'], generation=lane['generation'],
                          reason='pool:' + item['id'], instruction=item['instruction'], models=models,
                          model_index=0, version=None, session=lane['task_id'].removeprefix('opencode:'),
                          status='intent', process=None, created_at=self.clock(), attempts=0,
                          work_class=data['jobs'][item['job']].get('work_class', 'existing'),
                          focus=data['jobs'][item['job']].get('focus', 'existing_content'), code_revision=code)
            c['launches'][identity] = launch
            item.update(launch_id=identity, status='dispatched')
            self.event(state, 'launch_intent', lane['lane'], action=identity)
            return launch


    def provision_pool_lane(self, record, previous_lane):
        """Register a new explicit slice using a stopped worker's historical identity.

        Unlike register(), this does not claim an already-live runner. Controller
        bind_launch later records the actual new runner and increments generation.
        """
        import re
        from pathlib import Path, PurePosixPath
        from .handoff import GATES, source_record
        from .remote import check_remote_ownership
        record = copy.deepcopy(record)
        required = {'lane', 'issue', 'owner', 'scope', 'target_level', 'next_action',
                    'milestone', 'owned_files', 'acceptance', 'root', 'native'}
        require(required <= set(record) <= required | {'closes_gates'},
                'Explicit slice fields required; process and session are inherited, never supplied')
        for key in ('lane', 'owner', 'scope', 'target_level', 'next_action', 'milestone'):
            require(nonempty(record[key]), key + ' required')
        require(re.fullmatch(r'[a-z0-9][a-z0-9_-]*', record['lane']), 'Use a stable lowercase lane ID')
        require(type(record['issue']) is int and record['issue'] > 0, 'Issue required before claim')
        for key in ('owned_files', 'acceptance'):
            require(isinstance(record[key], list) and record[key] and all(nonempty(v) for v in record[key]),
                    key + ' required')
        require(len(set(record['owned_files'])) == len(record['owned_files']), 'Duplicate owned file')
        for name in record['owned_files']:
            require(not Path(name).is_absolute() and '..' not in Path(name).parts and '\\' not in name and
                    ':' not in name and str(PurePosixPath(name)) == name, 'Owned files use normalized relative paths')
        record.setdefault('closes_gates', [])
        require(isinstance(record['closes_gates'], list) and all(g in GATES for g in record['closes_gates']),
                'Unknown intended acceptance gate')
        source_record(record['root'], 'root')
        if record['native'] is not None:
            source_record(record['native'], 'native')
        with self.transaction() as state:
            data = self.scheduling(state)
            previous = self.lane(state, previous_lane)
            require(reusable(self, state, previous) or (previous['state'] == 'done' and (previous.get('integration') or previous.get('review_disposition') or previous.get('cancelled_before_start') or previous.get('superseded_planning'))),
                    'Previous slice must have an applied disposition')
            require(previous['owner'] == record['owner'], 'Pool provisioning cannot change implementation owner')
            require(previous['worker_id'] in data['workers'], 'Worker is not authorized for pool reuse')
            require(self.recovery_safe(state, previous), 'Previous worker or protected child is live/unknown')
            require(previous['task_id'].startswith('opencode:') and len(previous['task_id']) > 9,
                    'Previous worker has no known resumable session')
            require(not any(a['worker_id'] == previous['worker_id'] and a['status'] in OPEN
                            for a in data['assignments'].values()), 'Previous assignment remains open')
            require(not any(l['lane'] == previous_lane and l['status'] in ('intent', 'spawned', 'running')
                            for l in state.get('control', {}).get('launches', {}).values()), 'Previous launch remains in flight')
            require(record['lane'] not in state['lanes'], 'Lane ID already registered')
            check_remote_ownership(state, record['issue'], record['owned_files'])
            for other in state['lanes'].values():
                if other['state'] != 'done':
                    require(other['issue'] != record['issue'], 'Issue already has unfinished lane')
                    require(not ({f.casefold() for f in other['owned_files']} &
                                 {f.casefold() for f in record['owned_files']}), 'Owned files overlap another lane')
            record.update(worker_id=previous['worker_id'], task_id=previous['task_id'],
                          process=copy.deepcopy(previous['process']), state='ready', generation=1, revision=1,
                          dependencies=[], created_at=self.clock(), started_at=None, heartbeat_at=self.clock(),
                          progress_at=self.clock(), progress_detail='Explicit pool slice awaiting dispatch',
                          handoff_at=None, progress_evidence=None, failure_streak=0, recovery_count=0,
                          failure_fingerprint=None, handoff=None, integrated_at=None, previous_lane=previous_lane)
            self.check_wip(state, record)
            state['lanes'][record['lane']] = record
            self.event(state, 'pool_lane_provisioned', record['lane'], previous_lane=previous_lane)
            return record
