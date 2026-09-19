"""Immutable delivery bundles and provisional QA; never gameplay admission."""
import copy
import hashlib
import json

from .handoff import digest, local_path, nonempty, require, validate_handoff


def pin(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class DeliveryMixin:
    def delivery(self, state):
        value = state.setdefault('throughput', {})
        for key in ('snapshots', 'dispositions', 'candidates', 'qa'):
            value.setdefault(key, {})
        return value

    def _delivery_stopped(self, state, lane, candidate_pin=None):
        require(self.probe(lane['process']) == 'dead', 'Recorded worker is not confirmed stopped')
        for collection in ('leases', 'queue'):
            for item in state[collection].values():
                if item['lane'] == lane['lane'] and item['generation'] == lane['generation']:
                    require(self.probe(item['process']) == 'dead', 'Live/uninspectable resource owner')
        require(not any(item['lane'] == lane['lane'] and item['generation'] == lane['generation']
                        and item['status'] in ('intent', 'spawned', 'running')
                        and not (candidate_pin and item['status'] == 'intent' and item.get('reason') == 'candidate_qa:' + candidate_pin and item.get('version') == candidate_pin)
                        for item in state.get('control', {}).get('launches', {}).values()),
                'Controller dispatch in flight')

    def _delivery_validate(self, record, lane=None):
        path = self.evidence(record['handoff'])
        for item in record['files']:
            self.evidence(item)
        data = json.loads(path.read_text(encoding='utf-8'))
        result = validate_handoff(self.root, data, lane)
        require(data['kind'] != 'review' and result['slice_passed'], 'Passing implementation handoff required')
        return data, result

    def _delivery_read_handoff(self, lane):
        path = self.evidence(lane['handoff'])
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == lane['handoff']['sha256'],
                'Handoff changed during snapshot')
        data = json.loads(payload.decode('utf-8'))
        result = validate_handoff(self.root, data, lane)
        require(data['kind'] != 'review' and result['slice_passed'], 'Passing implementation handoff required')
        return data

    def _delivery_freeze(self, lane, data):
        """Content-addressed copies. Existing bytes are checked, never overwritten."""
        original_hash = pin(data)
        directory = self.root / 'output/workflow/delivery' / original_hash
        directory.mkdir(parents=True, exist_ok=True)
        files = []

        def write(name, payload):
            path = directory / name
            expected = hashlib.sha256(payload).hexdigest()
            try:
                with path.open('xb') as stream:
                    stream.write(payload)
            except FileExistsError:
                require(digest(path) == expected, 'Immutable snapshot bytes changed')
            item = dict(path=str(path), sha256=expected)
            files.append(item)
            return item

        frozen = copy.deepcopy(data)
        for index, (name, item) in enumerate(data['evidence'].items()):
            source = self.evidence(item)
            payload = source.read_bytes()
            require(hashlib.sha256(payload).hexdigest() == item['sha256'], 'Evidence changed during snapshot')
            frozen['evidence'][name] = write(f'evidence-{index}{source.suffix}', payload)
        build = frozen.get('build', {})
        if build is None:
            build = {}  # Valid tooling handoffs may explicitly omit a build.
        if build.get('replacement_main'):
            # Preserve original certificate bytes and explicitly derive a relocation
            # certificate for the identical executable bytes in the frozen bundle.
            name = build['provenance']
            provenance = json.loads(self.evidence(data['evidence'][name]).read_text(encoding='utf-8'))
            exe = frozen['evidence'][build['executable']]
            provenance['artifacts'][exe['path']] = {'sha256': exe['sha256']}
            provenance['snapshot_origin'] = data['evidence'][name]
            frozen['evidence'][name] = write('relocated-provenance.json', json.dumps(provenance, sort_keys=True).encode())
        handoff = write('handoff.json', json.dumps(frozen, sort_keys=True).encode())
        record = dict(handoff=handoff, files=files, original_sha256=original_hash,
                      root=frozen['root'], native=frozen.get('native'), build=build,
                      evidence=frozen['evidence'])
        self._delivery_validate(record, lane)
        return record

    def snapshot_handoff(self, key, generation, revision, version):
        require(nonempty(version), 'Snapshot version required')
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            snapshots = self.delivery(state)['snapshots']
            identity = pin([key, generation, version])
            old = snapshots.get(identity)
            if old:
                self._delivery_validate(old, lane)
                require(lane['handoff']['sha256'] == old['submitted_sha256'], 'Version source changed')
                return old
            self.check_handoff(lane)
            data = self._delivery_read_handoff(lane)
            record = self._delivery_freeze(lane, data)
            record.update(lane=key, generation=generation, version=version,
                          submitted_sha256=lane['handoff']['sha256'], created_at=self.clock())
            snapshots[identity] = record
            self.event(state, 'handoff_snapshot', key, version=version)
            return record

    def dispose_review(self, key, generation, revision, version, handoff_sha256,
                       file, status, reviewer, evidence):
        require(status in ('approved', 'rejected') and nonempty(reviewer) and nonempty(version),
                'Version, reviewer and explicit review disposition required')
        self.evidence(evidence)
        request = dict(file=file, status=status, reviewer=reviewer, evidence=evidence,
                       handoff_sha256=handoff_sha256)
        from .provenance import stamp
        stamp()  # Warm the per-process revision before taking the writer lock.
        with self.transaction() as state:
            return self._dispose_review(state, key, generation, revision, version, request)

    def _dispose_review(self, state, key, generation, revision, version, request):
        file, status, reviewer, evidence, handoff_sha256 = (request[k] for k in
            ("file", "status", "reviewer", "evidence", "handoff_sha256"))
        lane = self.lane(state, key, generation)
        dispositions = self.delivery(state)['dispositions']
        identity = pin([key, generation, version])
        old = dispositions.get(identity)
        if old:
            require(old['request'] == request, 'Conflicting disposition replay')
            self._delivery_validate(old['snapshot'], lane)
            require(lane['handoff']['sha256'] == old['snapshot']['handoff']['sha256'], 'Disposition superseded')
            return old
        self.lane(state, key, generation, revision)
        self._delivery_stopped(state, lane)
        require(lane['state'] in ('running', 'handoff_ready', 'integrating'), 'Resume/reconcile lane before disposition')
        self.check_handoff(lane)
        require(lane['handoff']['sha256'] == handoff_sha256, 'Review source hash changed')
        data = self._delivery_read_handoff(lane)
        matches = [r for r in data['shared_reviews'] if r['file'] == file]
        require(len(matches) == 1, 'Expected exactly one shared review for file')
        evidence_key = 'disposition_' + pin(request)
        data['evidence'][evidence_key] = evidence
        matches[0].update(status=status, reviewer=reviewer,
                          evidence=matches[0]['evidence'] + [evidence_key])
        snapshot = self._delivery_freeze(lane, data)
        _, result = self._delivery_validate(snapshot, lane)
        lane.update(state='handoff_ready', revision=revision + 1,
                    handoff_at=lane['handoff_at'] or self.clock(), progress_at=self.clock(),
                    handoff=dict(**snapshot['handoff'], result=result))
        self.check_wip(state, lane)
        from .provenance import stamp
        record = dict(request=request, snapshot=snapshot, revision=lane['revision'], at=self.clock(),
                      code_revision=stamp())
        dispositions[identity] = record
        self.event(state, 'shared_review_applied', key, file=file, status=status, version=version)
        return record

    def publish_candidate(self, key, generation, revision, version):
        require(nonempty(version), 'Candidate version required')
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            candidates = self.delivery(state)['candidates']
            identity = pin([key, generation, version])
            old = candidates.get(identity)
            if old:
                self._delivery_validate(old['snapshot'], lane)
                require(lane['handoff']['sha256'] == old['submitted_sha256'], 'Candidate version source changed')
                return old
            self.check_handoff(lane)
            data = self._delivery_read_handoff(lane)
            require(data.get('kind') == 'runtime', 'Candidate requires pinned native build and executable')
            snapshot = self._delivery_freeze(lane, data)
            for item in candidates.values():
                if item['producer'] == key:
                    item['current'] = False
            record = dict(producer=key, generation=generation, version=version, snapshot=snapshot,
                          pin=pin([identity, snapshot['handoff']]), current=True, provisional=True,
                          gameplay_accepted=False, integrated=False, created_at=self.clock(),
                          submitted_sha256=lane['handoff']['sha256'])
            candidates[identity] = record
            for subscription in self.delivery(state)['qa'].values():
                if subscription['producer'] == key:
                    for attempt in subscription['attempts'].values():
                        attempt['valid'] = False
            self.event(state, 'candidate_published', key, pin=record['pin'], version=version)
            return record

    def subscribe_candidate_qa(self, key, generation, revision, producer, session_id):
        require(nonempty(session_id) and key != producer, 'Distinct QA lane and session required')
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            self.lane(state, producer)
            require(lane['state'] != 'done', 'QA lane is completed')
            require(lane['task_id'] == 'opencode:' + session_id, 'QA session must match registered task')
            qa = self.delivery(state)['qa']
            request = dict(lane=key, generation=generation, producer=producer, session_id=session_id,
                           task_id=lane['task_id'])
            old = qa.get(key)
            if old and old['generation'] == generation:
                require(all(old[k] == v for k, v in request.items()), 'Conflicting QA subscription')
                return old
            qa[key] = request | dict(attempts={})
            self.event(state, 'candidate_qa_subscribed', key, producer=producer)
            return qa[key]

    def _delivery_current(self, state, subscription, candidate_pin):
        candidates = self.delivery(state)['candidates'].values()
        matches = [c for c in candidates if c['producer'] == subscription['producer']
                   and c['pin'] == candidate_pin and c['current']]
        require(len(matches) == 1, 'Candidate pin superseded or missing')
        candidate = matches[0]
        producer = self.lane(state, candidate['producer'], candidate['generation'])
        require(producer.get('handoff', {}).get('sha256') == candidate['submitted_sha256'], 'Candidate source superseded')
        self._delivery_validate(candidate['snapshot'], producer)
        return candidate

    def candidate_qa_ready(self):
        from .handoff import Rejected
        with self.transaction() as state:
            ready = []
            delivery = self.delivery(state)
            for key, subscription in delivery['qa'].items():
                lane = state['lanes'][key]
                if lane['generation'] != subscription['generation'] or lane['task_id'] != subscription['task_id'] or lane['state'] != 'blocked':
                    continue
                for candidate in delivery['candidates'].values():
                    if candidate['producer'] != subscription['producer'] or not candidate['current'] or (candidate['pin'] in subscription['attempts'] and (subscription['attempts'][candidate['pin']].get('launch_id') or subscription['attempts'][candidate['pin']]['status'] == 'completed')):
                        continue
                    try:
                        self._delivery_stopped(state, lane, candidate['pin'])
                        self._delivery_current(state, subscription, candidate['pin'])
                    except Rejected:
                        continue
                    ready.append(dict(key=key, generation=lane['generation'], revision=lane['revision'],
                                      pin=candidate['pin'], session_id=subscription['session_id'], candidate=candidate))
            return ready

    def claim_candidate_qa(self, key, generation, revision, pin):
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            subscription = self.delivery(state)['qa'].get(key)
            require(subscription and subscription['generation'] == generation and subscription['task_id'] == lane['task_id'], 'Stale QA subscription')
            require(lane['state'] == 'blocked', 'Only parked QA can run provisionally')
            self._delivery_stopped(state, lane, pin)
            candidate = self._delivery_current(state, subscription, pin)
            attempt = subscription['attempts'].get(pin)
            require(not attempt or (attempt['status'] == 'claimed' and not attempt.get('launch_id') and attempt['valid']), 'Candidate QA already launched/completed')
            subscription['attempts'].setdefault(pin, dict(status='claimed', valid=True, provisional=True, at=self.clock()))
            if not attempt:
                self.event(state, 'candidate_qa_claimed', key, pin=pin)
            return dict(lane=key, pin=pin, session_id=subscription['session_id'], candidate=candidate, provisional=True)

    def record_candidate_qa(self, key, generation, pin, result, evidence):
        require(result in ('PASS', 'FAIL', 'BLOCKED'), 'Explicit QA result required')
        self.evidence(evidence)
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            subscription = self.delivery(state)['qa'].get(key)
            require(subscription and subscription['task_id'] == lane['task_id'], 'Stale QA subscription')
            linked = subscription['attempts'].get(pin, {}).get('launch_id')
            launch = state.get('control', {}).get('launches', {}).get(linked, {})
            if generation != subscription['generation']:
                require(launch.get('bound_generation') == generation and
                        launch.get('generation') == subscription['generation'] and
                        generation == subscription['generation'] + 1 and
                        launch.get('process') == lane['process'] and
                        launch.get('status') in ('running', 'completed') and
                        launch.get('lane') == key, 'Stale QA launch ownership')
            self._delivery_current(state, subscription, pin)
            attempt = subscription['attempts'].get(pin)
            require(attempt and attempt['valid'], 'Claim valid candidate before recording QA')
            record = dict(result=result, evidence=evidence, provisional=True, gameplay_accepted=False, integrated=False)
            require(not attempt.get('result') or attempt['result'] == record, 'Conflicting QA result replay')
            attempt.update(status='completed', result=record)
            self.event(state, 'candidate_qa_result', key, pin=pin, result=result)
            return record

    def bind_candidate_qa_launch(self, key, pin, launch_id):
        """Persist controller launch binding; unbound claims remain discoverable."""
        with self.transaction() as state:
            subscription = self.delivery(state)['qa'].get(key)
            require(subscription, 'Missing QA subscription')
            self._delivery_current(state, subscription, pin)
            attempt = subscription['attempts'].get(pin)
            require(attempt and attempt['valid'], 'Missing valid QA claim')
            launch = state.get('control', {}).get('launches', {}).get(launch_id)
            require(launch and launch['lane'] == key and launch['generation'] == subscription['generation'] and
                    launch.get('session') == subscription['session_id'] and launch.get('version') == pin and
                    launch.get('reason') == 'candidate_qa:' + pin and pin in launch.get('instruction', ''),
                    'Launch identity/session/candidate mismatch')
            require(not attempt.get('launch_id') or attempt['launch_id'] == launch_id, 'Conflicting launch binding')
            attempt['launch_id'] = launch_id
            return attempt

    def queue_candidate_qa(self, key, generation, revision, pin, instruction, models):
        """Atomically claim a pin and persist/bind its one launch intent."""
        from .control import fingerprint
        from .provenance import stamp
        require(nonempty(instruction) and pin in instruction, 'Instruction must identify candidate pin')
        require(models and all(nonempty(m) and '/' in m for m in models), 'Provider/model chain required')
        code = stamp()
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            subscription = self.delivery(state)['qa'].get(key)
            require(subscription and subscription['generation'] == generation and
                    subscription['task_id'] == lane['task_id'], 'Stale QA subscription')
            self._delivery_current(state, subscription, pin)
            reason = 'candidate_qa:' + pin
            identity = fingerprint([key, reason, pin, generation])
            control = self.control(state)
            old = control['launches'].get(identity)
            attempt = subscription['attempts'].get(pin)
            if old:
                require(old['session'] == subscription['session_id'] and old['version'] == pin and
                        old['reason'] == reason and old['generation'] == generation,
                        'Conflicting candidate intent')
                require(not attempt or not attempt.get('launch_id') or attempt['launch_id'] == identity,
                        'Candidate already bound elsewhere')
            else:
                require(lane['state'] == 'blocked', 'Only parked QA can run provisionally')
                self._delivery_stopped(state, lane)
                require(self.recovery_safe(state, lane), 'QA resource ownership is not stopped')
                require(not attempt or (attempt['valid'] and attempt['status'] == 'claimed' and not attempt.get('launch_id')),
                        'Candidate already completed/launched')
                old = dict(id=identity, lane=key, generation=generation, reason=reason,
                           instruction=instruction, models=models, model_index=0, version=pin,
                           session=subscription['session_id'], status='intent', process=None,
                           created_at=self.clock(), attempts=0, code_revision=code)
                control['launches'][identity] = old
                self.event(state, 'launch_intent', key, action=identity)
            attempt = subscription['attempts'].setdefault(pin, dict(status='claimed', valid=True,
                                                                    provisional=True, at=self.clock()))
            attempt['launch_id'] = identity
            return old
