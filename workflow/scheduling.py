"""Issue-backed reusable worker scheduling; dispatch stays in the controller.

Queue records never transfer lane ownership or manufacture sessions. An assignment
reserves a worker and (where requested) heavy capacity until completed or safely
released. SQLite transactions serialize selectors across controller processes.
"""
import copy
import math
import uuid

from .handoff import nonempty, require

ROLES = {'implementation', 'review', 'repair', 'integration', 'qa'}
PRIORITY = {'repair': 0, 'review': 1, 'integration': 2, 'qa': 3, 'implementation': 4}
OPEN = {'assigned', 'dispatched'}


class SchedulingMixin:
    @staticmethod
    def scheduling(state):
        data = state.setdefault('throughput', {})
        for key in ('workstreams', 'workers', 'jobs', 'assignments'):
            data.setdefault(key, {})
        return data

    def scheduling_status(self):
        with self.transaction() as state:
            return copy.deepcopy(self.scheduling(state))

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

    def enqueue_job(self, record):
        record = copy.deepcopy(record)
        for key in ('id', 'lane', 'workstream', 'role', 'instruction'):
            require(nonempty(record.get(key)), key + ' required')
        require(type(record.get('issue')) is int and record['issue'] > 0, 'Issue-backed scope required')
        require(record['role'] in ROLES, 'Unknown job role')
        record.setdefault('capabilities', [])
        record.setdefault('heavy', False)
        require(type(record['heavy']) is bool, 'heavy must be boolean')
        require(isinstance(record['capabilities'], list) and all(nonempty(c) for c in record['capabilities']),
                'Capabilities must be strings')
        require(set(record) <= {'id', 'lane', 'issue', 'workstream', 'role', 'instruction', 'capabilities', 'heavy'},
                'Unknown job fields')
        with self.transaction() as state:
            data = self.scheduling(state)
            old = data['jobs'].get(record['id'])
            if old:
                require(all(old[k] == v for k, v in record.items()), 'Job ID already has different scope')
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
            if ram_percent >= 90:
                return None
            jobs = sorted(data['jobs'].values(), key=lambda j: (PRIORITY[j['role']], j['queued_at'], j['id']))
            for job in jobs:
                if job['status'] != 'queued' or job['worker_id'] != worker_id:
                    continue
                if job['role'] not in worker['roles'] or not set(job['capabilities']) <= set(worker['capabilities']):
                    continue
                lane = self.lane(state, job['lane'])
                owner = self.lane(state, data['workstreams'][job['workstream']]['owner_lane'])
                if owner['state'] == 'done' or self.probe(owner['process']) != 'alive':
                    continue
                if lane['generation'] != job['generation'] or lane['worker_id'] != worker_id:
                    continue
                if lane['state'] not in ('ready', 'running', 'blocked', 'reconciling') or not self.recovery_safe(state, lane):
                    continue
                if lane.get('dependencies'):
                    continue  # Dependency controller must consume an explicit ready version.
                if any(l['lane'] != lane['lane'] and l['worker_id'] == worker_id and
                       l['state'] in ('ready', 'running', 'waiting_resource', 'blocked', 'reconciling')
                       for l in state['lanes'].values()):
                    continue
                launches = state.get('control', {}).get('launches', {})
                if any(l['lane'] == lane['lane'] and l['status'] in ('intent', 'spawned', 'running') for l in launches.values()):
                    continue
                # Count each assigned lane once even after it acquires its build lease.
                heavy_leases = [v for r, v in state['leases'].items() if self.heavy(r)]
                heavy_lanes = {v['lane'] for v in heavy_leases}
                pending = {a['lane'] for a in data['assignments'].values() if a['status'] in OPEN and a['heavy']}
                pending.difference_update(heavy_lanes)
                if job['heavy'] and lane['lane'] not in heavy_lanes and len(heavy_leases) + len(pending) >= state['settings']['max_heavy_builds']:
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

    def validate_assignment(self, assignment_id, ram_percent):
        """Read-only preflight; plan_assignment also performs it under the launch lock."""
        with self.transaction() as state:
            return self._validate_assignment(state, assignment_id, ram_percent)

    def _validate_assignment(self, state, assignment_id, ram_percent):
        require(type(ram_percent) in (int, float) and math.isfinite(ram_percent) and 0 <= ram_percent < 90,
                'Fresh RAM measurement must be below 90 percent')
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
        require(owner['state'] != 'done' and self.probe(owner['process']) == 'alive', 'Integration owner is unavailable')
        require(lane['state'] in ('ready', 'running', 'blocked', 'reconciling') and not lane.get('dependencies'),
                'Lane state or dependency changed')
        require(self.recovery_safe(state, lane), 'Lane or protected child is live/unknown')
        self.check_wip(state, lane)
        if item['heavy']:
            leases = [v for r, v in state['leases'].items() if self.heavy(r)]
            pending = {a['lane'] for a in data['assignments'].values() if a['status'] in OPEN and a['heavy']}
            pending.difference_update(v['lane'] for v in leases)
            require(len(leases) + len(pending) <= state['settings']['max_heavy_builds'], 'Heavy-build capacity exhausted')
        return item

    def plan_assignment(self, assignment_id, models, ram_percent):
        """Atomic validation + existing controller launch-intent schema, never spawn."""
        from .control import fingerprint
        require(models and all(nonempty(m) and '/' in m for m in models), 'Provider/model chain required')
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
                          status='intent', process=None, created_at=self.clock(), attempts=0)
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
            require(previous['state'] == 'done' and (previous.get('integration') or previous.get('review_disposition')),
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
