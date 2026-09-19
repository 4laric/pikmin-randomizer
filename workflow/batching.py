"""Explicit, fenced integration batches; never merge or accept gameplay."""
import copy
import json
from pathlib import PurePosixPath

from .handoff import digest, local_path, nonempty, require, source_record, Rejected
from .analytics import finite_number
from .control import fingerprint


def _store(state):
    return state.setdefault('throughput', {}).setdefault('batches', {})


def _proven(lane):
    """The lane's receipt carries the landing proof integrate() wrote for that exact root commit."""
    landing = lane.get('integration_landing') if isinstance(lane.get('integration_landing'), dict) else {}
    return (landing.get('root') or {}).get('commit') == (lane.get('integration') or {}).get('root_commit')


def isolated_handoff(batches, key, lane):
    """Return the recorded rejection of these exact handoff ownership pins."""
    review = lane.get('review_repair')
    if review and all(review['candidate'].get(field) == lane.get(field) for field in
                      ('generation', 'revision', 'root', 'native', 'handoff')):
        return review['pin']
    for batch in batches.values():
        isolation = batch.get('isolated', {}).get(key)
        pin = batch.get('candidates', {}).get(key, {})
        if isolation and all(pin.get(field) == lane.get(field) for field in
                             ('generation', 'revision', 'root', 'native', 'handoff')):
            return dict(batch_id=batch['id'], generation=lane['generation'], revision=lane['revision'],
                        reason=isolation['reason'])
    return None


