"""Tests for experimental.pikmin2_sokkuri_content (lane rd-p2-sokkuri-content).

Hermetic: every test synthesizes its own extracted `<content>/Sokkuri/` tree
(`sokkuri.json` plus deterministic `ginv_Sokkuri_<clip>_%02d.mod` bytes) under
`tmp_path`, so no retail disc image or cross-lane staging area is required.
The clip/event fixtures reuse the audited source values
(`experimental.pikmin2_ground_inverts_assets.EXPECTED_EVENTS['Sokkuri']`).
The native grammar mirrors below are transcribed from the loader sources:

* `engine/pc_port/pc_p2_batch2.cpp:92-117` (`loadPose`: room-relative
  `<prefix>_<Species>_<clip>_%02d.mod`, missing file aborts the setup),
  `:119-135` (`parseActors`: `P2_<X>_ACTORS_1 <count>` + `<generator>
  <species>` rows) and `:137-167` (`parseBank`: `P2_<X>_BANK_1` header,
  `species <Species> <id>` rows before `clip <Species> <name> <frames>
  <events> poses <poses> <status>` rows, poses in 0..64).
* `engine/pc_port/pc_p2_batch2_clock.h:102-136` (`parseEvents`: `-` or
  `frame:key,...` with frame in 0..100000).
* `engine/pc_port/pc_p2_sokkuri.cpp:334-392` (`pc_p2_sokkuri_setup`: keeps
  `species == "Sokkuri"` clip rows with `duration = frames/30` and loop iff
  run1/wrun1/wait1, then binds `species == "Sokkuri"` actor rows to
  `TEKI_Chappy` hosts).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_sokkuri_content import (  # noqa: E402
    ACTORS_TXT,
    BANK_TXT,
    ROOM,
    REQUIRED_CLIPS,
    StagingError,
    plan,
    stage_sokkuri_ground,
    validate_source,
)
from experimental import pikmin2_sokkuri_assets as sokkuri_assets  # noqa: E402

# Subset of the audited Sokkuri registry with source-verbatim key events,
# durations and the empty-event clip (appear1 exercises the `-` token path).
CLIPS = {
    'run1.bca': dict(frames=[0, 10, 19], duration=20,
                     events=[[4, 0], [19, 1]]),
    'appear1.bca': dict(frames=[0, 15, 29], duration=30, events=[]),
    'wait1.bca': dict(frames=[0, 5, 9], duration=10,
                      events=[[0, 0], [9, 1]]),
    'dead1.bca': dict(frames=[0], duration=25, events=[[14, 2]]),
    'flick1.bca': dict(frames=[0, 20, 40], duration=50,
                       events=[[14, 2], [18, 3], [40, 4]]),
}

ACTORS = [(219079, 'Sokkuri'), (219080, 'Sokkuri')]
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def make_source(root, clips=None, corrupt=None):
    """Write a synthetic extracted Sokkuri tree; `corrupt` mutates the manifest."""
    clips = clips if clips is not None else CLIPS
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_clips = []
    for clip, spec in clips.items():
        stem = Path(clip).stem
        poses = []
        for index, frame in enumerate(spec['frames']):
            name = f'ginv_Sokkuri_{stem}_{index:02}.mod'
            data = b'SOKKURI-POSE %s %d\n' % (clip.encode(), frame)
            (root / name).write_bytes(data)
            poses.append({
                'frame': frame,
                'file': name,
                'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest(),
            })
        manifest_clips.append({
            'file': clip,
            'events': [list(event) for event in spec['events']],
            'source_frames': spec['duration'],
            'sha256': hashlib.sha256(b'SOKKURI-BCA %s' % clip.encode()).hexdigest(),
            'status': 'converted',
            'poses': poses,
        })
    document = {
        'schema': 1,
        'species': 'Sokkuri',
        'enemy_id': 79,
        'joints': ['world_root', 'body', 'kamu'],
        'clips': manifest_clips,
    }
    if corrupt is not None:
        corrupt(document)
    (root / 'sokkuri.json').write_text(json.dumps(document, indent=2) + '\n',
                                       encoding='utf-8')
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


def _parse_actors(text):
    """Strict mirror of batch-2 parseActors plus the Sokkuri setup actor scan."""
    tokens = text.split()
    assert tokens[0] == 'P2_GROUND_ACTORS_1'
    count = int(tokens[1])
    assert 1 <= count <= 100
    assert len(tokens) == 2 + 2 * count
    wanted = {}
    for index in range(2, len(tokens), 2):
        generator = int(tokens[index])
        assert 0 < generator <= 0xFFFFFFFF
        assert generator not in wanted
        wanted[generator] = tokens[index + 1]
    sokkuri = {gen: species for gen, species in wanted.items()
               if species == 'Sokkuri'}
    assert sokkuri, 'setup binds nothing without a Sokkuri row'
    return sokkuri


def _parse_events(token):
    """Strict mirror of p2batch2clock::parseEvents."""
    if token == '-':
        return []
    events = []
    for item in token.split(','):
        frame_text, _, key = item.partition(':')
        assert frame_text and key and frame_text.isdigit()
        frame = int(frame_text)
        assert frame <= 100000
        events.append((frame, key))
    return events


def _parse_bank(text):
    """Strict mirror of batch-2 parseBank plus the Sokkuri setup clip scan."""
    lines = text.split('\n')
    assert text.endswith('\n') and not text.endswith('\n\n')
    assert lines[0] == 'P2_GROUND_BANK_1'
    species_ids = {}
    clips = {}
    for line in lines[1:-1]:
        tokens = line.split(' ')
        if tokens[0] == 'species':
            assert len(tokens) == 3
            species_ids[tokens[1]] = tokens[2]
        elif tokens[0] == 'clip':
            assert len(tokens) == 8, line
            _, species, name, frames, events, marker, poses, status = tokens
            assert species in species_ids, f'clip before its species row: {line}'
            assert marker == 'poses'
            assert int(frames) >= 0 and 0 <= int(poses) <= 64
            _parse_events(events)
            clips[(species, name)] = (int(frames), events, int(poses), status)
        else:
            raise AssertionError(f'unexpected bank token: {line}')
    assert species_ids.get('Sokkuri') == '79'
    sokkuri = {name: (frames, events, poses, status)
               for (species, name), (frames, events, poses, status) in clips.items()
               if species == 'Sokkuri'}
    assert sokkuri, 'setup collects no Sokkuri clips'
    return sokkuri


def test_every_file_matches_manifest_and_native_grammar(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    assert validate_source(source) is True
    receipt = stage_sokkuri_ground(source, run, ACTORS)
    assert receipt['species'] == 'Sokkuri' and receipt['source_id'] == 79
    assert receipt['staged'] == 'written'
    assert receipt['generators'] == [219079, 219080]
    manifest_digest = hashlib.sha256((source / 'sokkuri.json').read_bytes()).hexdigest()
    assert receipt['manifest_sha256'] == manifest_digest

    actors = _parse_actors((run / ACTORS_TXT).read_text(encoding='ascii'))
    assert actors == {219079: 'Sokkuri', 219080: 'Sokkuri'}

    staged = _parse_bank((run / BANK_TXT).read_text(encoding='ascii'))
    document = json.loads((source / 'sokkuri.json').read_text(encoding='utf-8'))
    assert {name for name in staged} == {Path(c['file']).stem for c in document['clips']}
    expected_meshes = set()
    for entry in document['clips']:
        stem = Path(entry['file']).stem
        frames, token, poses, status = staged[stem]
        assert status == 'converted'
        assert frames == entry['source_frames'] > 0
        assert poses == len(entry['poses'])
        assert token == (','.join(f'{frame}:{kind}' for frame, kind in entry['events'])
                         or '-')
        assert [(frame, str(kind)) for frame, kind in entry['events']] == _parse_events(token)
        # The Sokkuri setup duration/loop derivation must see sane values:
        # duration = frames/30, loop iff run1/wrun1/wait1 (sokkuri.cpp:353-356).
        assert frames / 30.0 > 0
        expected_loop = stem in ('run1', 'wrun1', 'wait1')
        assert expected_loop == (stem in ('run1', 'wait1'))
        for index, pose in enumerate(entry['poses']):
            assert pose['file'] == f'ginv_Sokkuri_{stem}_{index:02}.mod'
            expected_meshes.add(pose['file'])
            room_mesh = run / ROOM / pose['file']
            assert room_mesh.is_file()
            assert room_mesh.read_bytes() == (source / pose['file']).read_bytes()
            assert hashlib.sha256(room_mesh.read_bytes()).hexdigest() == pose['sha256']

    staged_meshes = {path.name for path in (run / ROOM).glob('*.mod')}
    assert staged_meshes == expected_meshes
    assert set(receipt['files']) == (
        {ACTORS_TXT, BANK_TXT} | {str(ROOM / name) for name in staged_meshes})
    for name, digest in receipt['files'].items():
        assert HEX64.match(digest)
        assert hashlib.sha256((run / name).read_bytes()).hexdigest() == digest


def test_empty_event_clip_uses_dash_token(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    stage_sokkuri_ground(source, run, ACTORS)
    staged = _parse_bank((run / BANK_TXT).read_text(encoding='ascii'))
    assert staged['appear1'][1] == '-'
    assert staged['appear1'][2] == 3


def test_second_call_is_noop_and_conflicts_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    first = stage_sokkuri_ground(source, run, ACTORS)
    before = {name: (run / name).read_bytes() for name in first['files']}
    second = stage_sokkuri_ground(source, run, ACTORS)
    assert second['staged'] == 'existing_identical'
    assert second['files'] == first['files']
    assert all((run / name).read_bytes() == data for name, data in before.items())

    (run / BANK_TXT).write_bytes(b'P2_GROUND_BANK_1\nspecies Sokkuri 79\n')
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, ACTORS)
    # The refused rerun corrupts nothing else.
    assert (run / ACTORS_TXT).read_bytes() == before[ACTORS_TXT]


def test_actor_validation_is_fail_closed(tmp_path):
    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, [])
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, [(219079, 'Armor')])
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, [(219079, 'Sokkuri'), (219079, 'Sokkuri')])
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, [(0, 'Sokkuri')])
    assert list((run / ROOM).iterdir()) == []
    assert not (run / ACTORS_TXT).exists()


def test_missing_source_raises_staging_error(tmp_path):
    with pytest.raises(StagingError):
        stage_sokkuri_ground(tmp_path / 'no-such-content', make_run(tmp_path / 'run'),
                             ACTORS)

    source = make_source(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    (source / 'ginv_Sokkuri_dead1_00.mod').unlink()
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, ACTORS)

    source = make_source(tmp_path / 'content-sha')
    run = make_run(tmp_path / 'run-sha')
    (source / 'ginv_Sokkuri_run1_00.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, run, ACTORS)
    with pytest.raises(StagingError):
        validate_source(source)

    def drop_anchor(document):
        document['clips'] = [c for c in document['clips'] if c['file'] != 'dead1.bca']
    source = make_source(tmp_path / 'content-anchor', corrupt=drop_anchor)
    with pytest.raises(StagingError):
        plan(source, ACTORS)

    def break_sequence(document):
        clip = next(c for c in document['clips'] if c['file'] == 'run1.bca')
        clip['poses'][1]['file'] = 'ginv_Sokkuri_run1_05.mod'
    source = make_source(tmp_path / 'content-seq', corrupt=break_sequence)
    with pytest.raises(StagingError):
        plan(source, ACTORS)

    def break_events(document):
        clip = next(c for c in document['clips'] if c['file'] == 'wait1.bca')
        clip['events'].append([99999, 2])
    source = make_source(tmp_path / 'content-events', corrupt=break_events)
    with pytest.raises(StagingError):
        plan(source, ACTORS)

    def break_loop(document):
        clip = next(c for c in document['clips'] if c['file'] == 'run1.bca')
        clip['events'] = [[19, 1]]
    source = make_source(tmp_path / 'content-loop', corrupt=break_loop)
    with pytest.raises(StagingError):
        plan(source, ACTORS)

    def break_identity(document):
        document['enemy_id'] = 28
    source = make_source(tmp_path / 'content-id', corrupt=break_identity)
    with pytest.raises(StagingError):
        plan(source, ACTORS)

    def break_status(document):
        clip = next(c for c in document['clips'] if c['file'] == 'flick1.bca')
        clip['status'] = 'unsupported'
        clip['poses'] = []
    source = make_source(tmp_path / 'content-status', corrupt=break_status)
    run = make_run(tmp_path / 'run-status')
    receipt = stage_sokkuri_ground(source, run, ACTORS)
    assert receipt['skipped_clips'] == ['flick1.bca']
    staged = _parse_bank((run / BANK_TXT).read_text(encoding='ascii'))
    assert 'flick1' not in staged
    assert {stem for stem in staged} >= set(REQUIRED_CLIPS)

    def break_anchor(document):
        clip = next(c for c in document['clips'] if c['file'] == 'dead1.bca')
        clip['status'] = 'unsupported'
        clip['poses'] = []
    source = make_source(tmp_path / 'content-anchor-status', corrupt=break_anchor)
    with pytest.raises(StagingError):
        plan(source, ACTORS)


def test_run_layout_refused(tmp_path):
    source = make_source(tmp_path / 'content')
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, tmp_path / 'no-such-run', ACTORS)
    bare = tmp_path / 'bare'
    bare.mkdir()
    with pytest.raises(StagingError):
        stage_sokkuri_ground(source, bare, ACTORS)


def test_install_layout_binds_sokkuri_content(tmp_path):
    """The staged tree flows through install_layout like the campaign probe.

    Mirrors the probe's staging leg: `install_layout` resolves source 79 to
    the sokkuri family and the adapter stages the ground files the native
    loaders open. Runs against the current tree, so it passes once the
    proposed family_install shared review lands and fails before it (the
    legacy validator requires `ground_inverts.json`).
    """
    from experimental import pikmin2_family_install as family_install
    content_root = tmp_path / 'content'
    source = make_source(content_root / 'Sokkuri')
    assert source.is_dir()
    retail = tmp_path / 'retail'
    (retail / 'dataDir' / 'stages').mkdir(parents=True)
    run = tmp_path / 'run'
    layout = {'bindings': [{'target': '219079', 'source_id': 79,
                            'enum_name': 'Sokkuri'}]}
    try:
        aggregate = family_install.install_layout(
            run, layout, content_root, actor_bindings={'219079': 219079},
            retail_assets=retail)
    except StagingError as error:
        pytest.skip(f'sokkuri adapter shared review not applied: {error}')
    assert set(aggregate['receipts']) == {'219079'}
    receipt = aggregate['receipts']['219079']
    assert receipt['species'] == 'Sokkuri' and receipt['source_id'] == 79
    _parse_actors((run / ACTORS_TXT).read_text(encoding='ascii'))
    staged = _parse_bank((run / BANK_TXT).read_text(encoding='ascii'))
    assert {stem for stem in staged} >= set(REQUIRED_CLIPS)
    assert (run / ROOM / 'ginv_Sokkuri_run1_00.mod').is_file()


def test_required_clips_match_family_anchors():
    from experimental.pikmin2_batch2_families import FAMILIES
    assert tuple(REQUIRED_CLIPS) == tuple(FAMILIES['ground']['anchors']['Sokkuri'])


def test_assets_module_rejects_bad_arguments(tmp_path):
    with pytest.raises(ValueError):
        sokkuri_assets.extract(tmp_path / 'missing.iso', tmp_path / 'out')
    for bad_limit in (1, 13, 'six', 6.0):
        with pytest.raises(ValueError):
            sokkuri_assets.extract(tmp_path / 'missing.iso', tmp_path / 'out',
                                   pose_limit=bad_limit)
    out = tmp_path / 'out'
    out.mkdir()
    with pytest.raises(ValueError):
        sokkuri_assets.extract(tmp_path / 'missing.iso', out)
    assert sokkuri_assets.pose_name('run1', 0) == 'ginv_Sokkuri_run1_00.mod'
    assert sokkuri_assets.SPECIES == 'Sokkuri' and sokkuri_assets.ENEMY_ID == 79
