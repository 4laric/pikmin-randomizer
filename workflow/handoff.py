"""Validate reviewable evidence, without promoting it to gameplay acceptance."""
import hashlib
import json
from pathlib import Path
import re

GATES = ('identity_spawn', 'movement_animation', 'attacks_receivers',
         'death_corpse', 'transport_reward', 'cleanup_reentry')
RESULTS = {'PASS', 'FAIL', 'BLOCKED', 'UNTESTED', 'N/A'}


class Rejected(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_path(root, value):
    require(nonempty(value), 'Expected local path')
    path = (Path(root) / value).resolve()
    require(path.is_relative_to(Path(root).resolve()), 'Path escapes workspace: ' + value)
    return path


def source_record(value, name):
    require(isinstance(value, dict), name + ': source record required')
    for key in ('base', 'head'):
        require(bool(re.fullmatch(r'[0-9a-f]{40}', value.get(key, ''))), name + ': full ' + key + ' required')
    require(isinstance(value.get('dirty'), str), name + ': dirty state required (empty means clean)')
    require(nonempty(value.get('worktree')), name + ': worktree required')
    require(isinstance(value.get('commits'), list) and all(
        isinstance(c, str) and re.fullmatch(r'[0-9a-f]{40}', c) for c in value['commits']),
        name + ': ordered full commits required')
    require(value['head'] == (value['commits'][-1] if value['commits'] else value['base']),
            name + ': head must end the ordered commit list')


def validate_handoff(root, data, lane=None):
    """Raise Rejected on missing/tampered evidence; accept explicit untested gates."""
    if isinstance(data, dict) and data.get('kind') == 'review':
        return validate_review(root, data, lane)
    require(isinstance(data, dict) and data.get('schema') == 1, 'Handoff schema must be 1')
    for key in ('lane', 'owner', 'task_id', 'scope', 'target_level', 'next_action'):
        require(nonempty(data.get(key)), key + ' required')
    for key in ('issue', 'parent_issue', 'generation'):
        require(type(data.get(key)) is int and data[key] > 0, key + ' must be positive')
    if lane:
        for key in ('lane', 'owner', 'task_id', 'issue', 'generation', 'scope', 'target_level'):
            require(data[key] == lane[key], 'Handoff differs from lane: ' + key)
    require(data.get('kind') in ('runtime', 'tooling'), 'kind must be runtime or tooling')
    for key in ('owned_files', 'changed_files', 'source_mapping', 'tests', 'remaining_work', 'shared_reviews'):
        require(isinstance(data.get(key), list), key + ' must be a list')
    require(data['owned_files'] and data['changed_files'] and data['source_mapping'] and data['tests'],
            'Ownership, changes, source mapping and tests cannot be empty')
    for name in data['owned_files'] + data['changed_files']:
        require(nonempty(name), 'File names must be strings')
    if lane:
        require(data['owned_files'] == lane['owned_files'], 'Ownership differs from lane')
    for repo in ('root', 'native'):
        if repo == 'native' and data.get('native') is None and data['kind'] == 'tooling':
            continue
        source_record(data.get(repo), repo)
        require(local_path(root, data[repo]['worktree']).is_dir(), repo + ' worktree missing')
        if lane:
            require(data[repo] == lane[repo], repo + ' differs from lane source checkpoint')
    reviews = data['shared_reviews']
    for review in reviews:
        require(isinstance(review, dict) and nonempty(review.get('file')) and
                nonempty(review.get('reason')) and nonempty(review.get('issue_url')) and
                review.get('status') in ('requested', 'approved', 'rejected'), 'Invalid shared review')
    covered = set(data['owned_files']) | {r['file'] for r in reviews}
    require(set(data['changed_files']) <= covered, 'Changed files lack ownership or shared review')
    evidence = data.get('evidence')
    require(isinstance(evidence, dict) and evidence, 'Evidence map required')
    paths = {}
    for key, item in evidence.items():
        require(isinstance(item, dict), 'Invalid evidence: ' + key)
        path = local_path(root, item.get('path'))
        require(path.is_file(), 'Evidence file missing: ' + str(path))
        require(item.get('sha256') == digest(path), 'Evidence hash mismatch: ' + key)
        paths[key] = path

    def refs(items, label):
        require(isinstance(items, list) and items and all(isinstance(k, str) and k in paths for k in items),
                label + ': evidence references required')

    for item in data['tests']:
        require(isinstance(item, dict) and nonempty(item.get('command')) and
                type(item.get('exit_code')) is int, 'Test command and exit code required')
        refs(item.get('evidence'), 'test')
    require(all(nonempty(item) for item in data['remaining_work']), 'Remaining work must contain descriptions')
    for item in data['source_mapping']:
        require(isinstance(item, dict) and nonempty(item.get('description')), 'Source mapping required')
        refs(item.get('evidence'), 'source mapping')
    for item in reviews:
        refs(item.get('evidence'), 'shared review')

    gates = data.get('gates')
    require(isinstance(gates, dict) and set(gates) == set(GATES), 'Exactly six arena gates required')
    for name, gate in gates.items():
        require(isinstance(gate, dict) and gate.get('status') in RESULTS and nonempty(gate.get('detail')),
                'Invalid gate: ' + name)
        require(gate.get('method') in ('natural', 'injected', 'source', 'unobserved'), 'Gate method required')
        if gate['status'] in ('PASS', 'FAIL', 'N/A'):
            refs(gate.get('evidence'), name)
        if gate['status'] == 'N/A':
            require(gate['method'] == 'source', 'N/A must be source-backed')
        if gate['status'] == 'PASS':
            require(gate['method'] in ('natural', 'injected'), 'PASS needs observed method')
            from .fixture_health import require_uninterrupted
            require_uninterrupted(paths, gate['evidence'], name)
    criteria = data.get('slice_acceptance')
    require(isinstance(criteria, list) and criteria, 'Slice acceptance required')
    for item in criteria:
        require(isinstance(item, dict) and nonempty(item.get('criterion')) and item.get('status') in RESULTS,
                'Invalid slice criterion')
        refs(item.get('evidence'), 'slice criterion')
        if item['status'] == 'PASS':
            from .fixture_health import require_uninterrupted
            require_uninterrupted(paths, item['evidence'], 'slice criterion')
    if lane:
        require([i['criterion'] for i in criteria] == lane['acceptance'], 'Slice criteria differ from claim')

    adoption = data.get('fixture_adoption')
    require(isinstance(adoption, dict), 'Fixture adoption required')
    if data['kind'] == 'runtime' and lane and lane.get('fixture_captain_guard_required'):
        safety = adoption.get('captain_safety', {})
        require(safety.get('policy') in ('unprotected', 'protected_observation'),
                'Captain safety adoption required for this lane (#632)')
        refs(safety.get('evidence'), 'captain safety source, negative test and fresh run')
        if safety['policy'] == 'protected_observation':
            require(gates['attacks_receivers']['status'] != 'PASS',
                    'Protected observation cannot substantiate attack/receiver acceptance')
    if data['kind'] == 'tooling':
        require(adoption.get('status') == 'N/A' and nonempty(adoption.get('reason')),
                'Tooling requires explicit fixture non-applicability')
        require(all(g['status'] != 'PASS' for g in gates.values()), 'Tooling cannot claim runtime PASS')
    else:
        require(adoption.get('status') == 'PASS', 'Runtime handoff requires observed fixture adoption')
        for key in ('window', 'live_squad', 'active_gameplay', 'no_immediate_extinction',
                    'fresh_arena', 'overlay_source', 'window_source', 'assets_config'):
            refs(adoption.get(key), 'fixture adoption ' + key)
        build = data.get('build')
        require(isinstance(build, dict) and nonempty(build.get('command')) and
                build.get('exit_code') == 0, 'Successful build record required')
        require(local_path(root, build.get('directory')).is_dir(), 'Build directory missing')
        require(local_path(root, build['directory']).is_relative_to(Path(root).resolve() / 'output'),
                'Lane build must be under output/')
        refs(build.get('evidence'), 'build')
        refs(build.get('dry_run'), 'dry run')
        require(build.get('dry_run_exit_code') == 0 and any(
            'ninja: no work to do.' in paths[k].read_text(encoding='utf-8', errors='replace')
            for k in build['dry_run']), 'No-work Ninja dry run required')
        exe = build.get('executable')
        refs([exe], 'executable')
        require(build.get('replacement_main') in (True, False), 'replacement_main boolean required')
        if build['replacement_main']:
            refs([build.get('provenance')], 'provenance')
            provenance = json.loads(paths[build['provenance']].read_text(encoding='utf-8'))
            require(provenance.get('status') == 'built', 'Fixture provenance is not built')
            require(provenance.get('expected_native_head') == data['native']['head'] and
                    provenance.get('observed_source', {}).get('head') == data['native']['head'] and
                    provenance.get('observed_source', {}).get('status') == data['native']['dirty'],
                    'Fixture provenance native identity mismatch')
            require(local_path(root, provenance.get('source')) == local_path(root, data['native']['worktree']) and
                    local_path(root, provenance.get('build')) == local_path(root, build['directory']),
                    'Fixture provenance source/build mismatch')
            artifact = provenance.get('artifacts', {}).get(str(paths[exe]), {})
            require(artifact.get('sha256') == evidence[exe]['sha256'], 'Fixture artifact hash mismatch')
    return {'reviewable': True, 'gameplay_accepted': False,
            'slice_passed': all(c['status'] in ('PASS', 'N/A') for c in criteria) and
                            all(t['exit_code'] == 0 for t in data['tests']),
            'pending_reviews': [r['file'] for r in reviews if r['status'] != 'approved'],
            'outstanding_gates': [k for k, g in gates.items() if g['status'] not in ('PASS', 'N/A')]}


def validate_review(root, data, lane=None):
    """Review of existing evidence is not a fresh runtime or implementation handoff."""
    require(data.get('schema') == 1 and data.get('fresh_runtime') is False, 'Review must explicitly exclude a new runtime claim')
    require(nonempty(data.get('conclusion')), 'Review conclusion required')
    for name in ('lane', 'owner', 'task_id'):
        require(nonempty(data.get(name)), name + ' required')
        if lane: require(data[name] == lane[name], 'Review identity mismatch: ' + name)
    for name in ('issue', 'generation'):
        require(type(data.get(name)) is int and data[name] > 0, name + ' required')
        if lane: require(data[name] == lane[name], 'Review identity mismatch: ' + name)
    require(data.get('evidence'), 'Review evidence required')
    for item in data['evidence'].values():
        path = local_path(root, item.get('path'))
        require(path.is_file() and item.get('sha256') == digest(path), 'Review evidence missing or changed')
    require(not data.get('gates') and not data.get('build'), 'Review cannot declare new gate/build acceptance')
    return dict(reviewable=True, gameplay_accepted=False, slice_passed=True,
                pending_reviews=[], outstanding_gates=list(GATES), kind='review')
