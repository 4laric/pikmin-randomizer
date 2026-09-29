"""Persistent Purple flight wiring; synthetic assets/processes, no gameplay claim."""
import hashlib
import json
import struct
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from experimental import pikmin2_campaign as campaign
from experimental.pikmin2_purple_motion import CLIPS
from scripts import preview_pikmin2_emergence as preview


@pytest.fixture
def banks(tmp_path):
    imported, purple, motion = (tmp_path/name for name in ('imported', 'purple', 'motion'))
    pods = [tmp_path/'pod1', tmp_path/'pod2']
    ordered = []

    def put(label, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        ordered.append((label, data))

    units = ('room_north_tutorial_1_snow', 'room_purple14x14_snow')
    for floor, unit in enumerate(units, 1):
        for name in ('render.mod', 'collision.json'):
            put(f'floor{floor}/{name}', imported/'units'/unit/name,
                b'{"routes": [], "vertices": [], "triangles": []}' if name.endswith('json') else b'room')
    manifest = {'schema': 1, 'cave': 'tutorial_1',
                'units': {unit: {'start_destination_audit': []} for unit in units}}
    put('import-manifest', imported/'manifest.json', json.dumps(manifest).encode())
    for index, pod in enumerate(pods, 1):
        for name in ('pod.mod', 'treasure.mod', 'p2-pod.txt'):
            put(f'pod{index}/{name}', pod/name,
                b'P2_POD_1 atlas 200 101 101 0 1\n' if name.endswith('txt') else name.encode())
    put('purple/purple_wait_00.mod', purple/'purple_wait_00.mod', b'purple')
    put('purple/config', purple/'p2-purple.txt', b'P2_PURPLE_1\n')
    motion.mkdir()
    matrices = [f'happa {name} {index} ' + ' '.join(['0']*12)
                for name, count in CLIPS for index in range(count)]
    profile = '\n'.join(['P2_PURPLE_MOTION_1', 'rolljmp 14 0.466667', 'fall 20 0.666667'] + matrices) + '\n'
    (motion/'p2-purple-motion.txt').write_text(profile)
    for name, count in CLIPS:
        for index in range(count):
            (motion/f'purple_{name}_{index:02}.mod').write_bytes(f'{name}:{index}'.encode())
    return imported, pods, purple, motion, ordered


def test_legacy_identity_is_byte_compatible_and_motion_binds_resume(banks, tmp_path):
    imported, pods, purple, motion, ordered = banks
    # Independently reproduce the pre-option byte stream, including its order.
    legacy = hashlib.sha256(b'P2_CAVE_LAYOUT_1:two-standalone-rooms:all-survivors:boundary-checkpoint')
    for label, data in ordered:
        legacy.update(label.encode() + b'\0' + hashlib.sha256(data).digest())
    assert campaign.content_identity(imported, pods, purple) == legacy.hexdigest()
    enabled = campaign.content_identity(imported, pods, purple, purple_motion=motion)
    assert enabled != legacy.hexdigest()
    checkpoint = tmp_path/'checkpoint.json'
    checkpoint.write_text(json.dumps(campaign.initial(enabled)))
    assert campaign.load(checkpoint, enabled)['content'] == enabled
    for path in (motion/'purple_fall_19.mod', motion/'p2-purple-motion.txt'):
        original = path.read_bytes()
        changed = original + b'\n' if path.suffix == '.mod' else original.replace(b'0.666667', b'0.700000')
        path.write_bytes(changed)
        with pytest.raises(ValueError, match='changed'):
            campaign.load(checkpoint, campaign.content_identity(imported, pods, purple, purple_motion=motion))
        path.write_bytes(original)
    with pytest.raises(ValueError, match='changed'):
        campaign.load(checkpoint, legacy.hexdigest())


@pytest.mark.parametrize('invalid', ['missing', 'extra', 'profile'])
def test_invalid_bank_rejected_before_session_creation(banks, tmp_path, invalid):
    imported, pods, purple, motion, _ = banks
    if invalid == 'missing':
        (motion/'purple_fall_19.mod').unlink()
    elif invalid == 'extra':
        (motion/'purple_fall_20.mod').write_bytes(b'extra')
    else:
        (motion/'p2-purple-motion.txt').write_text('bad profile')
    session = tmp_path/'session'
    with pytest.raises(ValueError), patch.object(campaign.subprocess, 'run') as launch:
        campaign.run_campaign(tmp_path, imported, pods, purple, pods[0]/'treasure.mod',
                              tmp_path/'unused.exe', session, purple_motion=motion)
    launch.assert_not_called()
    assert not session.exists()


@pytest.mark.parametrize('enabled', [False, True])
def test_campaign_forwards_bank_across_both_floor_processes(banks, tmp_path, enabled):
    imported, pods, purple, motion, _ = banks
    selected = motion if enabled else None
    calls = []

    def staged(*args, **kwargs):
        calls.append(kwargs)
        run = tmp_path/f'run{kwargs["floor"]}'
        run.mkdir()
        return run

    def child(command, cwd, **kwargs):
        # Emulate only the process handoff, using the real checkpoint parser.
        entry = (cwd/'p2-cave-entry.txt').read_text()
        (cwd/'p2-cave-transfer.txt').write_text(entry.replace('P2_CAVE_ENTRY_', 'P2_CAVE_TRANSFER_'))
        return SimpleNamespace(returncode=campaign.EXIT_TRANSITION)

    with patch.object(campaign, 'prepare', side_effect=staged), \
         patch.object(campaign, 'allowed_receipts', return_value={}), \
         patch.object(campaign.subprocess, 'run', side_effect=child):
        state = campaign.run_campaign(tmp_path, imported, pods, purple, pods[0]/'treasure.mod',
                                      tmp_path/'unused.exe', tmp_path/'session', purple_motion=selected)
    assert state['status'] == 'exited'
    assert [call['floor'] for call in calls] == [1, 2]
    assert all(call['purple_motion'] == selected for call in calls)
    assert [call['violet'] for call in calls] == [False, True]


def test_real_preview_stages_flight_profile_and_all_poses(banks, tmp_path):
    imported, pods, purple, motion, _ = banks
    assets = tmp_path/'assets'
    (assets/'dataDir/stages/chal0').mkdir(parents=True)
    (assets/'dataDir/stages/chal0.ini').write_bytes(b'map_file old\nnavi_start 0 0\n')
    actor = bytearray(100)
    actor[:8] = b'    0.0v'
    actor[16:48] = b'preview red onion'.ljust(32, b'\0')
    generator = b'1.0v' + struct.pack('>4fI', 0, 0, 0, 0, 1) + actor

    def overlay(_assets, destination, overrides):
        for name, data in overrides.items():
            path = destination/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    # Geometry and the base P1 asset overlay are synthetic; the production
    # Purple config/bank staging itself executes unmocked.
    with patch.object(preview, 'generator', return_value=generator), \
         patch.object(preview, 'attach_collision', return_value=b'room'), \
         patch.object(preview, 'route_ini', return_value=''), \
         patch.object(preview, 'ground_height', return_value=0), \
         patch.object(preview, 'overlay', side_effect=overlay):
        run = preview.prepare(assets, imported, pods[0]/'treasure.mod', tmp_path/'runs',
                              pod=pods[0], purple=purple, violet=False, purple_motion=motion)
    assert (run/'p2-purple-flight.txt').read_text() == 'P2_PURPLE_FLIGHT_1\n'
    assert (run/'p2-purple-motion.txt').read_text() == (motion/'p2-purple-motion.txt').read_text()
    assert (run/'p2-purple.txt').read_text().count('impact red_earthquake_v1') == 1
    for source in motion.glob('*.mod'):
        assert (run/'assets/dataDir/courses/pikmin2room'/source.name).read_bytes() == source.read_bytes()
