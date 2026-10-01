"""Man-at-Legs (Houdai, 66) sampled joint rig: sampling contract, text format and the disc bake (#1012)."""
from pathlib import Path

import pytest

import experimental.pikmin2_houdai_rig as rig

ISO = Path(r'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso')


def ident(tx=0.0, ty=0.0, tz=0.0):
    return [[1, 0, 0, tx], [0, 1, 0, ty], [0, 0, 1, tz]]


@pytest.mark.parametrize('clip,duration', [('landing', 230), ('wait', 40), ('flick', 85), ('attack', 70), ('dead', 140)])
def test_sample_frames_cover_ends_keys_and_the_24_pose_floor(clip, duration):
    frames = rig.sample_frame_list(clip, duration)
    assert frames[0] == 0 and frames[-1] == duration - 1
    assert all(b > a for a, b in zip(frames, frames[1:]))
    assert set(rig.KEY_FRAMES[clip]) <= set(frames)  # every key the source FSM reads is a sample
    assert len(frames) >= min(rig.MIN_POSES, duration)
    assert len(frames) <= rig.POSE_LIMIT_MAX + len(rig.KEY_FRAMES[clip]) + 2


def test_short_clip_keeps_every_frame():
    assert rig.sample_frame_list('wait', 40) == list(range(40))


@pytest.mark.parametrize('duration,limit', [(1, 48), (230, 1), (230, 65)])
def test_sample_frames_reject_bad_inputs(duration, limit):
    with pytest.raises(ValueError):
        rig.sample_frame_list('landing', duration, limit)


def synthetic(count=3):
    names = ['kosi', 'body', 'gun'][:count]
    parents = [-1, 0, 1][:count]
    nodes = [dict(id='none', code='____', radius=50.0, joint=0, offset=[0.0, 0.0, 0.0], parent=None, attribute=0),
             dict(id='tama', code='st__', radius=30.0, joint=0, offset=[5.0, 0.0, 0.0], parent=0, attribute=0)]
    rows = []
    for clip in rig.CLIPS:
        frames = [0, 4, 9]
        samples = [[ident(0, 10 * k, 0) for _ in range(count)] for k in range(3)]
        rows.append((clip, 10, frames, samples))
    return names, parents, nodes, rows


def test_text_round_trip():
    names, parents, nodes, rows = synthetic()
    text = rig.rig_text(names, parents, nodes, rows)
    assert text.splitlines()[0] == rig.HEADER and text.endswith('end\n')
    data = rig.parse(text)
    assert data['names'] == names and data['parents'] == parents
    assert [c['id'] for c in data['coll']] == ['none', 'tama'] and data['coll'][0]['parent'] == -1
    assert list(data['clips']) == list(rig.CLIPS)
    wait = data['clips']['wait']
    assert wait['frames'] == [0, 4, 9] and wait['duration'] == 10 and len(wait['samples']) == 3
    assert wait['samples'][2][7] == 20.0  # joint 0 translation y of sample 2 (row 1, column 3)


@pytest.mark.parametrize('mutate', [
    lambda t: t.replace(rig.HEADER, 'P2_HOUDAI_RIG_2', 1),
    lambda t: t.replace('\nend\n', '\n'),
    lambda t: t.replace('frames 0 4 9', 'frames 0 4 4', 1),
    lambda t: t.replace('frames 0 4 9', 'frames 1 4 9', 1),
])
def test_parse_rejects_malformed_text(mutate):
    names, parents, nodes, rows = synthetic()
    with pytest.raises(ValueError):
        rig.parse(mutate(rig.rig_text(names, parents, nodes, rows)))


def test_rig_text_rejects_bad_frames_and_joint_names():
    names, parents, nodes, rows = synthetic()
    bad = [(c, d, [1, 4, 9], s) for c, d, _, s in rows]
    with pytest.raises(ValueError):
        rig.rig_text(names, parents, nodes, bad)
    with pytest.raises(ValueError):
        rig.rig_text(['a b', 'body', 'gun'], parents, nodes, rows)


@pytest.mark.skipif(not ISO.is_file(), reason='needs the US GPVE01 disc')
def test_disc_bake_meets_the_admission_pose_bar():
    index = rig.disc_files(ISO)
    with ISO.open('rb') as disc:
        def read(path):
            at, size = index[path]
            disc.seek(at)
            return disc.read(size)
        model = rig.archive_files(read('enemy/data/Houdai/model.szs'))['enemy.bmd']
        motions = rig.archive_files(read('enemy/data/Houdai/anim.szs'))
        coll = rig.archive_files(read('enemy/parm/enemyParms.szs'))['houdai/enemycoll.txt']
    text, report = rig.bake(model, motions, coll)
    assert report['joints'] == 22 and report['collision_nodes'] == 2
    assert report['min_poses'] >= rig.MIN_POSES
    assert {c: v['source_frames'] for c, v in report['clips'].items()} == {
        'landing': 230, 'wait': 40, 'flick': 85, 'attack': 70, 'dead': 140}
    data = rig.parse(text)
    names = data['names']
    assert names[0] == 'kosi' and names[4] == 'tamajnt' and names[5] == 'gun'
    assert data['parents'][5] == 4 and data['parents'][4] == 1 and data['parents'][0] == -1
    assert [(c['id'], c['code'], c['radius']) for c in data['coll']] == [('none', '____', 50.0), ('tama', 'st__', 30.0)]

    def joint_y(clip, frame, joint):
        samples = data['clips'][clip]
        k = samples['frames'].index(frame)
        return samples['samples'][k][12 * joint + 7]
    kosi, gun = 0, 5
    assert joint_y('wait', 0, kosi) == pytest.approx(114.0, abs=0.5)        # standing body
    assert joint_y('landing', 0, kosi) < 10.0                               # dormant crouch on the ground
    assert joint_y('landing', 229, kosi) == pytest.approx(114.0, abs=1.0)   # landing ends standing
    assert joint_y('attack', 39, gun) == pytest.approx(90.0, abs=0.5)       # gun deployed below the body
    # Deterministic: a second bake is byte-identical.
    assert rig.bake(model, motions, coll)[0] == text
