"""Durable outcomes, artifact versions and launch intents in the shared registry."""
import hashlib
import json
import subprocess
import uuid
from pathlib import Path

from .handoff import Rejected, digest, local_path, require, nonempty, validate_review


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def git(tree, *args):
    """Bounded; a git that cannot run or finish refuses like a failed check."""
    try:
        p = subprocess.run(['git', '-C', str(tree), *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Rejected('Git verification failed: ' + (str(exc) or type(exc).__name__))
    require(p.returncode == 0, 'Git verification failed: ' + p.stderr.strip())
    return p.stdout.strip()


class ControlMixin:
    def control(self, state):
        return state.setdefault('control', dict(artifacts={}, launches={}, providers={},
            notices={}, consumed={}, controller=None, decisions={}, ram_paused=False))

    def control_status(self):
        control=self.snapshot(section=('control',))
        return self.control({'control':control} if control else {})

    def control_meta(self):
        """Control scalars (RAM, providers, model limits) from the meta row alone; never its partitions."""
        from .storage import read_record
        return self.control(read_record(self, (), '') or {})

    def evidence(self, value):
        require(isinstance(value, dict), 'Hashed evidence required')
        path = local_path(self.root, value.get('path'))
        require(path.is_file() and digest(path) == value.get('sha256'), 'Missing or changed evidence')
        return path

    def recovery_evidence(self, value):
        """Verify recovery evidence, falling back to the content-addressed archive.

        Blocked/recovery turns consume hashed reports copied from worker inboxes
        that are cleaned later. ``evidence`` stays strict for every other caller;
        only recovery demand may resolve exact recorded bytes from
        ``output/workflow/evidence/<sha256>`` when the transient source path is
        gone. The recorded hash is never weakened or substituted.
        """
        require(isinstance(value, dict), 'Hashed evidence required')
        try:
            return self.evidence(value)
        except (Rejected, OSError):
            archived = self.archived_evidence(value)
            require(archived is not None, 'Missing or changed evidence')
            return archived

    def archived_evidence(self, value):
        """Return the archive path for exact recorded bytes, or ``None``."""
        sha = value.get('sha256') if isinstance(value, dict) else None
        if not (isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha)):
            return None
        candidate = self.root / 'output/workflow/evidence' / sha
        try:
            if candidate.is_file() and digest(candidate) == sha:
                return candidate
        except OSError:
            return None
        return None

    def finish(self, key, generation, outcome, summary, evidence, dependencies=None, path=None, shared_hooks=None):
        """A small terminal API; runtime handoffs still go through full validation.

        blocked may also carry structured shared_hooks [{kind:'shared_hook', issue, files|item_id}] next to its
        text dependencies; approvals.shared_hook_decision records decisions against them."""
        require(nonempty(summary), 'Outcome summary required')
        require(outcome in ('blocked', 'review-ready', 'implementation-ready', 'reconcile'), 'Unknown outcome')
        require(shared_hooks is None or outcome == 'blocked', 'shared_hooks belong to a blocked outcome')
        if shared_hooks is not None:
            from .approvals import hooks
            shared_hooks = hooks(shared_hooks)
        self.evidence(evidence)
        if outcome == 'implementation-ready':
            require(path is not None, 'implementation-ready requires a validated handoff path')
            lane = self.status()['lanes'][key]
            return self.submit_handoff(key, generation, lane['revision'], path)
        if outcome == 'review-ready':
            lane = self.status()['lanes'][key]
            for source_name in ('root', 'native'):
                source = lane.get(source_name)
                if not source:
                    continue
                tree = local_path(self.root, source['worktree'])
                # Synthetic/report-only fixtures may use a non-Git directory.
                # Real source worktrees must be pinned to what is actually
                # checked out when review-ready evidence is submitted.
                if (tree / '.git').exists():
                    require(git(tree, 'rev-parse', 'HEAD') == source['head'],
                            f'{source_name} worktree HEAD differs from recorded review source pin')
                    require(git(tree, 'status', '--porcelain') == source['dirty'].strip(),
                            f'{source_name} worktree dirty state differs from recorded review source')
        if outcome == 'blocked':
            # Blocked outcomes are consumed by blocked/prerequisite recovery turns
            # from worker inboxes that are cleaned later. Archive the exact bytes now
            # so the recorded report cannot be stranded by a transient source path.
            evidence = self.archive_evidence(evidence)
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            require(lane['state'] != 'done', 'Completed slice cannot be reopened')
            value = dict(outcome=outcome, summary=summary, evidence=evidence,
                         dependencies=dependencies or [])
            if shared_hooks:
                value['shared_hooks'] = shared_hooks
            if lane.get('outcome') == value and lane.get('shared_hooks', []) == (shared_hooks or []):
                return lane
            if outcome == 'blocked':
                require(dependencies and all(nonempty(d) for d in dependencies), 'Blocked needs explicit dependencies')
            if outcome == 'review-ready':
                from .support_actions import require_outcomes
                require_outcomes(state,key)
                from .review_followup import require_dispositions
                require_dispositions(state, key, generation)
            lane.update(state={'blocked': 'blocked', 'review-ready': 'review_ready',
                               'reconcile': 'reconciling'}[outcome], outcome=value,
                        next_action=summary, revision=lane['revision'] + 1,
                        dependencies=dependencies or [], progress_at=self.clock(),
                        progress_detail=summary, progress_evidence=evidence)
            if outcome == 'blocked' and (shared_hooks or 'shared_hooks' in lane):
                lane['shared_hooks'] = shared_hooks or []  # Each blocked finish replaces the structured hooks.
            elif outcome != 'blocked':
                lane.pop('shared_hooks', None)
            if outcome == 'review-ready':
                # Review is a terminal worker outcome, not runtime acceptance or source integration.
                lane['handoff_at'] = lane['handoff_at'] or self.clock()
                review = dict(schema=1, kind='review', fresh_runtime=False, conclusion=summary,
                    evidence={'review': evidence}, **{k: lane[k] for k in ('lane', 'owner', 'task_id', 'issue', 'generation')})
                lane['review'] = review
                validate_review(self.root, review, lane)
            from .no_progress import record
            record(self, state, lane, outcome)  # The substantive signal sits next to the outcome it describes.
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
        require(nonempty(summary), 'Review disposition required')
        with self.transaction() as state:
            lane = self.lane(state, key, generation)
            record = dict(summary=summary, evidence=evidence)
            if lane['state'] == 'done':
                previous = lane.get('review_disposition') or {}
                require(all(previous.get(k) == v for k, v in record.items()), 'Conflicting review disposition')
                if previous.get('archived_evidence'):
                    self.evidence(previous['archived_evidence'])
                else:
                    previous['archived_evidence'] = self.archive_evidence(evidence)
                    self.event(state, 'review_evidence_archived', key, evidence=previous['archived_evidence'])
                return lane
            require(lane['state'] == 'review_ready' and lane.get('review'), 'Completed review required')
            validate_review(self.root, lane['review'], lane)
            record['archived_evidence'] = self.archive_evidence(evidence)
            lane.update(state='done', review_disposition=record, revision=lane['revision'] + 1)
            self.event(state, 'review_accepted', key)
            return lane

    def archive_evidence(self, evidence):
        """Keep verified bytes independent of mutable worker inbox lifetimes."""
        source = local_path(self.root, evidence.get('path'))
        content = source.read_bytes()
        expected = evidence.get('sha256')
        require(hashlib.sha256(content).hexdigest() == expected, 'Missing or changed evidence')
        target = self.root / 'output/workflow/evidence' / expected
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open('xb') as stream:
                stream.write(content)
        except FileExistsError:
            require(digest(target) == expected, 'Evidence archive is corrupt')
        return dict(path=str(target), sha256=expected)

    def receipt(self, key, generation, record, root_worktree, native_worktree=None, lander=None):
        """Verify an existing integration, then replay its completion safely.

        Ancestry here is an extra, stricter gate; integrate() still proves the landed bytes."""
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
        return self.integrate(key, generation, lane['revision'], record, lander)

    def reconcile_handoff(self, key, generation, revision, summary, evidence):
        """Return a blocked lane with a still-valid handoff to handoff_ready.

        Fenced clerical repair for lanes parked in blocked by a terminal
        outcome while a validated handoff was awaiting integration (no
        supported checkpoint transition covers blocked->handoff_ready, and
        blocked->running would destroy the handoff). Fails closed unless:
        fresh generation/revision, recorded worker confirmed dead (live or
        uninspectable owners are refused so a live lane is never raced), no
        live/unknown lease or queued request for this lane/generation, no
        in-flight controller launch for this lane/generation, and the
        submitted handoff file plus every referenced evidence hash still
        revalidates. Preserves the handoff record, source identities and
        pending shared reviews; integrate() still refuses until the
        integrator approves outstanding reviews through a new handoff.
        """
        require(nonempty(summary), 'Reconcile summary required')
        self.evidence(evidence)
        with self.transaction() as state:
            lane = self.lane(state, key, generation, revision)
            require(lane['state'] == 'blocked', 'Only blocked lanes can reconcile a handoff')
            require(lane.get('handoff'), 'Blocked lane carries no submitted handoff')
            require(self.probe(lane['process']) == 'dead', 'Recorded worker is not confirmed stopped')
            for name, lease in state['leases'].items():
                if lease['lane'] == key and lease['generation'] == generation:
                    require(self.probe(lease['process']) == 'dead', 'Live/uninspectable lease held: ' + name)
            for queued_id, queued in state['queue'].items():
                if queued['lane'] == key and queued['generation'] == generation:
                    require(self.probe(queued['process']) == 'dead', 'Live/uninspectable request queued: ' + queued_id)
            launches = self.control(state).get('launches', {})
            require(not any(item['lane'] == key and item['generation'] == generation and
                            item['status'] in ('intent', 'spawned', 'running')
                            for item in launches.values()), 'Controller dispatch in flight for this lane')
            result = self.check_handoff(lane, state)
            lane.update(state='handoff_ready', revision=revision + 1,
                        outcome=None, dependencies=[],
                        next_action=summary, progress_at=self.clock(), progress_detail=summary,
                        reconcile=dict(summary=summary, evidence=evidence, at=self.clock(),
                                       pending_reviews=result['pending_reviews'],
                                       outstanding_gates=result['outstanding_gates']))
            self.check_wip(state, lane)
            self.event(state, 'handoff_reconciled', key)
            return lane

    def notice(self, key, kind, detail, status='pending'):
        """One open notice per (lane, kind, error); a repeat bumps its counter at most every ten minutes.

        Only a still-open row (same status) absorbs repeats: once the shepherd resolves it, a distinct
        detail is a new notice and an identical one stays suppressed, as with exact-detail identities.
        A notice naming a launch (action) stays one per launch. status='info' is recorded for
        visibility but never offered to the shepherd. A row written under the older exact-detail
        identity still counts when the collapsed one has none, so a resolved notice stays resolved."""
        exact = fingerprint([key, kind, detail])
        error = detail.get('error') if isinstance(detail, dict) and 'action' not in detail else None
        identity = fingerprint([key, kind, error]) if isinstance(error, str) else exact
        from .storage import read_record, selected
        old = read_record(self, ('control', 'notices'), identity)
        if old is None and identity != exact:
            legacy = read_record(self, ('control', 'notices'), exact)
            if legacy is not None: identity, old = exact, legacy
        if old is not None and old.get('status') != status:
            if old.get('detail') == detail: return identity
            identity, old = exact, read_record(self, ('control', 'notices'), exact)
        if old is not None:
            if old.get('status') == status and self.clock() - old.get('last_at', old.get('at', 0)) >= 600:
                with selected(self, [(('control', 'notices'), identity)]) as rows:
                    row = rows[(('control', 'notices'), identity)]
                    if row is not None:
                        row.update(repeats=row.get('repeats', 0) + 1, last_at=self.clock(), last_detail=detail)
            return identity
        with self.transaction() as state:
            c = self.control(state)
            c['notices'].setdefault(identity, dict(id=identity, lane=key, kind=kind,
                detail=detail, status=status, at=self.clock()))
            return identity

    def _resumable_integration_batches(self, state, lane):
        """Fence ownership, not candidate validity: invalid candidates need isolation."""
        pool = state.get('throughput', {})
        batches = [b for b in pool.get('batches', {}).values()
                   if b.get('integrator') == lane['lane'] and b.get('state') == 'claimed']
        for batch in batches:
            require(batch.get('generation') == lane['generation'], 'Stale integration batch generation')
            require(pool.get('workstreams', {}).get(batch.get('workstream'), {}).get('owner_lane') == lane['lane'],
                    'Integration batch workstream ownership changed')
        return batches

    def plan_launch(self, key, reason, instruction, models, version=None, inputs=None, obligation=False, supersedes=None,
                    carry=None):
        """Commit intent before external spawn; repeat requests return the same intent.

        Wake-type reasons pass the substantive inputs they carry; no_progress parks a stalled lane
        whose wake brings none it has not already been offered (Parked). obligation marks a wake
        that carries a non-deferrable duty (disposition_required reviews) and is never parked.
        supersedes names the stopped launch a recovery continues: it is marked exited in the same
        transaction, so a refused plan leaves it unexited for the next completion sweep. carry adds
        fields (obligations, retry counters) to a new intent without overriding its own. Whatever the
        planner, a lane whose provisioned fresh session was never adopted (session_pending) starts
        fresh again: its task_id is still the worker's previous, unrelated lane's session."""
        require(models and all(nonempty(m) and '/' in m for m in models), 'Provider/model chain required')
        require(nonempty(instruction), 'Resume instruction required')
        from . import no_progress
        from .storage import read_record
        inputs = sorted(set(inputs or []))
        # Reduced lanes use the transaction-fenced semantic-input guard below;
        # the legacy timed guard must not veto a genuinely changed input first.
        wake = no_progress.guarded(reason) and not obligation and not key.startswith('rd-')
        if wake:  # An already parked lane refuses from committed rows, without the writer lock.
            row = read_record(self, ('lanes',), key)
            refusal = row and no_progress.verdict(row, inputs, self.clock())
            if (refusal and row.get('wake_after') == refusal['wake_after'] and read_record(
                    self, ('control', 'launches'), fingerprint([key, reason, version, row['generation']])) is None):
                raise no_progress.Parked(refusal['message'])
        from .provenance import stamp
        code = stamp()
        refusal = None
        with self.transaction() as state:
            c = self.control(state)
            lane = self.lane(state, key)
            identity = fingerprint([key, reason, version, lane['generation']])
            old = c['launches'].get(identity)
            stopped = c['launches'].get(supersedes) if supersedes else None
            require(supersedes is None or (stopped and stopped['lane'] == key and
                    stopped['status'] in ('running', 'exiting', 'exited')), 'Superseded launch must belong to this lane')
            if old:
                if stopped: stopped['status'] = 'exited'
                return old
            if reason.startswith('internal-owner-resume:'):
                from .action_routing import validate_resume
                validate_resume(state,key,reason)
            owner_wakeup = reason.startswith('integration-demand:') and lane['state'] == 'review_ready'
            repair_wakeup = reason.startswith('integration-repair:')
            if repair_wakeup:
                from .integration_repair import repair_pin
                repair_pin(state, lane, reason, self)
            if owner_wakeup:
                require(any(s.get('owner_lane') == key for s in state.get('throughput', {}).get('workstreams', {}).values()),
                        'Only registered integration owners can wake from review')
            if reason.startswith('integration-demand:'):
                self._resumable_integration_batches(state, lane)
            require(owner_wakeup or repair_wakeup or lane['state'] in ('blocked', 'ready', 'running', 'reconciling'), 'Lane cannot resume')
            from .reduced_supervision import check_retry
            retry_evidence = (carry or {}).get('operator_retry_evidence')
            if retry_evidence is not None:
                require(reason.startswith('operator:'), 'Explicit operator retry reason required')
                self.evidence(retry_evidence)
                self.event(state, 'operator_retry', key, evidence=retry_evidence, reason=reason)
            else:
                check_retry(state, lane)
            require(self.recovery_safe(state, lane), 'Old worker or protected child still live/unknown')
            self.check_wip(state, dict(lane, state='running'))
            require(not any(l['lane'] == key and l['status'] in ('intent', 'spawned', 'running')
                            and l['id'] != supersedes for l in c['launches'].values()), 'Dispatch already in flight')
            require(lane['task_id'].startswith('opencode:'), 'Only known OpenCode sessions can resume')
            refusal = wake and no_progress.verdict(lane, inputs, self.clock())
            if refusal:
                no_progress.park(self, state, lane, reason, refusal)
            else:
                if wake:
                    no_progress.admit(self, state, lane, reason)
                if stopped:
                    stopped['status'] = 'exited'
                item = dict(id=identity, lane=key, generation=lane['generation'], reason=reason,
                    instruction=instruction, models=models, model_index=0, version=version,
                    session=lane['task_id'].removeprefix('opencode:'), status='intent',
                    process=None, created_at=self.clock(), attempts=0, code_revision=code)
                if inputs:
                    item['inputs'] = inputs
                item.update({k: v for k, v in (carry or {}).items() if k not in item})
                if lane.get('session_pending') and not lane.get('session_lane'):
                    item['fresh_session'] = True
                c['launches'][identity] = item
                self.event(state, 'launch_intent', key, action=identity)
                return item
        # Informational: field, event and dashboard carry it; a pending notice would invite a shepherd resume.
        self.notice(key, 'no_progress_parked', dict(error=refusal['message']), status='info')
        raise no_progress.Parked(refusal['message'])

    def _rebind_pool_recovery(self, state, item, lane):
        """Move one dispatched assignment across a verified same-session recovery."""
        pool = state.get('throughput', {})
        assignments = [a for a in pool.get('assignments', {}).values()
                       if a.get('lane') == lane['lane'] and a.get('status') == 'dispatched']
        require(len(assignments) <= 1, 'Multiple dispatched assignments for recovered lane')
        if not assignments:
            return None
        assignment = assignments[0]
        if assignment.get('launch_id') == item['id']:
            return assignment  # Initial binding or already-reconciled recovery.
        old = self.control(state)['launches'].get(assignment.get('launch_id'))
        require(isinstance(old, dict) and old.get('status') == 'exited', 'Previous pool launch must have exited')
        require(old.get('bound_generation') == item.get('generation') and
                item.get('bound_generation') == lane['generation'], 'Recovery generation chain differs')
        require(old.get('lane') == item.get('lane') == assignment['lane'] == lane['lane'], 'Recovery lane differs')
        require(lane['task_id'].startswith('opencode:') and
                old.get('session') == item.get('session') == lane['task_id'].removeprefix('opencode:'),
                'Recovery must preserve the exact worker session')
        job = pool.get('jobs', {}).get(assignment.get('job'), {})
        require(assignment.get('worker_id') == lane['worker_id'] == job.get('worker_id') and
                job.get('lane') == lane['lane'] and job.get('assignment') == assignment['id'] and
                job.get('status') == 'assigned', 'Recovery assignment worker/job ownership differs')
        require(isinstance(old.get('process'), dict) and self.probe(old['process']) == 'dead',
                'Previous pool runner remains live or unknown')
        require(item.get('process') == lane['process'], 'Recovered runner identity differs')
        link = dict(previous_launch=old['id'], launch_id=item['id'],
                    previous_generation=old['bound_generation'], generation=lane['generation'], at=self.clock())
        assignment.setdefault('recovery_history', []).append(link)
        assignment.update(launch_id=item['id'], generation=lane['generation'], revision=lane['revision'])
        self.event(state, 'pool_recovery_rebound', lane['lane'], assignment=assignment['id'],
                   previous_launch=old['id'], action=item['id'], generation=lane['generation'])
        return assignment

    def reconcile_pool_recovery(self, action_id):
        """Reconcile an already-bound recovery without modifying its live worker."""
        with self.transaction() as state:
            item = self.control(state)['launches'][action_id]
            require(item['status'] in ('running', 'exiting', 'exited'), 'Recovery launch has not bound')
            lane = self.lane(state, item['lane'], item.get('bound_generation'))
            require(type(item.get('bound_generation')) is int and item['process'] == lane['process'],
                    'Recovery no longer owns current execution')
            return self._rebind_pool_recovery(state, item, lane)

    def bind_launch(self, action_id, process):
        with self.transaction() as state:
            c = self.control(state); item = c['launches'][action_id]
            if item['status'] == 'running':
                require(item['process'] == process, 'Launch already bound to another process')
                lane = self.lane(state, item['lane'], item['bound_generation'])
                self._rebind_pool_recovery(state, item, lane)
                return lane
            require(item['status'] in ('intent', 'spawned'), 'Launch is not awaiting registration')
            lane = self.lane(state, item['lane'], item['generation'])
            require(self.recovery_safe(state, lane), 'Previous execution is not stopped')
            self.check_wip(state, dict(lane, state='running'))
            require(self.probe(process) == 'alive', 'New runner must be alive')
            resumed_batches = []
            if item['reason'].startswith('integration-demand:'):
                require(item['session'] == lane['task_id'].removeprefix('opencode:'),
                        'Integration session changed before recovery')
                resumed_batches = self._resumable_integration_batches(state, lane)
            if item['reason'].startswith('integration-repair:'):
                from .integration_repair import repair_pin
                pin = repair_pin(state, lane, item['reason'], self)
                lane.setdefault('repair_history', []).append(dict(isolation=pin, handoff=lane['handoff'],
                    root=lane['root'], native=lane.get('native'), handoff_at=lane.get('handoff_at'),
                    launch_id=action_id, at=self.clock(), handoff_code_revision=lane.pop('handoff_code_revision', None)))
                lane.update(handoff=None, handoff_at=None)
            if lane['state'] == 'review_ready':
                require(item['reason'].startswith('integration-demand:') and
                        any(s.get('owner_lane') == lane['lane'] for s in state.get('throughput', {}).get('workstreams', {}).values()),
                        'Review ownership changed before wakeup')
                lane.setdefault('completed_turns', []).append(dict(generation=lane['generation'],
                    outcome=lane.get('outcome'), review=lane.get('review'), handoff_at=lane.get('handoff_at')))
                lane.update(review=None, handoff_at=None)
            claims = [v for v in state.get('planning_claims', {}).values() if v['lane'] == lane['lane']]
            for claim in claims:
                require(self.probe(claim['process']) == 'dead', 'Original planning claim owner must be stopped')
            for claim in claims:
                claim.update(generation=lane['generation'] + 1, process=dict(process))
            if claims:
                self.event(state, 'planning_claims_rebound', lane['lane'], action=action_id)
            lane.update(generation=lane['generation'] + 1, revision=lane['revision'] + 1,
                process=process, state='running', heartbeat_at=self.clock(), progress_at=self.clock(),
                next_action=item['instruction'], progress_detail='Resumed: ' + item['reason'],
                outcome=None, failure_streak=0, recovery_count=0)
            item.update(status='running', process=process, bound_generation=lane['generation'])
            from .no_progress import bound
            bound(lane, item)  # stall_streak survives bind; only a changed terminal signal resets it.
            from .consumer_verification import bind_context
            bind_context(self,state,item,lane)
            lane['next_action']=item['instruction']
            for batch in resumed_batches:
                batch.setdefault('recovery_history', []).append(dict(
                    generation=batch['generation'], revision=batch['revision'],
                    launch_id=action_id, at=self.clock()))
                batch.update(generation=lane['generation'], revision=batch['revision'] + 1)
                self.event(state, 'integration_batch_resumed', lane['lane'],
                           batch_id=batch['id'], action=action_id)
            self._rebind_pool_recovery(state, item, lane)
            if item['version']:
                c['consumed'][item['lane']] = item['version']
            self.drop_leases(state, lane['lane'], 'launch_bound')
            state['queue'] = {k: v for k, v in state['queue'].items() if v['lane'] != lane['lane']}
            self.event(state, 'launch_bound', lane['lane'], action=action_id)
            return lane

    def controller_claim(self, process):
        """The identity stays exact for probing; its revision names the claiming process."""
        from .provenance import code_revision
        code = code_revision()  # Git runs before the writer lock is taken.
        with self.transaction() as state:
            c = self.control(state); old = c['controller']
            require(old is None or old == process or self.probe(old) == 'dead', 'Controller already live/unknown')
            c['controller'] = process
            if old != process or c.get('controller_code_revision') != dict(code, process=process):
                c['controller_code_revision'] = dict(code, process=process)  # Older claims never touch it.
                self.event(state, 'controller_started', None, process=process, code_revision=code)

    def cool_provider(self, provider, seconds):
        with self.transaction() as state:
            c = self.control(state)
            c['providers'][provider] = max(c['providers'].get(provider, 0), self.clock() + seconds)

    def select_model(self, models):
        c = self.control_meta()
        now = self.clock()
        return next((m for m in models if c['providers'].get(m.split('/')[0], 0) <= now
                     and c.get('model_limits', {}).get(m, {}).get('until', 0) <= now
                     and c.get('model_launch_after', {}).get(m, 0) <= now), None)

    def model_rate_limit(self, model, action, *, initial=30, maximum=300, reset_after=1800):
        """Persist one adaptive penalty per failed attempt, including across replay."""
        with self.transaction() as state:
            c = self.control(state)
            records = c.setdefault('model_limit_attempts', {})
            if action in records:
                return records[action]
            now = self.clock()
            previous = c.setdefault('model_limits', {}).get(model, {})
            count = previous.get('count', 0) if now - previous.get('at', 0) < reset_after else 0
            seconds = min(maximum, initial * 2 ** min(count, 16))
            record = dict(model=model, count=count + 1, at=now, until=now + seconds, seconds=seconds)
            c['model_limits'][model] = record
            records[action] = record
            return record
