"""Governed Linux descriptors backed by collected local evidence; never local paths.

This is a delivery validator, not execution, remote authentication or gameplay
acceptance. Each supported suite must retain its existing phase/oracle contract.
"""
import hashlib
import json
import re
import posixpath
import subprocess
from pathlib import PurePosixPath
from functools import lru_cache
from .handoff import require, local_path, digest


def descriptor(value, prefix):
    require(isinstance(value, str) and '\\' not in value and ':' not in value and
            '\x00' not in value and str(PurePosixPath(value)) == value and
            '..' not in PurePosixPath(value).parts and
            PurePosixPath(value).is_relative_to(PurePosixPath(prefix)),
            'Invalid remote descriptor')
    return value


def git_bytes(root, record, *args):
    path = local_path(root, record['worktree'])
    result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=30)
    require(result.returncode == 0, 'Local source mapping unavailable')
    return result.stdout


@lru_cache(maxsize=16)
def committed_manifest(worktree, head):
    # Hash committed blobs, never Windows checkout bytes (which may be CRLF).
    listing = subprocess.run(['git', '-C', worktree, 'ls-tree', '-r', '-z', head],
                             capture_output=True, timeout=30)
    require(listing.returncode == 0, 'Committed tree unavailable')
    records = []
    symlinks = []
    for entry in listing.stdout.split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        mode, kind, oid = meta.split()
        require(kind == b'blob', 'Remote source mapping requires ordinary committed blobs')
        if mode == b'120000':
            symlinks.append((name.decode('utf-8'), oid))
        else:
            records.append((name.decode('utf-8'), oid))
    batch = subprocess.run(['git', '-C', worktree, 'cat-file', '--batch'],
                           input=b''.join(oid + b'\n' for _, oid in records),
                           capture_output=True, timeout=30)
    require(batch.returncode == 0, 'Committed blob mapping unavailable')
    position = 0
    result = {}
    for name, oid in records:
        end = batch.stdout.index(b'\n', position)
        actual, kind, size = batch.stdout[position:end].split()
        require(actual == oid and kind == b'blob', 'Committed blob identity mismatch')
        position = end + 1
        content = batch.stdout[position:position + int(size)]
        hashes = {hashlib.sha256(content).hexdigest()}
        # Git checkout may apply declared text EOL conversion. Binary bytes stay exact.
        if b'\x00' not in content:
            lf = content.replace(b'\r\n', b'\n')
            hashes.update((hashlib.sha256(lf).hexdigest(), hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest()))
        result[name] = hashes
        position += int(size) + 1
    require(position == len(batch.stdout), 'Committed blob closure mismatch')
    for name, oid in symlinks:
        link = subprocess.run(['git', '-C', worktree, 'cat-file', 'blob', oid.decode()], capture_output=True, timeout=30)
        require(link.returncode == 0, 'Committed symlink unavailable')
        target = link.stdout.decode('utf-8')
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
        if resolved in result:
            result[name] = result[resolved]
    return result


