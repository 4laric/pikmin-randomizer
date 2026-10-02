"""Issue-backed editing agreements for communicating agents, never acceptance.

Inactive producers retain their claims and their incomplete delivery evidence.
Only the live integration actor amends its scope, in a distinct private checkout.
"""
import argparse
import copy
import json
from pathlib import Path, PurePosixPath

from .control import fingerprint, git
from .handoff import local_path, nonempty, require


def files(value):
    require(isinstance(value, list) and value and all(nonempty(f) for f in value), 'Exact file keys required')
    require(len({f.casefold() for f in value}) == len(value), 'Duplicate file key')
    for f in value:
        require(not Path(f).is_absolute() and ':' not in f and '\\' not in f and
                '..' not in PurePosixPath(f).parts and str(PurePosixPath(f)) == f,
                'Use normalized repository-relative file keys')
    return value


def identity(lane):
    return copy.deepcopy({k: lane.get(k) for k in
                          ('lane', 'issue', 'generation', 'worker_id', 'task_id', 'process', 'root', 'native')})


def actor(reg, state, key, generation, chain):
    lane = reg.lane(state, key, generation)
    require(lane['state'] == 'running' and reg.probe(lane['process']) == 'alive', 'Live integration actor required')
    require(lane['process'] in chain, 'Caller must run inside the registered integration process')
    # Communicating desktop agents need no synthetic OpenCode/controller launch.
    reg.check_wip(state, lane)
    return lane


def checkout(reg, lane, repo, *, consumer):
    source = lane.get(repo)
    require(isinstance(source, dict), 'Source record required for ' + repo)
    path = local_path(reg.root, source['worktree'])
    if consumer:
        require(path.is_relative_to(reg.root / 'output') and path != reg.root / 'output',
                'Coordinated edits require a private checkout under output/')
    # A missing historical producer checkout is disclosed, not repaired or accepted.
    # The integration consumer always needs a real linked private git worktree.
    if not path.exists():
        require(not consumer, 'Integration checkout missing')
        return dict(path=str(path), git_dir=None, missing=True)
    if consumer:
        require((path / '.git').is_file(), 'Linked private git worktree required')
    else:
        # Historical producers may reference the canonical or an ordinary checkout.
        # This is a read-only identity reference, never permission to edit it.
        require((path / '.git').exists(), 'Producer git checkout reference required')
    directory = git(path, 'rev-parse', '--absolute-git-dir')
    if consumer:
        # A .git text file alone can redirect to an ordinary/shared git directory.
        # A linked checkout also has its own metadata pointing back to this path.
        backlink = Path(directory) / 'gitdir'
        target = Path(backlink.read_text().strip()) if backlink.is_file() else None
        if target is not None and not target.is_absolute():
            target = backlink.parent / target
        require(target is not None and target.resolve() == path / '.git',
                'Linked private git worktree identity required')
        require(git(path, 'rev-parse', 'HEAD') == source['head'], 'Integration checkout HEAD differs from source pin')
    return dict(path=str(path), git_dir=str(Path(directory).resolve()), missing=False)


def current(reg, state, row):
    """Revalidate all frozen identities and evidence before any new scope access."""
    for item in [row['integration']] + row['participants']:
        lane = reg.lane(state, item['identity']['lane'])
        require(identity(lane) == item['identity'], 'Stale coordination source/task/process/generation identity')
        require(lane['state'] != 'done', 'Completed lane requires a new agreement')
        for repo, expected in item['checkouts'].items():
            require(checkout(reg, lane, repo, consumer=item is row['integration']) == expected,
                    'Coordinated checkout identity changed')
    reg.evidence(row['authorization'])
    for item in row['participants']:
        for evidence in item['evidence']:
            reg.evidence(evidence)
        owner = reg.lane(state, item['identity']['lane'])
        require({f.casefold() for f in item['files']} <= {f.casefold() for f in owner['owned_files']},
                'Producer ownership changed')
    return row


