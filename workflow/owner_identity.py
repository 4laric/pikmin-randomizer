"""Explicit correction of an idle lane's mistaken live process registration.

This is not recovery: both identities must remain alive, and no execution may
be transferred. The hashed owner receipt pins the whole lane and actual source
bytes. There is deliberately no caller-chain override on the public API.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess

from . import approvals, processes
from .handoff import Rejected, digest, local_path, nonempty, require


def sha(content):
    return hashlib.sha256(content).hexdigest()


def git_bytes(path, *args):
    try:
        result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Rejected('Source observation unavailable: ' + str(exc)) from exc
    require(result.returncode == 0, 'Source observation failed')
    return result.stdout


def sources(reg, receipt):
    """Verify separately pinned live source, without rewriting registered source."""
    lane = receipt['lane']
    expected_repos = {repo for repo in ('root', 'native') if lane.get(repo)}
    rows = receipt.get('observed_worktrees')
    require(isinstance(rows, list) and len(rows) == len(expected_repos) and
            {row.get('repo') for row in rows} == expected_repos, 'Exact source observations required')
    for row in rows:
        record = lane[row['repo']]
        tree = local_path(reg.root, record['worktree'])
        require(tree == local_path(reg.root, row['path']) and (tree / '.git').is_file(),
                'Exact linked private source checkout required')
        require(tree.is_relative_to(reg.root / 'output'), 'Private source checkout required')
        require(git_bytes(tree, 'rev-parse', 'HEAD').decode().strip() == row['head'] == record['head'],
                'Source HEAD changed')
        dirty = git_bytes(tree, 'status', '--porcelain').decode('utf-8').replace('\r\n', '\n')
        require(dirty == row['dirty'] and sha(dirty.encode()) == row['dirty_sha256'], 'Source dirty status changed')
        # Schema 1 owner receipts use raw `git diff --binary` bytes. Refuse any
        # staged delta, which that observation cannot attest.
        require(not git_bytes(tree, 'diff', '--cached', '--binary'), 'Staged source requires a new receipt schema')
        diff = git_bytes(tree, 'diff', '--binary')
        require(sha(diff) == row['tracked_diff_sha256'], 'Source tracked bytes changed')
        # -z avoids quoting/rename ambiguity. Every untracked file must be hashed;
        # tracked changes are also bound by the complete binary HEAD diff.
        untracked = git_bytes(tree, 'ls-files', '--others', '--exclude-standard', '-z').decode('utf-8').split('\0')
        entries = row.get('files')
        require(isinstance(entries, list), 'Source file hashes required')
        keys = [item.get('path') for item in entries]
        require(all(isinstance(key, str) for key in keys) and len(keys) == len(set(keys)), 'Unique source file paths required')
        require(set(filter(None, untracked)) <= set(keys), 'Unhashed untracked source')
        for item in entries:
            path = (tree / item['path']).resolve()
            require(path.is_relative_to(tree) and not Path(item['path']).is_absolute() and
                    path.is_file() and not (tree / item['path']).is_symlink(), 'Exact regular source file required')
            require(digest(path) == item['sha256'], 'Source file bytes changed')


def execution(reg, state, receipt):
    lane = reg.lane(state, receipt['lane']['lane'])
    require(lane == receipt['lane'], 'Stale whole-lane identity; obtain fresh owner consent')
    require(lane['state'] in ('ready', 'running', 'blocked') and lane.get('handoff') is None,
            'Lane has delivery or execution in flight')
    old, new = receipt['old_process'], receipt['new_process']
    require(old == lane['process'] and new != old, 'Exact distinct old/new identities required')
    require(reg.probe(old) == 'alive' and reg.probe(new) == 'alive', 'Both exact identities must be alive')
    chain = approvals.ancestry()
    require(new in chain and old not in chain, 'Replacement must be an actual caller ancestor; old must be outside it')
    # A common desktop host may own other lanes. Only the mistaken old owner is
    # required to be childless; unrelated descendants of the new host are allowed.
    require(processes.busy_descendants(processes.process_rows(), old['pid']) == [],
            'Old owner descendants absent or uninspectable')
    require(reg.probe(old) == 'alive' and reg.probe(new) == 'alive',
            'Exact identities changed during process observation')
    for section in ('leases', 'queue'):
        require(not any(row.get('lane') == lane['lane'] for row in state.get(section, {}).values()),
                'Lane retains resource lease or request')
    require(not any(row.get('lane') == lane['lane'] and row.get('status') in
                    ('intent', 'spawned', 'running', 'exiting')
                    for row in state.get('control', {}).get('launches', {}).values()), 'Lane launch in flight')
    require(not lane.get('session_pending'), 'Lane session adoption in flight')
    require(not any(row.get('lane') == lane['lane'] for row in state.get('planning_claims', {}).values()),
            'Lane retains planning claim')
    require(not any(row.get('lane') == lane['lane'] and row.get('status') == 'claimed'
                    for row in state.get('actions', {}).values()), 'Lane action already claimed')
    require(not any(row.get('lane') == lane['lane'] and row.get('status') not in ('completed', 'cancelled')
                    for row in state.get('control', {}).get('terminal_recoveries', {}).values()),
            'Lane terminal recovery in flight')
    delivery = state.get('throughput', {})
    for collection in ('jobs', 'assignments'):
        require(not any((row.get('lane') == lane['lane'] or row.get('worker_id') == lane['worker_id']) and
                        row.get('status') not in ('completed', 'cancelled', 'superseded')
                        for row in delivery.get(collection, {}).values()), 'Lane or worker has queued pool execution')
    require(not any(row.get('producer') == lane['lane'] and row.get('current')
                    for row in delivery.get('candidates', {}).values()), 'Lane has current delivery candidate')
    require(not any(row.get('lane') == lane['lane'] or row.get('producer') == lane['lane']
                    for row in delivery.get('qa', {}).values()), 'Lane has delivery QA subscription')
    return lane, chain


class OwnerIdentityMixin:
    def correct_owner_identity(self, consent, *, apply=False):
        """Read-only preflight by default; explicit apply records an atomic correction."""
        path = self.evidence(consent)
        content = path.read_bytes()
        require(sha(content) == consent['sha256'], 'Owner consent changed')
        receipt = json.loads(content.decode('utf-8-sig'))
        require(receipt.get('schema') == 1 and type(receipt.get('correction_issue')) is int and
                receipt['correction_issue'] > 0 and receipt['correction_issue'] != receipt['lane']['issue'] and
                receipt.get('implementation_issue') == receipt['lane']['issue'] and
                nonempty(receipt.get('owner_consent')), 'Issue-scoped explicit owner consent required')
        require(nonempty(receipt.get('registration_error')), 'Explicit clerical registration error required')
        error_evidence = receipt.get('registration_error_evidence')
        self.evidence(error_evidence)
        require(receipt.get('resources') == [] and receipt.get('queue') == [], 'Owner must attest no execution resources')
        require(receipt['new_process'] in receipt.get('actual_caller_chain', []), 'Owner receipt lacks replacement ancestry')
        sources(self, receipt)
        state = self.snapshot()
        lane, chain = execution(self, state, receipt)
        if not apply:
            return dict(preflight=True, applied=False, lane=lane['lane'], generation=lane['generation'],
                        revision=lane['revision'], consent=consent)
        # Archive exact consent before the transaction; an aborted attempt may
        # leave harmless content-addressed evidence, never a corrected lane.
        archived = self.archive_evidence(consent)
        archived_error = self.archive_evidence(error_evidence)
        with self.transaction() as state:
            require(digest(path) == consent['sha256'], 'Owner consent changed')
            self.evidence(error_evidence)
            sources(self, receipt)
            lane, chain = execution(self, state, receipt)
            before = copy.deepcopy(lane)
            lane['process'] = copy.deepcopy(receipt['new_process'])
            lane['revision'] += 1
            audit = dict(issue=receipt['correction_issue'], before=before, after=copy.deepcopy(lane),
                         consent=archived, registration_error_evidence=archived_error,
                         observed_worktrees=copy.deepcopy(receipt['observed_worktrees']),
                         actual_caller_chain=chain, at=self.clock())
            records = state.setdefault('owner_identity_corrections', {})
            require(consent['sha256'] not in records, 'Consent already consumed')
            records[consent['sha256']] = audit
            self.event(state, 'owner_identity_corrected', lane['lane'], issue=receipt['correction_issue'],
                       consent=archived, revision=lane['revision'])
            return copy.deepcopy(audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--consent', required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    from .registry import Registry
    root = Path(args.root).resolve()
    result = Registry(root / 'output/workflow/registry.sqlite3', root).correct_owner_identity(
        dict(path=args.consent, sha256=args.sha256), apply=args.apply)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
