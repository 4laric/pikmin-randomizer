"""Tests for the P1 Challenge runtime input package (#649).

Pure unit tests plus repo-file checks: contract loading from the recorded
pin, per-stage input package build/validation round-trip, malformed-input
rejection, log validation (boot observed vs captain-down blocked), and the
fixture audit (single staging, genuine level selection, no health writes).
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    'pikmin2_challenge_runtime_inputs',
    ROOT / 'experimental/pikmin2_challenge_runtime_inputs.py')
_inputs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inputs)

load_contract = _inputs.load_contract
build_input_package = _inputs.build_input_package
validate_package = _inputs.validate_package
validate_run_log = _inputs.validate_run_log
InputError = _inputs.InputError
CONTRACT_PIN = _inputs.CONTRACT_PIN
GUARD_SHA256 = _inputs.GUARD_SHA256

CANONICAL = Path('C:/Users/alari/pikmin-randomizer')
ASSETS = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')


def test_contract_loads_from_recorded_pin():
    contract = load_contract(CANONICAL)
    assert contract.stage_slots() == ['chal%d' % n for n in range(5)]
    assert contract.stage_entry('chal2')['area_id'] == 2


def test_contract_pin_enforced():
    try:
        build_input_package(CANONICAL, '0' * 64, ASSETS, Path('.'))
    except InputError:
        return
    raise AssertionError('expected InputError')


def _package(tmp_path):
    record = build_input_package(CANONICAL, CONTRACT_PIN, ASSETS, tmp_path / 'inputs')
    packet = json.loads(Path(record['path']).read_text(encoding='utf-8'))
    assert validate_package(packet) is True
    return packet, record


def test_package_round_trip(tmp_path):
    packet, record = _package(tmp_path)
    import hashlib
    assert record['sha256'] == hashlib.sha256(Path(record['path']).read_bytes()).hexdigest()
    assert [s['slot'] for s in packet['stages']] == ['chal%d' % n for n in range(5)]
    assert [s['challenge_level'] for s in packet['stages']] == [0, 1, 2, 3, 4]
    assert packet['guard']['sha256'] == GUARD_SHA256
    assert packet['stages'][0]['argv'][-1] == '0'


def test_package_rejects_malformed(tmp_path):
    packet, _ = _package(tmp_path)
    for mutate in (lambda p: p.update(schema=2),
                   lambda p: p['stages'].pop(),
                   lambda p: p['stages'][0].update(slot='chal9'),
                   lambda p: p.update(guard={})):
        broken = json.loads(json.dumps(packet))
        mutate(broken)
        try:
            validate_package(broken)
        except InputError:
            continue
        raise AssertionError('expected InputError')


def test_log_accepts_boot_observed():
    text = ('P2_CHALLENGE_BOOT level=2 slot=chal2\n'
            'P2_CHALLENGE_SQUAD pikis=20\n'
            'PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive\n')
    result = validate_run_log(text)
    assert result == {'observed': True, 'blocked': False, 'levels': [2]}


def test_log_maps_captain_down_to_blocked():
    text = ('P2_CHALLENGE_BOOT level=2 slot=chal2\n'
            'P2_CHALLENGE_SQUAD pikis=20\n'
            'P2_FIXTURE_CAPTAIN_DOWN tick=200 hp=0.500 orima_dead=0 dead_state=1 outcome=BLOCKED\n')
    result = validate_run_log(text)
    assert result['observed'] is False and result['blocked'] is True


def test_log_rejects_empty_run():
    assert validate_run_log('FPS: 60\n')['observed'] is False
def test_fixture_sections_parse():
    from scripts import build_p2_challenge_guarded_boot_fixture as builder_mod
    native = ROOT / 'native'
    if not (native / 'tools' / 'p2_challenge_guarded_boot_fixture.cpp').is_file():
        import pytest as _pytest
        _pytest.skip('native worktree link absent')
    includes, app = builder_mod.fixture_sections(native)
    assert 'p2_fixture_require_captain' in includes
    assert 'P2_CHALLENGE_BOOT level=' in app


def test_instrument_retargets_main_entry():
    from scripts import build_p2_challenge_guarded_boot_fixture as builder_mod
    native = ROOT / 'native'
    if not (native / 'tools' / 'preview_p2_room.cpp').is_file():
        import pytest as _pytest
        _pytest.skip('native worktree link absent')
    source = (native / 'tools' / 'preview_p2_room.cpp').read_text(encoding='utf-8')
    includes, app = builder_mod.fixture_sections(native)
    room = builder_mod.instrument(source, includes + app)
    assert 'requires --experimental-pikmin2-room' not in room
    assert 'requires --experimental-challenge-level 0-4' in room
    assert 'class RoomApp : public PlugPikiApp {' in room