class CoordinationMixin:
    def coordinate(self, request, *, chain=None):
        """Record editing-only access. The integration owner attests the evidence,
        distinguishing actual owner communication from legacy preservation authority.
        No producer state, handoff, shared review, claim or receipt is changed.
        """
        from .approvals import ancestry
        from .provenance import stamp
        chain = ancestry() if chain is None else chain
        require(isinstance(request, dict) and set(request) ==
                {'lane', 'generation', 'revision', 'issue', 'scope', 'authorization', 'participants'},
                'Exact coordination request fields required')
        require(nonempty(request['scope']), 'Issue-backed scope required')
        self.evidence(request['authorization'])
        participants = request['participants']
        require(isinstance(participants, list) and participants, 'Scoped producer participants required')
        require(all(isinstance(p, dict) for p in participants) and
                len({p.get('lane') for p in participants}) == len(participants), 'One participant per producer')
        with self.transaction() as state:
            owner = actor(self, state, request['lane'], request['generation'], chain)
            self.lane(state, owner['lane'], revision=request['revision'])
            require(request['issue'] == owner['issue'], 'Agreement must reference integration lane issue')
            integration = dict(identity=identity(owner), checkouts={})
            records = []
            for p in participants:
                require(set(p) == {'lane', 'generation', 'source', 'files', 'basis', 'preservation', 'evidence'},
                        'Exact producer coordination fields required')
                require(p['basis'] in ('owner-communication', 'user-authorized-legacy-preservation'),
                        'Describe actual coordination basis honestly')
                require(nonempty(p['preservation']), 'Bounded preservation obligations required')
                producer = self.lane(state, p['lane'], p['generation'])
                require(producer['lane'] != owner['lane'] and producer['state'] != 'done', 'Unfinished distinct producer required')
                require(p['source'] == identity(producer), 'Exact producer source/task identity required')
                keys = files(p['files'])
                require({f.casefold() for f in keys} <= {f.casefold() for f in producer['owned_files']},
                        'Agreement files must be producer-owned')
                require(isinstance(p['evidence'], list) and p['evidence'], 'Hashed communication/preservation evidence required')
                for evidence in p['evidence']:
                    self.evidence(evidence)
                repos = {'native' if f.startswith('native/') else 'root' for f in keys}
                checkouts = {}
                for repo in repos:
                    integration['checkouts'][repo] = checkout(self, owner, repo, consumer=True)
                    checkouts[repo] = checkout(self, producer, repo, consumer=False)
                    a, b = integration['checkouts'][repo], checkouts[repo]
                    require(a['path'].casefold() != b['path'].casefold() and
                            (b['git_dir'] is None or a['git_dir'].casefold() != b['git_dir'].casefold()),
                            'Shared checkout cannot be coordinated')
                records.append(dict(identity=identity(producer), files=copy.deepcopy(keys), basis=p['basis'],
                                    preservation=p['preservation'], evidence=copy.deepcopy(p['evidence']), checkouts=checkouts))
            value = dict(issue=owner['issue'], scope=request['scope'], authorization=copy.deepcopy(request['authorization']),
                         integration=integration, participants=records)
            agreement_id = fingerprint(value)
            rows = state.setdefault('coordination_agreements', {})
            if agreement_id not in rows:
                rows[agreement_id] = dict(value, id=agreement_id, at=self.clock(), code_revision=stamp(), editing_only=True)
                self.event(state, 'coordination_agreed', owner['lane'], agreement=agreement_id)
            return copy.deepcopy(rows[agreement_id])

    def amend_scope(self, key, generation, revision, agreement_ids, additions, scope, *, chain=None):
        from .approvals import ancestry
        chain = ancestry() if chain is None else chain
        files(additions)
        require(nonempty(scope), 'Updated issue-backed scope required')
        require(isinstance(agreement_ids, list) and all(nonempty(v) for v in agreement_ids),
                'Coordination agreement IDs must be a list of nonempty strings')
        with self.transaction() as state:
            lane = actor(self, state, key, generation, chain)
            self.lane(state, key, generation, revision)
            # Unclaimed files need no producer agreement, but they still require
            # an actual private checkout at the pinned HEAD for every touched repo.
            for repo in {'native' if f.casefold().startswith('native/') else 'root' for f in additions}:
                checkout(self, lane, repo, consumer=True)
            covered = set()
            for agreement_id in agreement_ids:
                row = state.get('coordination_agreements', {}).get(agreement_id)
                require(row is not None and row['integration']['identity'] == identity(lane), 'Unknown or mismatched agreement')
                current(self, state, row)
                for p in row['participants']:
                    covered.update((p['identity']['lane'], f.casefold()) for f in p['files'])
            for other in state['lanes'].values():
                if other['lane'] == key or other['state'] == 'done':
                    continue
                overlap = {f.casefold() for f in additions} & {f.casefold() for f in other['owned_files']}
                require(all((other['lane'], f) in covered for f in overlap), 'Uncoordinated producer overlap')
            # Remote ownership is not silently waived; nonlocal issue claims still govern.
            from .remote import check_remote_ownership
            check_remote_ownership(state, lane['issue'], additions)
            lane['owned_files'] += [f for f in additions if f.casefold() not in {v.casefold() for v in lane['owned_files']}]
            lane['scope'] = scope
            lane.setdefault('coordination', []).append(dict(agreements=copy.deepcopy(agreement_ids), files=copy.deepcopy(additions)))
            lane['revision'] += 1
            self.event(state, 'scope_amended', key, agreements=agreement_ids, files=additions, scope=scope)
            return copy.deepcopy(lane)

    def check_coordination(self, agreement_id):
        state = self.snapshot()
        row = state.get('coordination_agreements', {}).get(agreement_id)
        require(row is not None, 'Unknown coordination agreement')
        return copy.deepcopy(current(self, state, row))


def main():
    from .registry import Registry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('agree', 'amend', 'check'))
    parser.add_argument('--root', required=True)
    parser.add_argument('--request', required=True, help='Private JSON request path (or agreement ID for check)')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    reg = Registry(root / 'output/workflow/registry.sqlite3', root)
    if args.action == 'check':
        result = reg.check_coordination(args.request)
    else:
        request = json.loads(local_path(root, args.request).read_text(encoding='utf-8-sig'))
        result = reg.coordinate(request) if args.action == 'agree' else reg.amend_scope(**request)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
