"""Explicit, fenced integration batches; never merge or accept gameplay."""
import copy
import json
from pathlib import PurePosixPath

from .handoff import digest, local_path, nonempty, require, source_record
from .analytics import finite_number


def _store(state):
    return state.setdefault('throughput', {}).setdefault('batches', {})


def _files_overlap(left, right):
    def parts(value):
        require(nonempty(value) and '\\' not in value and ':' not in value,
                'Batch files must be canonical repository-relative paths')
        p = PurePosixPath(value)
        require(not p.is_absolute() and '..' not in p.parts and str(p) == value,
                'Batch files must be canonical repository-relative paths')
        return tuple(x.casefold() for x in p.parts)
    a, b = parts(left), parts(right)
    return a[:len(b)] == b or b[:len(a)] == a


class BatchingMixin:
    def _batch_owner(self, state, workstream, integrator, generation):
        owner = self.lane(state, integrator, generation)
        require(owner['state'] not in ('done', 'blocked'), 'Integrator must be active')
        require(self.probe(owner['process']) == 'alive', 'Integrator process must be live')
        stream = state.get('throughput', {}).get('workstreams', {}).get(workstream)
        require(isinstance(stream, dict) and stream.get('owner_lane') == integrator,
                'Named workstream integration owner required')
        return stream

    def batch_claim(self, batch_id, workstream, integrator, generation, revision, candidates):
        require(nonempty(batch_id) and nonempty(workstream), 'Batch ID and workstream required')
        require(isinstance(candidates, list) and 1 <= len(candidates) <= 16, 'Batch needs 1 to 16 candidates')
        with self.transaction() as state:
            self.lane(state, integrator, generation, revision)
            stream = self._batch_owner(state, workstream, integrator, generation)
            batches = _store(state)
            require(batch_id not in batches, 'Batch ID already exists')
            require(not any(b['state'] == 'claimed' and b['workstream'] == workstream for b in batches.values()),
                    'Workstream already has a claimed batch')
            pins, files = {}, []
            for item in candidates:
                require(isinstance(item, dict) and set(item) == {'key', 'generation', 'revision'}, 'Candidate ownership pins required')
                key = item['key']
                require(key not in pins and key != integrator, 'Duplicate or self candidate')
                lane = self.lane(state, key, item['generation'], item['revision'])
                require(lane.get('workstream') == workstream or key in stream.get('lanes', []) or any(j.get('lane') == key and j.get('workstream') == workstream for j in state.get('throughput', {}).get('jobs', {}).values()), 'Candidate belongs to another workstream')
                require(lane['state'] == 'handoff_ready', 'Candidate must have ready handoff')
                require(not any(b['state'] == 'claimed' and key in b['candidates'] and key not in b['isolated'] for b in batches.values()),
                        'Candidate is claimed by another batch')
                result = self.check_handoff(lane)
                require(not result['pending_reviews'], 'Candidate shared reviews unresolved')
                handoff = json.loads(local_path(self.root, lane['handoff']['path']).read_text(encoding='utf-8'))
                changed = handoff['changed_files']
                require(not any(_files_overlap(a, b) for a in files for b in changed), 'Candidates overlap source files')
                for name in changed:
                    _files_overlap(name, name)
                files.extend(changed)
                pins[key] = copy.deepcopy(dict(generation=lane['generation'], revision=lane['revision'],
                    root=lane['root'], native=lane.get('native'), handoff=lane['handoff'], changed_files=changed))
            batch = dict(id=batch_id, workstream=workstream, integrator=integrator, generation=generation,
                         revision=1, state='claimed', created_at=self.clock(), candidates=pins, isolated={}, builds=[])
            batches[batch_id] = batch
            self.event(state, 'batch_claimed', integrator, batch_id=batch_id, candidates=list(pins))
            return copy.deepcopy(batch)

    def _batch(self, state, batch_id, integrator, generation, revision):
        batch = _store(state).get(batch_id)
        require(batch is not None, 'Unknown batch')
        require(batch['state'] == 'claimed' and batch['revision'] == revision, 'Stale or closed batch')
        require(batch['integrator'] == integrator and batch['generation'] == generation, 'Batch owner mismatch')
        self._batch_owner(state, batch['workstream'], integrator, generation)
        return batch

    def _check_batch_pins(self, state, batch):
        for key, pin in batch['candidates'].items():
            if key in batch['isolated']:
                continue
            lane = self.lane(state, key, pin['generation'])
            require(lane['state'] in ('handoff_ready', 'integrating'), 'Candidate is no longer ready')
            require(all(lane.get(field) == pin[field] for field in ('root', 'native', 'handoff')), 'Candidate source or handoff drift')
            result = self.check_handoff(lane)
            require(not result['pending_reviews'], 'Candidate reviews changed')

    def batch_record_build(self, batch_id, integrator, generation, revision, sources, evidence):
        require(isinstance(sources, dict) and set(sources) == {'root', 'native'}, 'Complete build source pins required')
        source_record(sources['root'], 'root')
        if sources['native'] is not None:
            source_record(sources['native'], 'native')
        require(isinstance(evidence, dict) and evidence, 'Common build evidence required')
        for item in evidence.values():
            require(isinstance(item, dict), 'Hashed build evidence required')
            path = local_path(self.root, item.get('path'))
            require(path.is_file() and digest(path) == item.get('sha256'), 'Missing or changed build evidence')
        with self.transaction() as state:
            batch = self._batch(state, batch_id, integrator, generation, revision)
            self._check_batch_pins(state, batch)
            active = [k for k in batch['candidates'] if k not in batch['isolated']]
            require(active, 'No remaining batch candidates')
            build = dict(at=self.clock(), sources=copy.deepcopy(sources), evidence=copy.deepcopy(evidence),
                         candidates=active, candidate_pins={k: copy.deepcopy(batch['candidates'][k]) for k in active},
                         gameplay_accepted=False, superseded=False)
            batch['builds'].append(build)
            batch['revision'] += 1
            self.event(state, 'batch_build_recorded', integrator, batch_id=batch_id, candidates=active)
            return copy.deepcopy(batch)

    def batch_isolate(self, batch_id, integrator, generation, revision, candidate, reason):
        require(nonempty(reason), 'Isolation reason required')
        with self.transaction() as state:
            batch = self._batch(state, batch_id, integrator, generation, revision)
            require(candidate in batch['candidates'] and candidate not in batch['isolated'], 'Unknown or already isolated candidate')
            batch['isolated'][candidate] = dict(reason=reason, at=self.clock())
            for build in batch['builds']:
                if candidate in build['candidates']:
                    build['superseded'] = True
                    build['superseded_reason'] = 'Candidate isolated: ' + candidate
            batch['revision'] += 1
            self.event(state, 'batch_candidate_isolated', integrator, batch_id=batch_id, candidate=candidate)
            return copy.deepcopy(batch)

    def batch_close(self, batch_id, integrator, generation, revision):
        with self.transaction() as state:
            batch = self._batch(state, batch_id, integrator, generation, revision)
            batch.update(state='closed', closed_at=self.clock(), revision=revision + 1)
            self.event(state, 'batch_closed', integrator, batch_id=batch_id)
            return copy.deepcopy(batch)

    def _report_cost(self, state, event_id, lane, amount, currency='USD', at=None):
        require(nonempty(event_id) and isinstance(currency, str) and len(currency) == 3 and currency.isalpha() and currency.isupper(), 'Cost ID and ISO currency required')
        finite_number(amount, 'amount', minimum=0)
        if at is not None:
            finite_number(at, 'at', minimum=0)
        self.lane(state, lane)
        costs = state.setdefault('throughput', {}).setdefault('costs', {})
        prior = costs.get(event_id)
        value = dict(id=event_id, lane=lane, amount=amount, currency=currency,
                     at=prior['at'] if prior and at is None else self.clock() if at is None else at)
        require(prior is None or prior == value, 'Cost ID already has another value')
        if prior is None:
            costs[event_id] = value
            self.event(state, 'cost_reported', lane, event_id=event_id)
        return copy.deepcopy(value), prior is None

    def report_cost(self, event_id, lane, amount, currency='USD', at=None):
        with self.transaction() as state:
            return self._report_cost(state, event_id, lane, amount, currency, at)[0]

    def report_cost_batch(self, events):
        """Atomic ingestion; one invalid/conflicting event rolls back the batch."""
        require(isinstance(events, list), 'Cost events must be a list')
        with self.transaction() as state:
            count = 0
            for item in events:
                require(isinstance(item, dict) and {'event_id', 'lane', 'amount'} <= set(item) and
                        set(item) <= {'event_id', 'lane', 'amount', 'currency', 'at'}, 'Invalid cost event')
                _, added = self._report_cost(state, **item)
                count += int(added)
            return count
