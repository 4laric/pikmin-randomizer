"""Durable outcomes, artifact versions and launch intents in the shared registry."""
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

from .handoff import digest, local_path, require, nonempty, validate_review


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def git(tree, *args):
    p = subprocess.run(['git', '-C', str(tree), *args], capture_output=True, text=True)
    require(p.returncode == 0, 'Git verification failed: ' + p.stderr.strip())
    return p.stdout.strip()


class ControlMixin:
    def control(self, state):
        return state.setdefault('control', dict(artifacts={}, launches={}, providers={},
            notices={}, consumed={}, controller=None, decisions={}, ram_paused=False))

    def control_status(self):
        with self.transaction() as state:
            return self.control(state)

    def evidence(self, value):
        require(isinstance(value, dict), 'Hashed evidence required')
        path = local_path(self.root, value.get('path'))
        require(path.is_file() and digest(path) == value.get('sha256'), 'Missing or changed evidence')
        return path

    def finish(self, key, generation, outcome, summary, evidence, dependencies=None, path=None):
        """A small terminal API; runtime handoffs still go through full validation."""
        require(nonempty(summary), 'Outcome summary required')
        require(outcome in ('blocked', 'review-ready', 'implementation-ready', 'reconcile'), 'Unknown outcome')
        self.evidence(evidence)
        if outcome == 'implementation-ready':
            require(path is not None, 'implementation-ready requires a validated handoff path')
            lane = self.status()['lanes'][key]
            return self.submit_handoff(key, generation, lane['revision'], path)
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            require(lane['state'] != 'done', 'Completed slice cannot be reopened')
            value = dict(outcome=outcome, summary=summary, evidence=evidence,
                         dependencies=dependencies or [])
            if lane.get('outcome') == value:
                return lane
            if outcome == 'blocked':
                require(dependencies and all(nonempty(d) for d in dependencies), 'Blocked needs explicit dependencies')
            lane.update(state={'blocked': 'blocked', 'review-ready': 'review_ready',
                               'reconcile': 'reconciling'}[outcome], outcome=value,
                        next_action=summary, revision=lane['revision'] + 1,
                        dependencies=dependencies or [], progress_at=self.clock(),
                        progress_detail=summary, progress_evidence=evidence)
            if outcome == 'review-ready':
                # Review is a terminal worker outcome, not runtime acceptance or source integration.
                lane['handoff_at'] = lane['handoff_at'] or self.clock()
                review = dict(schema=1, kind='review', fresh_runtime=False, conclusion=summary,
                    evidence={'review': evidence}, **{k: lane[k] for k in ('lane', 'owner', 'task_id', 'issue', 'generation')})
                lane['review'] = review
                validate_review(self.root, review, lane)
            self.check_wip(state, lane)
            self.event(state, 'outcome', key, outcome=outcome)
            return lane

    def publish(self, producer, version, evidence, description):
        """Only completed provider slices publish automatic-wakeup artifacts."""
        self.evidence(evidence)
        require(nonempty(version) and nonempty(description), 'Artifact version and contract required')
        with self.transaction() as state:
            lane = self.lane(state, producer)
            require(lane['state'] == 'done' and lane.get('integration'), 'Provider must be integrated before publication')
            c = self.control(state)
            item = dict(producer=producer, version=version, evidence=evidence, description=description)
            key = producer + ':' + version
            previous = c['artifacts'].get(key)
            require(previous is None or previous == item, 'Artifact versions are immutable')
            c['artifacts'][key] = item
            if previous is None:
                self.event(state, 'artifact_published', producer, version=version)
            return item

    def accept_review(self, key, generation, summary, evidence):
        """Integrator acknowledges a completed review without promoting gameplay gates."""
        self.evidence(evidence)
        require(nonempty(summary), 'Review disposition required')
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            record = dict(summary=summary, evidence=evidence)
            if lane['state'] == 'done':
                require(lane.get('review_disposition') == record, 'Conflicting review disposition')
                return lane
            require(lane['state'] == 'review_ready' and lane.get('review'), 'Completed review required')
            validate_review(self.root, lane['review'], lane)
            lane.update(state='done', review_disposition=record, revision=lane['revision'] + 1)
            self.event(state, 'review_accepted', key)
            return lane

    def receipt(self, key, generation, record, root_worktree, native_worktree=None):
        """Verify an existing integration, then replay its completion safely."""
        self.evidence(dict(path=record.get('validation_path'), sha256=record.get('validation_sha256')))
        lane = self.status()['lanes'][key]
        require(lane['generation'] == generation, 'Stale ownership generation')
        root = local_path(self.root, root_worktree)
        git(root, 'merge-base', '--is-ancestor', lane['root']['head'], record['root_commit'])
        if lane.get('handoff'):
            handoff = json.loads(Path(lane['handoff']['path']).read_text(encoding='utf-8-sig'))
            if handoff.get('native'):
                tree = local_path(self.root, native_worktree)
                git(tree, 'merge-base', '--is-ancestor', handoff['native']['head'], record['native_commit'])
        if lane['state'] == 'done':
            require(lane.get('integration') == record, 'Conflicting integration receipt')
            return lane
        require(lane['state'] in ('handoff_ready', 'integrating'), 'Validated implementation handoff required')
        if lane['state'] != 'integrating':
            lane = self.checkpoint(key, generation, lane['revision'], {'state': 'integrating'})
        return self.integrate(key, generation, lane['revision'], record)

    def notice(self, key, kind, detail):
        with self.transaction() as state:
            c = self.control(state)
            identity = fingerprint([key, kind, detail])
            c['notices'].setdefault(identity, dict(id=identity, lane=key, kind=kind,
                detail=detail, status='pending', at=self.clock()))
            return identity

    def plan_launch(self, key, reason, instruction, models, version=None):
        """Commit intent before external spawn; repeat requests return the same intent."""
        require(models and all(nonempty(m) and '/' in m for m in models), 'Provider/model chain required')
        require(nonempty(instruction), 'Resume instruction required')
        with self.transaction() as state:
            c = self.control(state)
            lane = self.lane(state, key)
            identity = fingerprint([key, reason, version, lane['generation']])
            old = c['launches'].get(identity)
            if old:
                return old
            require(lane['state'] in ('blocked', 'ready', 'running', 'reconciling'), 'Lane cannot resume')
            require(self.recovery_safe(state, lane), 'Old worker or protected child still live/unknown')
            require(not any(l['lane'] == key and l['status'] in ('intent', 'spawned', 'running')
                            for l in c['launches'].values()), 'Dispatch already in flight')
            item = dict(id=identity, lane=key, generation=lane['generation'], reason=reason,
                instruction=instruction, models=models, model_index=0, version=version,
                session=lane['task_id'].removeprefix('opencode:'), status='intent',
                process=None, created_at=self.clock(), attempts=0)
            require(lane['task_id'].startswith('opencode:'), 'Only known OpenCode sessions can resume')
            c['launches'][identity] = item
            self.event(state, 'launch_intent', key, action=identity)
            return item

    def bind_launch(self, action_id, process):
        with self.transaction() as state:
            c = self.control(state); item = c['launches'][action_id]
            if item['status'] == 'running':
                require(item['process'] == process, 'Launch already bound to another process')
                return self.lane(state, item['lane'])
            require(item['status'] in ('intent', 'spawned'), 'Launch is not awaiting registration')
            lane = self.lane(state, item['lane'], item['generation'])
            require(self.recovery_safe(state, lane), 'Previous execution is not stopped')
            require(self.probe(process) == 'alive', 'New runner must be alive')
            lane.update(generation=lane['generation'] + 1, revision=lane['revision'] + 1,
                process=process, state='running', heartbeat_at=self.clock(), progress_at=self.clock(),
                next_action=item['instruction'], progress_detail='Resumed: ' + item['reason'],
                outcome=None, failure_streak=0, recovery_count=0)
            item.update(status='running', process=process, bound_generation=lane['generation'])
            if item['version']:
                c['consumed'][item['lane']] = item['version']
            state['leases'] = {k: v for k, v in state['leases'].items() if v['lane'] != lane['lane']}
            state['queue'] = {k: v for k, v in state['queue'].items() if v['lane'] != lane['lane']}
            self.event(state, 'launch_bound', lane['lane'], action=action_id)
            return lane

    def controller_claim(self, process):
        with self.transaction() as state:
            c = self.control(state); old = c['controller']
            require(old is None or old == process or self.probe(old) == 'dead', 'Controller already live/unknown')
            c['controller'] = process

    def cool_provider(self, provider, seconds):
        with self.transaction() as state:
            c = self.control(state)
            c['providers'][provider] = max(c['providers'].get(provider, 0), self.clock() + seconds)

    def select_model(self, models):
        c = self.control_status()
        return next((m for m in models if c['providers'].get(m.split('/')[0], 0) <= self.clock()), None)
