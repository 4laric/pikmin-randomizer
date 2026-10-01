"""#246 OWN: Titan Dweevil (73) campaign identity wiring and staging.

The four bind gates on the root side: 73 resolves to its own family (no
proxy row), the content extractor and the family adapter are wired, and the
stager writes exactly the files pc_p2_bigtreasure_teki.cpp opens. The disc
import is local-only (ISO), so the staging checks run against the private
import when present and skip otherwise.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
IMPORT_CANDIDATES = [
    Path(os.environ['P2_BIGTREASURE_IMPORT']) if os.environ.get('P2_BIGTREASURE_IMPORT') else None,
    ROOT.parent / 'wt-p2port-73-content' / 'content' / 'BigTreasure',
    ROOT / 'output' / 'wt-p2port-73-content' / 'content' / 'BigTreasure',
]


def _import_dir():
    for candidate in IMPORT_CANDIDATES:
        if candidate and (candidate / 'bigtreasure.json').is_file():
            return candidate
    return None


def test_73_resolves_to_its_own_family_not_a_proxy():
    from experimental.pikmin2_family_install import ADAPTERS, resolve_family
    from randomizer.p2_proxy import load_rows

    assert resolve_family(73) == 'bigtreasure'
    assert resolve_family('BigTreasure') == 'bigtreasure'
    assert 'install' in ADAPTERS['bigtreasure'] and 'validate' in ADAPTERS['bigtreasure']
    assert 73 not in {row['source_id'] for row in load_rows()}


def test_prepare_content_wires_the_extractor():
    from scripts import p2_prepare_content as prep

    assert prep.ENUM_FOR_SOURCE[73] == 'BigTreasure'
    assert prep.EXTRACTORS[73] == 'extract_bigtreasure'
    assert callable(prep.extract_bigtreasure)
    assert '73 BigTreasure' in prep.__doc__


def test_adapter_rejects_foreign_species(tmp_path):
    from experimental.pikmin2_family_install import StagingError, _adapt_bigtreasure

    source = tmp_path / 'BigTreasure'
    source.mkdir()
    (source / 'identity.json').write_text('{"schema": 1, "source_id": 73, "enum_name": "BigTreasure"}')
    with pytest.raises(StagingError):
        _adapt_bigtreasure(source, tmp_path / 'run', [(1, 'Chappy')])
    with pytest.raises(StagingError):
        _adapt_bigtreasure(source, tmp_path / 'run', [])


@pytest.mark.skipif(_import_dir() is None, reason='local BigTreasure disc import not present')
def test_plan_derives_bank_legs_and_poses_from_the_import():
    from experimental import pikmin2_bigtreasure_campaign as camp

    plan = camp.plan(_import_dir())
    parms = plan['parms']
    assert set(parms) == {camp.PARMS_TXT, camp.EVENTS_TXT, camp.BANK_TXT, camp.COLL_TXT}
    # The Titan's own collision tree is the verbatim retail enemycoll.txt (#246).
    coll = parms[camp.COLL_TXT].decode('ascii')
    for part in ('{tam1}', '{tam2}', '{elec}', '{fire}', '{gasi}', '{mizu}', '{lft1}', '{rht5}'):
        assert part in coll
    assert parms[camp.PARMS_TXT].startswith(b'# Creature::Property')
    assert parms[camp.EVENTS_TXT].startswith(b'P2_RETAIL_EVENTS_1 ')
    rows = parms[camp.BANK_TXT].decode('ascii').splitlines()
    assert rows[0] == camp.BANK_HEADER and rows[-1] == 'end'
    clips = [r.split() for r in rows if r.startswith('clip ')]
    assert [int(c[1]) for c in clips] == list(range(30))
    assert [c[2] for c in clips] == list(camp.ANIM_SLOTS)
    # Leg layout = the source 4-leg frame: rhand/lhand front, rfoot/lfoot back.
    legs = next(r for r in rows if r.startswith('legs ')).split()[1:]
    distance, angles = float(legs[0]), [float(a) for a in legs[1:]]
    assert 150.0 < distance < 260.0
    assert angles[0] < 0 < angles[1] and abs(angles[2]) > 2.0 and abs(angles[3]) > 2.0
    # Every staged pose carries every bank joint (weapons ride the animation).
    poses = [r.split() for r in rows if r.startswith('pose ')]
    joints = [r.split() for r in rows if r.startswith('joint ')]
    assert len(joints) == len(poses) * len(camp.BANK_JOINTS)
    assert all(len(j) == 4 + 12 for j in joints)
    names = [n for n, _ in plan['room']]
    assert sum(n.startswith('bigtreasure_pellet_') for n in names) == 4
    # slot 29 (Walk's wait2) reuses wait2's poses: no second copy (a substring test would hit
    # bigtreasure_wait2_20.mod once a clip has 20+ poses)
    import re
    assert not any(re.search(r'wait2_2_\d\d\.mod$', n) for n in names)
    assert plan['pose_bytes'] <= camp.MAX_BYTES


@pytest.mark.skipif(_import_dir() is None, reason='local BigTreasure disc import not present')
def test_stage_writes_run_files_idempotently_and_refuses_changes(tmp_path):
    from experimental import pikmin2_bigtreasure_campaign as camp

    run = tmp_path / 'run'
    (run / camp.ROOM).mkdir(parents=True)
    receipt = camp.stage_from(_import_dir(), run)
    assert receipt['room'] == 'private' and receipt['room_files'] > 100
    for name in (camp.PARMS_TXT, camp.EVENTS_TXT, camp.BANK_TXT, camp.COLL_TXT):
        assert (run / name).is_file()
    again = camp.stage_from(_import_dir(), run)
    assert again['bank_sha256'] == receipt['bank_sha256']
    (run / camp.BANK_TXT).write_bytes(b'tampered')
    with pytest.raises(camp.BigTreasureStageError):
        camp.stage_from(_import_dir(), run)


# --- Titan Dweevil pose density (owner playtest 2026-09-30: "needs way more poses") ---

def test_titan_pose_limit_is_dense_and_coherent():
    from experimental import pikmin2_bigtreasure_assets as assets
    from experimental import pikmin2_bigtreasure_campaign as camp
    from experimental.pikmin2_animation import DEFAULT_POSE_LIMIT, POSE_LIMIT_MAX

    # More than the global default, within the native compact loader row cap, and the
    # stage keeps everything the extractor bakes (nothing is thinned at staging).
    assert assets.POSE_LIMIT > DEFAULT_POSE_LIMIT
    assert assets.POSE_LIMIT <= POSE_LIMIT_MAX
    assert assets.MAX_POSES == assets.POSE_LIMIT
    assert camp.MAX_POSES >= assets.POSE_LIMIT
    # The extractor byte budgets cover the measured ~97 KiB/pose dense tree
    # (29 clips, 1181 poses, 103.7 MiB measured 2026-09-30).
    assert assets.CLIP_BYTES >= assets.POSE_LIMIT * 100 * 1024
    assert assets.TOTAL_BYTES >= 104 * 1024 * 1024
    assert camp.MAX_BYTES >= assets.TOTAL_BYTES


def test_prepare_content_keeps_the_titan_dense_under_the_generic_default(tmp_path, monkeypatch):
    from experimental import pikmin2_bigtreasure_assets as assets
    from scripts import p2_prepare_content as prep

    seen = {}

    def fake_extract(iso, research, tmp, pose_limit):
        seen['pose_limit'] = pose_limit
        (tmp).mkdir(parents=True)

    monkeypatch.setattr(assets, 'extract', fake_extract)
    iso = tmp_path / 'disc.iso'
    iso.write_bytes(b'x')
    research = tmp_path / 'research'
    research.mkdir()
    prep.extract_bigtreasure(iso, research, tmp_path / 'out', pose_limit=prep.DEFAULT_POSE_LIMIT)
    assert seen['pose_limit'] == assets.POSE_LIMIT  # the global 24 never thins the Titan
    prep.extract_bigtreasure(iso, research, tmp_path / 'out2', pose_limit=prep.POSE_LIMIT_MAX)
    assert seen['pose_limit'] == assets.MAX_POSES  # an explicit larger request is capped at the species max


def test_subset_keeps_every_pose_when_under_the_limit():
    from experimental import pikmin2_bigtreasure_campaign as camp

    poses = [{'frame': i} for i in range(48)]
    assert camp._subset(poses, camp.MAX_POSES) == poses
    # Over the limit it keeps first and last and spreads evenly.
    many = [{'frame': i} for i in range(100)]
    picked = camp._subset(many, 10)
    assert len(picked) == 10 and picked[0]['frame'] == 0 and picked[-1]['frame'] == 99


@pytest.mark.skipif(_import_dir() is None, reason='local BigTreasure disc import not present')
def test_staged_bank_carries_every_baked_pose():
    from experimental import pikmin2_bigtreasure_campaign as camp

    plan = camp.plan(_import_dir())
    rows = plan['parms'][camp.BANK_TXT].decode('ascii').splitlines()
    counts = {r.split()[2]: int(r.split()[4]) for r in rows if r.startswith('clip ')}
    # Attack and pre-attack clips are the ones the owner asked for: each gets min(source frames, POSE_LIMIT)
    # poses, minus frames the converter cannot bake (dead's vanishing tail).
    from experimental import pikmin2_bigtreasure_assets as assets
    frames = {r.split()[2]: int(r.split()[3]) for r in rows if r.startswith('clip ')}
    for name, poses in counts.items():
        if name == 'dead':
            assert poses >= 40
            continue
        assert poses == min(frames[name], assets.POSE_LIMIT), name
    assert sum(counts.values()) > 1000
    assert plan['pose_bytes'] <= camp.MAX_BYTES
