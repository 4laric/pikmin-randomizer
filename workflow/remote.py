"""Fenced remote work queue; remote results are proposals, never integration."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import uuid

from .handoff import require, nonempty

CAPABILITIES = {'source-edit', 'review', 'python-tests', 'windows-build', 'windows-runtime'}
REPOSITORIES = {
    'root': 'https://github.com/4laric/pikmin-randomizer.git',
    'native': 'https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port.git',
}
LEASE_SECONDS = 180


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', value), 'Invalid identifier')
    return value


def paths(values):
    require(isinstance(values, list) and values, 'Owned files required')
    for v in values:
        require(isinstance(v, str) and v and not v.startswith('/') and '\\' not in v and ':' not in v
                and '..' not in PurePosixPath(v).parts and str(PurePosixPath(v)) == v and v != '.',
                'Use normalized repository-relative file paths')
    require(len(set(v.casefold() for v in values)) == len(values), 'Duplicate owned files')
    return {v.casefold() for v in values}


def overlap(left, right):
    return any(a == b or a.startswith(b + '/') or b.startswith(a + '/') for a in left for b in right)


def remote_state(state):
    return state.setdefault('remote', dict(workers={}, jobs={}, requests={}))


def check_remote_ownership(state, issue, owned_files):
    wanted = paths(owned_files)
    for job in remote_state(state)['jobs'].values():
        if job['state'] != 'closed':
            require(job['issue'] != issue and not overlap(wanted, paths(job['owned_files'])),
                    'Scope or issue reserved by remote job ' + job['id'])


class RemoteMixin:
    def remote_artifact(self, worker, instance, job, attempt, content, sha256):
        import base64
        try:
            data=base64.b64decode(content,validate=True)
        except (ValueError, TypeError):
            raise ValueError('Invalid artifact encoding')
        require(0 < len(data) <= 1024*1024 and hashlib.sha256(data).hexdigest()==sha256, 'Artifact hash/size mismatch (1 MiB maximum)')
        with self.transaction() as state:
            remote=remote_state(state); item=self._remote_attempt(remote,worker,instance,job,attempt)
            uploaded=item.setdefault('uploads',{})
            require(sha256 in uploaded or len(uploaded)<20, 'Attempt artifact limit reached')
            directory=self.root/'output/workflow/remote/artifacts'; directory.mkdir(parents=True,exist_ok=True)
            target=directory/sha256
            if target.exists():
                require(hashlib.sha256(target.read_bytes()).hexdigest()==sha256,'Stored artifact corrupted')
            else:
                # Registry transaction serializes writers; rename publishes complete content.
                temp=directory/(sha256+'.tmp');temp.write_bytes(data);temp.replace(target)
            uploaded[sha256]=len(data)
        return {'sha256':sha256}

    def remote_provision(self, worker, token_sha256, platform, capabilities):
        identifier(worker)
        require(platform in ('Darwin', 'Windows', 'Linux'), 'Unknown worker platform')
        require(isinstance(capabilities, list) and capabilities and set(capabilities) <= CAPABILITIES, 'Unknown capabilities')
        require(platform == 'Windows' or not any(c.startswith('windows-') for c in capabilities), 'Windows capability requires Windows worker')
        require(bool(re.fullmatch('[0-9a-f]{64}', token_sha256)), 'Token digest required')
        with self.transaction() as state:
            remote = remote_state(state)
            require(worker not in remote['workers'], 'Worker already provisioned; use a new identity to rotate credentials')
            remote['workers'][worker] = dict(id=worker, token_sha256=token_sha256, platform=platform,
                capabilities=sorted(set(capabilities)), instance=None, heartbeat=0, revoked=False)
        return {'worker': worker, 'platform': platform, 'capabilities': capabilities}

    def remote_auth(self, token):
        import hmac
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.transaction() as state:
            for worker in remote_state(state)['workers'].values():
                if not worker['revoked'] and hmac.compare_digest(worker['token_sha256'], digest):
                    return worker['id']
        raise PermissionError('Invalid worker credential')

    def remote_register(self, worker, instance, platform, capabilities):
        identifier(instance)
        with self.transaction() as state:
            remote = remote_state(state); record = remote['workers'][worker]
            require(not record['revoked'], 'Worker revoked')
            require(platform == record['platform'] and set(capabilities) <= set(record['capabilities']), 'Unapproved worker capabilities/platform')
            require(capabilities, 'No compatible capabilities')
            if record['instance'] and record['instance'] != instance:
                require(self.clock() - record['heartbeat'] >= LEASE_SECONDS, 'Previous worker instance still owns its lease')
            record.update(instance=instance, capabilities_active=capabilities, heartbeat=self.clock())
        return {'worker': worker, 'lease_seconds': LEASE_SECONDS}

    def remote_enqueue(self, job, issue, owned_files, acceptance, instruction, requirements, sources):
        identifier(job); wanted = paths(owned_files)
        require(type(issue) is int and issue > 0, 'Assigned issue required')
        require(isinstance(acceptance, list) and acceptance and all(nonempty(a) for a in acceptance), 'Acceptance criteria required')
        require(nonempty(instruction), 'Bounded task instruction required')
        require(isinstance(requirements, list) and requirements and set(requirements) <= CAPABILITIES, 'Explicit capabilities required')
        require(isinstance(sources, dict) and 'root' in sources and set(sources) <= set(REPOSITORIES), 'Pinned root/native sources required')
        for name, source in sources.items():
            require(source.get('url') == REPOSITORIES[name], 'Source must use canonical network repository')
            require(bool(re.fullmatch('[0-9a-f]{40}', source.get('commit', ''))), 'Full source commit required')
            require(nonempty(source.get('ref')) and source['ref'].startswith('refs/heads/'), 'Published source branch ref required')
        with self.transaction() as state:
            remote = remote_state(state)
            require(job not in remote['jobs'], 'Job already exists')
            check_remote_ownership(state, issue, owned_files)
            for lane in state['lanes'].values():
                if lane['state'] != 'done':
                    require(lane['issue'] != issue and not overlap(wanted, paths(lane['owned_files'])), 'Scope or issue reserved by local lane ' + lane['lane'])
            remote['jobs'][job] = dict(id=job, issue=issue, owned_files=owned_files, acceptance=acceptance,
                instruction=instruction, requirements=requirements, sources=sources, state='queued',
                generation=0, attempt=None, worker=None, instance=None, expires=0, result=None)
            return remote['jobs'][job]

    def _remote_worker(self, remote, worker, instance):
        record = remote['workers'][worker]
        require(not record['revoked'] and record['instance'] == instance, 'Worker instance superseded or revoked')
        require(self.clock() - record['heartbeat'] < LEASE_SECONDS, 'Worker registration expired; register again')
        return record

    def remote_claim(self, worker, instance, request, ram_percent):
        identifier(request)
        require(type(ram_percent) in (int, float) and 0 <= ram_percent <= 100, 'RAM measurement required')
        with self.transaction() as state:
            remote = remote_state(state); record = self._remote_worker(remote, worker, instance)
            record['heartbeat'] = self.clock()
            request_key = worker + ':' + instance + ':' + request
            previous = remote['requests'].get(request_key)
            if previous:
                job = remote['jobs'][previous['job']]
                require(job['attempt'] == previous['attempt'] and job['expires'] > self.clock() and job['state'] == 'leased', 'Previous claim expired; reconcile local attempt')
                return job
            # One remote contributor per worker for the initial pilot.
            require(not any(j['worker'] == worker and j['state'] == 'leased' and j['expires'] > self.clock() for j in remote['jobs'].values()), 'Worker already has an active job')
            if ram_percent >= 75:
                return None
            for job in remote['jobs'].values():
                if job['state'] != 'queued' or not set(job['requirements']) <= set(record['capabilities_active']):
                    continue
                job.update(state='leased', worker=worker, instance=instance, generation=job['generation']+1,
                    attempt=uuid.uuid4().hex, expires=self.clock()+LEASE_SECONDS, uploads={})
                remote['requests'][request_key] = {'job': job['id'], 'attempt': job['attempt']}
                return job
        return None

    def _remote_attempt(self, remote, worker, instance, job, attempt):
        self._remote_worker(remote, worker, instance)
        item = remote['jobs'][job]
        require(item['worker'] == worker and item['instance'] == instance and item['attempt'] == attempt, 'Stale attempt or wrong worker')
        require(item['state'] == 'leased' and item['expires'] > self.clock(), 'Attempt expired or finished')
        return item

    def remote_heartbeat(self, worker, instance, job, attempt):
        with self.transaction() as state:
            remote = remote_state(state); item = self._remote_attempt(remote, worker, instance, job, attempt)
            remote['workers'][worker]['heartbeat'] = self.clock()
            item['expires'] = self.clock() + LEASE_SECONDS
            return {'expires': item['expires'], 'lease_seconds': LEASE_SECONDS}

    def remote_result(self, worker, instance, job, attempt, result):
        require(isinstance(result, dict) and set(result) == {'summary', 'commits', 'evidence', 'outcome'}, 'Result fields: summary, commits, evidence, outcome')
        require(nonempty(result['summary']) and len(result['summary']) <= 12000, 'Bounded summary required')
        require(result['outcome'] in ('candidate', 'blocked', 'review'), 'Remote results cannot grant acceptance')
        require(isinstance(result['commits'], dict) and set(result['commits']) <= set(REPOSITORIES), 'Invalid source commits')
        require(all(isinstance(c, str) and re.fullmatch('[0-9a-f]{40}', c) for c in result['commits'].values()), 'Full result commits required')
        require(isinstance(result['evidence'], list) and 0 < len(result['evidence']) <= 20, 'Evidence required')
        for sha in result['evidence']:
            require(isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha), 'Evidence hash required')
            require((self.root/'output/workflow/remote/artifacts'/sha).is_file(), 'Upload evidence before submitting result')
        with self.transaction() as state:
            remote=remote_state(state); item=remote['jobs'][job]
            require(not remote['workers'][worker]['revoked'], 'Worker revoked')
            if item['attempt'] == attempt and item['worker'] == worker and item['instance'] == instance and item['result'] == result:
                return {'state':item['state']}  # Lost response replay, even after lease expiry.
            item=self._remote_attempt(remote,worker,instance,job,attempt)
            require(set(result['evidence']) <= set(item.get('uploads',{})), 'Evidence must belong to this attempt')
            item.update(result=result,state='awaiting_windows_validation' if result['outcome']=='candidate' else 'awaiting_review')
            # Proposal receipt never changes a local lane or admits a gameplay gate.
            self.notice_in_remote(state, job, item['state'])
            return {'state':item['state']}

    def notice_in_remote(self, state, job, status):
        identity='remote-result-'+hashlib.sha256((job+':'+str(remote_state(state)['jobs'][job]['generation'])).encode()).hexdigest()
        item=remote_state(state)['jobs'][job]
        directory=self.root/'output/workflow/remote/results';directory.mkdir(parents=True,exist_ok=True)
        path=directory/(job+'-'+item['attempt']+'.json')
        path.write_text(json.dumps(item,indent=2),encoding='utf-8')
        control=self.control(state)
        control['notices'].setdefault(identity, dict(id=identity,lane='remote:'+job,
            kind='remote_result_ready',detail={'job':job,'state':status},status='resolved',at=self.clock()))
        control['decisions'].setdefault(identity,dict(action='notify',reason='Remote proposal needs integrator review; no acceptance granted',
            job=job,issue=item['issue'],state=status,evidence=str(path)))

    def remote_requeue(self, job):
        with self.transaction() as state:
            item=remote_state(state)['jobs'][job]
            require(item['state']=='leased' and item['expires'] <= self.clock(), 'Only expired attempts can be reassigned')
            item.update(state='queued',attempt=None,result=None)
        return {'job':job,'state':'queued'}

    def remote_close(self, job, summary):
        require(nonempty(summary), 'Integrator disposition required')
        with self.transaction() as state:
            item=remote_state(state)['jobs'][job]
            require(item['state'] != 'leased' or item['expires'] <= self.clock(), 'Cannot release live remote ownership')
            item.update(state='closed',disposition=summary)
        return {'job':job,'state':'closed'}

    def remote_revoke(self, worker):
        with self.transaction() as state:
            remote_state(state)['workers'][worker]['revoked']=True
        return {'worker':worker,'revoked':True}

    def remote_status(self):
        with self.transaction() as state:
            remote=remote_state(state)
            return dict(workers=[{k:v for k,v in w.items() if k!='token_sha256'} | {'online': not w['revoked'] and self.clock()-w['heartbeat'] < LEASE_SECONDS} for w in remote['workers'].values()],
                        jobs=list(remote['jobs'].values()))
