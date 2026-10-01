"""Negative and positive tests for the Mar29 observer reader (#375)."""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_muse_mar as muse  # noqa: E402

GEN = '346001'
BASE = "\n".join([
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_MAR_BIND generator=%s source_id=29 visual_only=0' % GEN,
    'P2_ENEMY_READY species=Mar native_family=Mar generator=%s x=1.0 y=2.0 z=3.0 '
    'health=3000.0 max_health=3000.0 behavior=native source_FSM=implemented '
    'attack=interactflick_wind' % GEN,
    'P2_MAR_STATE generator=%s state=wait' % GEN,
    'P2_MAR_STATE generator=%s state=chase' % GEN,
    'P2_MAR_BLOW generator=%s pikmin=4' % GEN,
    'P2_MUSE_MAR_DRAIN events=8 min=90.00 start=3000.00',
    'P2_MUSE_MAR_NATURAL_DEATH mar=1 health=0.00 tick=1234',
    'P2_MAR_DEAD generator=%s source_id=29 health=0' % GEN,
    'P2_MUSE_MAR_CORPSE pellet=1 generator=%s' % GEN,
    'P2_MUSE_MAR_CARRY state=1 alive=1 transport=6',
    'P2_POD_RECEIPT id=corpse:%s value=2 new=1 pokos=2 seeds=0' % GEN,
    'P2_MUSE_MAR_FORGET count=0 registered=0',
    'P2_MUSE_MAR_REENTRY old=1 new=2 stale=0 fresh=1 count=1',
    'P2_MUSE_MAR_SESSION navi=1 pikis=1',
    'PASS P2_MUSE_MAR death=Mar corpse=1 receipt=1 reentry=1 injected=0',
]) + "\n"


def log(**replace):
    text = BASE
    for key, value in replace.items():
        text = text.replace('{%s}' % key, value)
    return text


def test_valid_natural_run_passes():
    result = muse.validate(BASE, 0)
    assert result['gates'] == {'death_corpse': 'pass', 'transport_reward': 'pass',
                               'cleanup_reentry': 'pass'}
    assert result['passed'] is True
    assert result['mar_generator'] == GEN


def test_blocked_run_reports_transport_blocked_not_pass():
    text = BASE.replace('P2_MUSE_MAR_CARRY state=1 alive=1 transport=6',
                        'BLOCKED transport=missing_receipt')
    text = re.sub(r'P2_POD_RECEIPT[^\n]*\n', '', text)
    result = muse.validate(text, 0)
    assert result['gates']['transport_reward'] == 'blocked'
    assert result['gates']['death_corpse'] == 'pass'
    assert result['gates']['cleanup_reentry'] == 'pass'
    assert result['passed'] is False


def test_injected_death_marker_rejected():
    text = BASE.replace('PASS P2_MUSE_MAR',
                        'P2_MUSE_MAR_INJECT mhealth=0\nPASS P2_MUSE_MAR')
    result = muse.validate(text, 0)
    assert result['checks']['no_inject'] is False
    assert result['gates']['death_corpse'] == 'fail'


def test_injected_receipt_rejected_while_blocked():
    text = BASE.replace('P2_POD_RECEIPT id=corpse:%s value=2 new=1 pokos=2 seeds=0' % GEN,
                        'BLOCKED transport=missing_receipt\n'
                        'P2_POD_RECEIPT id=corpse:%s value=2 new=1 pokos=2 seeds=0' % GEN)
    result = muse.validate(text, 0)
    assert result['gates']['transport_reward'] == 'blocked'
    assert result['checks']['natural_carry'] is False


def test_proxy_carry_rejected():
    text = BASE.replace('P2_MUSE_MAR_CARRY state=1 alive=1 transport=6',
                        'P2_MUSE_MAR_CARRY state=1 alive=1 transport=6 proxy=1')
    result = muse.validate(text, 0)
    assert result['checks']['natural_carry'] is False
    assert result['gates']['transport_reward'] == 'fail'


def test_missing_native_dead_marker_rejected():
    text = re.sub(r'P2_MAR_DEAD[^\n]*\n', '', BASE)
    result = muse.validate(text, 0)
    assert result['gates']['death_corpse'] == 'fail'


def test_receipt_for_wrong_generator_rejected():
    text = BASE.replace('P2_POD_RECEIPT id=corpse:%s' % GEN,
                        'P2_POD_RECEIPT id=corpse:999999')
    result = muse.validate(text, 0)
    assert result['checks']['natural_carry'] is False
    assert result['gates']['transport_reward'] == 'fail'


def test_duplicate_delivery_is_idempotent_gate():
    text = BASE + 'P2_POD_RECEIPT id=corpse:%s value=2 new=0 pokos=2 seeds=0\n' % GEN
    result = muse.validate(text, 0)
    assert result['gates']['transport_reward'] == 'pass'


def test_nonzero_exit_code_fails():
    result = muse.validate(BASE, 1)
    assert result['passed'] is False


def test_captain_down_rejected():
    text = BASE.replace('PASS P2_MUSE_MAR',
                        'P2_FIXTURE_CAPTAIN_DOWN tick=99 hp=1.000 orima_dead=0 '
                        'dead_state=0 outcome=BLOCKED\nPASS P2_MUSE_MAR')
    result = muse.validate(text, 86)
    assert result['checks']['captain_safe'] is False
    assert result['passed'] is False


def test_dependency_report_cites_native_evidence():
    report = muse.dependency_report()
    assert report['gate'] == 'transport_reward'
    assert any('pc_p2_preview.cpp' in item for item in report['evidence'])
    assert any('pc_p2_mar.cpp' in item for item in report['evidence'])
    assert 'existing-owner review' in report['needs']


def test_reader_is_dependency_free():
    source = (ROOT / 'experimental' / 'pikmin2_muse_mar.py').read_text()
    assert 'import numpy' not in source
    assert 'import requests' not in source