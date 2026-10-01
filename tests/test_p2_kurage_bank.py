"""Jellyfloat sampled pose bank (#972): profile text and fail-closed staging.

Hermetic: synthetic manifest + pose bytes, no ISO.  The real-extraction check
runs only when a bank-bearing content tree is staged under output/.
"""
import hashlib
import json
from pathlib import Path

import pytest

from experimental.pikmin2_kurage_bank import PROFILE_MAGIC, POLICY, profile_text, staged_bank
from experimental.pikmin2_kurage_content import ROOM, plan, stage_kurage_host
from experimental.pikmin2_staging import StagingError

from tests.test_p2_kurage_content import NATIVE_NAMES, make_kurage_source, make_run


def _bank(source, clips=(('wait', 35, 3), ('attack', 120, 4))):
    rows = []
    for name, duration, count in clips:
        frames = [round(i * (duration - 1) / (count - 1)) for i in range(count)]
        poses = []
        for index, frame in enumerate(frames):
            data = f'pose-{name}-{index}'.encode()
            file = f'{name}_{index:02}.mod'
            (source / file).write_bytes(data)
            poses.append(dict(frame=frame, file=file, bytes=len(data),
                              sha256=hashlib.sha256(data).hexdigest(),
                              proom=[0.0, 10.0 + index, 0.5]))
        rows.append(dict(name=name, status='converted', source_frames=duration, poses=poses))
    return dict(policy=POLICY, pose_limit=24, total_bytes=0, clips=rows)


def _with_bank(tmp_path, **kwargs):
    source = make_kurage_source(tmp_path)
    document = json.loads((source / 'kurage.json').read_text(encoding='utf-8'))
    document['bank'] = _bank(source, **kwargs)
    (source / 'kurage.json').write_text(json.dumps(document), encoding='utf-8')
    return source, document


def test_profile_lists_frames_and_proom_rows():
    bank = _bank(Path('.'), clips=()) | {}
    bank['clips'] = [dict(name='wait', status='converted', source_frames=35,
                          poses=[dict(frame=0, proom=[0, 11.2, 0.7]),
                                 dict(frame=17, proom=[0, 12, 0]),
                                 dict(frame=34, proom=[0, 11.2, 0.7])]),
                     dict(name='bad', status='unsupported', source_frames=None, poses=[])]
    lines = profile_text(bank).splitlines()
    assert lines[0] == PROFILE_MAGIC
    assert len(lines) == 2
    tokens = lines[1].split()
    assert tokens[:6] == ['wait', '3', '35', '0', '17', '34']
    assert len(tokens) == 6 + 9


def test_profile_rejects_bad_frames():
    bank = dict(clips=[dict(name='wait', status='converted', source_frames=35,
                            poses=[dict(frame=0, proom=[0, 0, 0]), dict(frame=20, proom=[0, 0, 0])])])
    with pytest.raises(ValueError):
        profile_text(bank)


def test_bank_is_staged_with_the_profile(tmp_path):
    source, _ = _with_bank(tmp_path)
    files, _ = plan(source)
    assert str(ROOM / 'kurage_wait_00.mod') in files
    assert str(ROOM / 'kurage_attack_03.mod') in files
    assert files['p2-kurage-animation.txt'].startswith(PROFILE_MAGIC.encode())
    # the static fallback visuals are still staged
    for name in NATIVE_NAMES:
        assert str(ROOM / f'kurage_{name}.mod') in files
    run = make_run(tmp_path)
    assert stage_kurage_host(source, run)['staged'] == 'written'
    assert (run / 'p2-kurage-animation.txt').is_file()
    assert stage_kurage_host(source, run)['staged'] == 'existing_identical'


def test_manifest_without_a_bank_stages_only_the_static_visuals(tmp_path):
    source = make_kurage_source(tmp_path)
    files, _ = plan(source)
    assert 'p2-kurage-animation.txt' not in files
    assert len(files) == len(NATIVE_NAMES)


def test_bank_hash_mismatch_refused(tmp_path):
    source, _ = _with_bank(tmp_path)
    (source / 'wait_01.mod').write_bytes(b'tampered')
    with pytest.raises(StagingError):
        plan(source)


def test_bank_pose_missing_refused(tmp_path):
    source, _ = _with_bank(tmp_path)
    (source / 'attack_02.mod').unlink()
    with pytest.raises(StagingError):
        plan(source)


def test_bank_wrong_policy_refused(tmp_path):
    source, document = _with_bank(tmp_path)
    document['bank']['policy'] = 'OTHER'
    with pytest.raises(StagingError):
        staged_bank(source, document, 'kurage_', 'p2-kurage-animation.txt')


REAL = Path(__file__).resolve().parents[2] / 'smooth-evidence' / 'jelly' / 'content'


@pytest.mark.skipif(not (REAL / 'Kurage' / 'kurage.json').exists(), reason='no extracted Jellyfloat bank')
def test_real_bank_profile_matches_the_static_proom_table():
    document = json.loads((REAL / 'Kurage' / 'kurage.json').read_text(encoding='utf-8'))
    wait = next(c for c in document['bank']['clips'] if c['name'] == 'wait')
    assert wait['poses'][0]['frame'] == 0 and wait['poses'][0]['proom'][1] == pytest.approx(11.2, abs=0.05)
    assert wait['poses'][-1]['frame'] == wait['source_frames'] - 1