def handoff_repairs(state, now):
    """Keep isolated and currently executing repairs visible until a new handoff."""
    result = []
    batches = state.get('throughput', {}).get('batches', {})
    for key, lane in state.get('lanes', {}).items():
        pin = isolated_handoff(batches, key, lane) if lane.get('state') == 'handoff_ready' else None
        at = lane.get('handoff_at')
        status = 'blocked'
        if not pin and lane.get('repair_history') and lane.get('state') in ('running', 'blocked', 'ready', 'reconciling', 'waiting_resource'):
            previous = lane['repair_history'][-1]
            pin, at, status = previous['isolation'], previous.get('handoff_at'), lane['state']
        if pin:
            result.append(dict(lane=key, age_seconds=max(0, now-(at or now)), status=status, **pin))
    return result


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
                result = self.check_handoff(lane, state)
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

    def auto_claim_batches(self, max_candidates=16, batch_prefix='auto'):
        """Claim one bounded oldest-first batch for each live workstream owner.

        This reserves integration work only. Builds, merges, gameplay gates and
        receipts remain explicit owner actions through the normal batch API.
        """
        require(type(max_candidates) is int and 1 <= max_candidates <= 16,
                'Batch candidate limit must be between 1 and 16')
        state = self.status()
        scheduling = self.scheduling_status()
        streams = scheduling.get('workstreams', {})
        batches = scheduling.get('batches', {})
        claimed = {b.get('workstream') for b in batches.values() if b.get('state') == 'claimed'}
        results = []
        now = self.clock()
        ledger = {'approvals': self.snapshot(section=('approvals',))}
        # Repair visibility must not depend on the integrator still running.
        for key, lane in state['lanes'].items():
            if lane.get('state') == 'handoff_ready':
                isolated = isolated_handoff(batches, key, lane)
                if isolated:
                    self.notice(key, 'integration_repair_needed', isolated)
        for workstream, stream in sorted(streams.items()):
            if workstream in claimed or not isinstance(stream, dict):
                continue
            owner_key = stream.get('owner_lane')
            owner = state['lanes'].get(owner_key, {})
            if not owner_key or owner.get('state') in ('done', 'blocked') or self.probe(owner.get('process')) != 'alive':
                continue
            candidates = []
            for key in stream.get('lanes', []):
                lane = state['lanes'].get(key)
                if not lane or lane.get('state') != 'handoff_ready' or not lane.get('handoff_at'):
                    continue
                isolated = isolated_handoff(batches, key, lane)
                if isolated:
                    continue
                try:
                    result = self.check_handoff(lane, ledger)
                    if result.get('pending_reviews'):
                        continue
                    handoff = json.loads(local_path(self.root, lane['handoff']['path']).read_text(encoding='utf-8-sig'))
                    if not isinstance(handoff.get('changed_files'), list) or not handoff['changed_files']:
                        continue
                except (Rejected, OSError, ValueError, TypeError, KeyError):
                    continue
                candidates.append(dict(key=key, generation=lane['generation'], revision=lane['revision']))
            candidates.sort(key=lambda item: state['lanes'][item['key']].get('handoff_at', now))
            candidates = candidates[:max_candidates]
            if not candidates:
                continue
            batch_id = batch_prefix + '-' + workstream + '-' + fingerprint(candidates)[:12]
            try:
                results.append(self.batch_claim(batch_id, workstream, owner_key,
                                                owner['generation'], owner['revision'], candidates))
            except (Rejected, OSError, ValueError, TypeError, KeyError) as exc:
                # Candidate overlap or source drift is a normal reason to leave
                # the workstream for explicit owner adjudication.
                self.notice(owner_key, 'auto_batch_claim_rejected', dict(batch_id=batch_id, reason=str(exc)))
                continue
        return results

    def batch_reassign(self, batch_id, old_integrator, old_generation, old_revision,
                       new_integrator, new_generation, new_revision, reason):
        """Transfer a claimed batch after a fenced owner replacement."""
        require(nonempty(reason), 'Batch reassignment reason required')
        with self.transaction() as state:
            batch = _store(state).get(batch_id)
            require(batch and batch.get('state') == 'claimed', 'Claimed batch required')
            require(batch.get('integrator') == old_integrator and batch.get('generation') == old_generation,
                    'Old batch owner mismatch')
            old = self.lane(state, old_integrator, old_generation)
            new = self.lane(state, new_integrator, new_generation, new_revision)
            require(self.probe(old.get('process')) == 'dead', 'Old integration owner must be stopped')
            require(new['state'] not in ('done', 'blocked') and self.probe(new.get('process')) == 'alive',
                    'Replacement integration owner must be live')
            data = self.scheduling(state)
            stream = data['workstreams'].get(batch['workstream'])
            require(isinstance(stream, dict) and stream.get('owner_lane') == old_integrator,
                    'Workstream owner changed; reread before transfer')
            stream.update(owner_lane=new_integrator, owner=new['owner'], issue=new['issue'])
            batch.update(integrator=new_integrator, generation=new_generation,
                         revision=old_revision + 1, reassigned_at=self.clock(),
                         reassigned_from=old_integrator, reassignment_reason=reason)
            self.event(state, 'batch_reassigned', new_integrator, batch_id=batch_id,
                       previous_owner=old_integrator, reason=reason)
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
            result = self.check_handoff(lane, state)
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

    def _reprove(self, batch_id):
        """{lane: (lane record, problems)} for done candidates whose receipt predates the landing proof.

        Git runs here, outside the writer lock, over committed records read one by one."""
        from .landing import inspect
        from .storage import read_record
        batch, result = read_record(self, ('throughput', 'batches'), batch_id) or {}, {}
        for key in batch.get('candidates', {}):
            lane = read_record(self, ('lanes',), key)
            if (key in batch.get('isolated', {}) or not isinstance(lane, dict) or lane.get('state') != 'done' or
                    not isinstance(lane.get('integration'), dict) or _proven(lane)):
                continue
            try:
                result[key] = (lane, inspect(self.root, lane, lane['integration'])[1])
            except (Rejected, OSError, ValueError) as exc:
                result[key] = (lane, [dict(kind='unverifiable', detail=str(exc) or type(exc).__name__)])
        return result

    def batch_close(self, batch_id, integrator, generation, revision):
        reproved = self._reprove(batch_id)
        with self.transaction() as state:
            batch = self._batch(state, batch_id, integrator, generation, revision)
            unfinished = [key for key, pin in batch['candidates'].items()
                          if key not in batch['isolated'] and not (
                              state['lanes'][key]['generation'] == pin['generation'] and
                              state['lanes'][key]['state'] == 'done' and
                              state['lanes'][key].get('integration'))]
            require(not unfinished, 'Record per-lane integration receipts or explicitly isolate before closing: ' + ', '.join(unfinished))
            # A receipt written before the landing proof existed is re-proven read-only; it must
            # be clean against the same committed lane record, or the close refuses.
            unproven, legacy = [], {}
            for key in batch['candidates']:
                lane = state['lanes'][key]
                if key in batch['isolated'] or _proven(lane):
                    continue
                prior, problems = reproved.get(key, (None, None))
                if prior is None or problems or any(prior.get(k) != lane.get(k) for k in
                                                    ('generation', 'revision', 'root', 'native', 'integration')):
                    unproven.append(key + (': ' + '; '.join(p['detail'] for p in problems[:3]) if problems else ''))
                else:
                    legacy[key] = dict(root_commit=lane['integration'].get('root_commit'),
                                       native_commit=lane['integration'].get('native_commit'), at=self.clock())
            require(not unproven, 'Candidate receipts lack a verified landing proof (see landing_audit --lane KEY; '
                    'isolate a candidate whose commits do not contain its reviewed bytes): ' + ' | '.join(unproven))
            if legacy:
                batch.setdefault('reproved', {}).update(legacy)
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