def validate_remote_runtime(root, data, paths, refs):
    remote = data['build'].get('remote')
    require(isinstance(remote, dict) and remote.get('schema') == 1,
            'Remote runtime descriptor schema required')
    require(set(remote) == {'schema', 'repository', 'run_id', 'attempt', 'request_id',
                           'controller_head', 'root_tree', 'native_tree', 'receipt',
                           'manifest', 'boundary', 'raw', 'native_deadline', 'outer_deadline'},
            'Exact remote runtime fields required')
    require(remote['repository'] == '4laric/game-build-ci', 'Governed repository required')
    require(type(remote['run_id']) is int and remote['run_id'] > 0 and
            type(remote['attempt']) is int and remote['attempt'] > 0 and
            re.fullmatch('[0-9a-f]{32}', remote['request_id']), 'Run identity required')
    require(re.fullmatch('[0-9a-f]{40}', remote['controller_head']), 'Controller commit required')
    # A suite-specific validator prevents invented phase requirements from a caller.
    require(remote['native_deadline'] == 60 and remote['outer_deadline'] == 300,
            'Reviewed runtime deadlines required')
    refs([remote['receipt'], remote['manifest'], remote['boundary']], 'Remote receipt and full collection')
    raw = remote['raw']
    require(isinstance(raw, dict) and raw, 'Collected raw closure required')
    refs(list(raw.values()), 'Remote raw closure')
    manifest = json.loads(paths[remote['manifest']].read_text(encoding='utf-8'))
    require(manifest['run_id'] == remote['run_id'] and
            manifest['request_id'] == remote['request_id'] and
            manifest['conclusion'] == 'success', 'Collection identity mismatch')
    boundary = json.loads(paths[remote['boundary']].read_text(encoding='utf-8'))
    require(boundary['run_id'] == remote['run_id'], 'Boundary run mismatch')
    entries = manifest['files'] + [dict(e, remote=e['path']) for e in boundary['files']]
    require(len(entries) == len(raw) and {x['name'] for x in entries} == set(raw),
            'Full raw collection must be retained')
    job = '/srv/game-ci/jobs/fixture-%d-%d' % (remote['run_id'], remote['attempt'])
    for entry in entries:
        name = entry['name']
        require('/' not in name and '\\' not in name and ':' not in name and name not in ('.', '..'),
                'Invalid collected file name')
        path = paths[raw[name]]
        require(path.stat().st_size == entry['bytes'] and digest(path) == entry['sha256'],
                'Raw collection hash/size mismatch')
        if 'remote' in entry:
            prefix = '/srv/game-ci/logs' if name == 'broker-cleanup.json' else job
            descriptor(entry['remote'], prefix)
    def load(name):
        require(name in raw, 'Missing raw receipt: ' + name)
        return json.loads(paths[raw[name]].read_text(encoding='utf-8'))
    result = json.loads(paths[remote['receipt']].read_text(encoding='utf-8'))
    require(result == load('job--result.json'), 'Build receipt differs from collected raw')
    require(result.get('schema') == 1 and result.get('platform') == 'Linux' and
            result.get('kind') == 'selected-target-runtime' and result.get('status') == 'passed' and
            result.get('gameplay_accepted') is False, 'Actual bounded Linux receipt required')
    require(result['run_id'] == str(remote['run_id']) and
            result['attempt'] == str(remote['attempt']) and
            result['request_id'] == remote['request_id'], 'Build run identity mismatch')
    actions = load('actions-run.json')
    require(actions['id'] == remote['run_id'] and actions['run_attempt'] == remote['attempt'] and
            actions['head_sha'] == remote['controller_head'] and actions['status'] == 'completed' and
            actions['conclusion'] == 'success' and actions['repository']['full_name'] == remote['repository'] and
            actions['path'] == '.github/workflows/fixtures.yml' and actions['event'] == 'workflow_dispatch' and
            remote['request_id'] in actions['display_title'], 'Actions provenance mismatch')
    for repo in ('root', 'native'):
        require(result[repo + '_sha'] == data[repo]['head'] and data[repo]['dirty'] == '',
                'Compiled source pin mismatch')
        tree = git_bytes(root, data[repo], 'rev-parse', data[repo]['head'] + '^{tree}').decode().strip()
        require(tree == remote[repo + '_tree'], 'Local committed tree mismatch')
        source_manifest = load('job--' + repo + '-source-manifest.json')
        require(digest(paths[raw['job--' + repo + '-source-manifest.json']]) ==
                result[repo + '_source_manifest_sha256'], 'Compiled source manifest mismatch')
        expected_manifest = committed_manifest(str(local_path(root, data[repo]['worktree'])), data[repo]['head'])
        require(set(source_manifest) == set(expected_manifest) and all(source_manifest[k] in expected_manifest[k] for k in source_manifest), 'Remote compiled tree content mismatch')
        selected = result['selected_source'] if repo == 'native' else result['canonical_root_guard']
        name = selected['path']
        require(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts and
                '\\' not in name and ':' not in name, 'Source key must be repository relative')
        blob = git_bytes(root, data[repo], 'show', data[repo]['head'] + ':' + name)
        require(hashlib.sha256(blob).hexdigest() == selected['sha256'] == source_manifest[name],
                'Selected source/guard local mapping mismatch')
    require(result['suite'] == 'white-carry-sdl-runtime' and
            result['selected_target'] == 'pikmin_ci_fixture_white_carry' and
            result['selected_source']['path'] == 'tools/p2_white_carry_runtime.cpp' and
            result['requested_source_sha256'] == result['selected_source']['sha256'],
            'Unsupported or mismatched governed suite')
    require(result['configuration']['netplay'] == 'OFF' and
            result['configuration']['netplay_declared'] is True, 'Netplay profile mismatch')
    require(result['job_directory'] == job and data['build']['directory'] == job + '/build',
            'Remote build descriptor mismatch')
    executable = result['executable']
    require(executable['path'] == job + '/build/fixtures/' + result['selected_target'] and
            re.fullmatch('[0-9a-f]{64}', executable['sha256']) and executable['bytes'] > 0 and
            data['build']['executable'] == executable and data['build']['replacement_main'] is True,
            'Actual remote executable descriptor required')
    descriptor(executable['path'], job + '/build')
    runtime = result['white_carry_runtime']
    require(runtime['native_deadline'] == 60 and runtime['outer_deadline'] == 300 and
            runtime['human_launched'] is False and runtime['gameplay_accepted'] is False,
            'Bounded runtime qualifications required')
    phases = runtime['phases']
    require([p['mode'] for p in phases] == ['ready', 'forced-down', 'paused-down', 'positive'],
            'Exact initialized phase set required')
    admission = result['admission_proof']
    require(admission['admitted'] is True and admission['job'] == job and
            admission['exe'] == executable['path'] and admission['exe_sha256'] == executable['sha256'] and
            admission['guard_sha256'] == result['canonical_root_guard']['sha256'] and
            admission['target'] == result['selected_target'] and
            admission['controller_sha256'] == result['controller_sha256'], 'Admission binding mismatch')
    expected_pins = dict(GITHUB_RUN_ID=str(remote['run_id']), GITHUB_RUN_ATTEMPT=str(remote['attempt']),
                         FIXTURE_REQUEST_ID=remote['request_id'], FIXTURE_SUITE=result['suite'],
                         FIXTURE_SOURCE_SHA256=result['requested_source_sha256'],
                         PIKMIN_SHA=data['root']['head'], NATIVE_SHA=data['native']['head'])
    require(admission['pins'] == expected_pins, 'Admission source identity mismatch')
    for phase in phases:
        directory = descriptor(phase['directory'], job + '/root/output/white-carry')
        def phase_load(name):
            key = directory[len(job) + 1:].replace('/', '--') + '--' + name
            require(key in raw and digest(paths[raw[key]]) == phase['evidence_sha256'][name],
                    'Phase raw evidence mismatch')
            return load(key)
        for name, sha in phase['evidence_sha256'].items():
            key = directory[len(job) + 1:].replace('/', '--') + '--' + name
            require(key in raw and digest(paths[raw[key]]) == sha, 'Incomplete phase evidence')
        run = phase_load('run-result.json')
        expected = 86 if phase['mode'] in ('forced-down', 'paused-down') else 0
        require(run['exit_code'] == phase['native_exit'] == expected and phase['driver_exit'] == 0 and
                run['timeout_seconds'] == 60 and run['timed_out'] is False and
                0 <= run['elapsed_seconds'] <= 60 and run['pid'] == phase['pid'] ==
                run['owned_process_group'] == phase['owned_process_group'], 'Phase exit/deadline mismatch')
        require(run['argv'] == [executable['path'], '--experimental-pikmin2-room'], 'Phase executable mismatch')
        proof = phase_load('admission.json')
        require(proof['pins'] == expected_pins and proof['exe_sha256'] == executable['sha256'] and
                proof['admitted'] is True and proof['session'] == directory,
                'Phase admission mismatch')
        require(proof['target'] == result['selected_target'] and proof['guard_sha256'] == result['canonical_root_guard']['sha256'] and proof['controller_sha256'] == result['controller_sha256'] and proof['job'] == job and proof['unit'] == admission['unit'], 'Phase compiled profile mismatch')
        inputs = phase_load('run-inputs.json')
        require(inputs['exe'] == executable['path'] and inputs['exe_sha256'] == executable['sha256'] and
                inputs['cwd'] == directory, 'Phase input mismatch')
        cleanup = phase['cleanup_probe']
        require(cleanup['outcome'] == 'ESRCH' and cleanup['pid'] == phase['pid'] and
                cleanup['process_group'] == phase['pid'], 'Owned phase reaping required')
    positive = phases[-1]
    oracle = positive['oracle']
    require(oracle['slice_passed'] is True and oracle['gameplay_accepted'] is False and
            oracle['full_campaign'] is False, 'Bounded oracle qualifications required')
    stage = load(positive['directory'][len(job)+1:].replace('/', '--') + '--staging.json')
    require(stage['initial_pikmin'] == 20, 'Twenty body staging baseline required')
    log_key = positive['directory'][len(job)+1:].replace('/', '--') + '--native.log'
    log = paths[raw[log_key]].read_text(encoding='utf-8', errors='replace')
    require('960x540' in log and 'centered' in log and 'P2_WHITE_CARRY_PASS' in log,
            'Observed window and actual positive marker required')
    cleanup = load('broker-cleanup.json')
    require(cleanup['unit'] == admission['unit'] and cleanup['exit_code'] == 0 and
            cleanup['cleanup']['ActiveState'] == 'inactive' and
            cleanup['cleanup']['ControlGroup'] == '', 'Actual terminal cgroup cleanup required')
    require(result['no_work'] is True and 'ninja: no work to do.' in
            paths[raw['job--no-work.log']].read_text(encoding='utf-8'), 'Actual no-work build required')
    require(data['remaining_work'], 'Remote delivery must retain incomplete gameplay scope')
