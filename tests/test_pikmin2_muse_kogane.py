"""Tests for the lane 54 natural-throw Kogane receiver gate (#494).

Pins the validator contract for Kogane source ID 9 gate 3 through a real
thrown-Pikmin path: the staged captain marker, one genuine throw row per
release, the three native receiver flips with the audited drop table, the
source escape and a clean no-substitute fixture audit. The critical
discrimination test proves a legacy forced-AI log -- identical flip rows but
no throw rows -- is rejected.
"""
import experimental.pikmin2_muse_kogane as kogane

TARGET = kogane.TARGET
PASS_MARKER = kogane.PASS_MARKER


def _throw_log(completion=True, flips=(1, 2, 3), drops=None, forced=False):
    rows = ['P2_KOGANE_BIRTH id=%d type=3 x=0.000 y=30.000 z=0.000' % i
            for i in (219001, 219002, 219003, 219004)]
    if not forced:
        rows.append('P2_KOGANE_THROW_STAGED nx=-590.000 ny=30.000 nz=1500.000 '
                    'bx=-440.000 by=30.000 bz=1500.000')
    rows.append('P2_KOGANE_SQUAD pikis=20')
    if forced:
        rows.append('P2_KOGANE_NATURAL_COMMAND attackers=5')
    else:
        rows += ['P2_KOGANE_THROW n=%d generator=219001 dist=150.0' % n
                 for n in (1, 2, 3)]
    table = drops if drops is not None else {1: (1, 1, 0), 2: (0, 0, 2), 3: (0, 0, 3)}
    for f in flips:
        rows.append('P2_KOGANE_NATURAL_ATTACK generator=219001 source_id=9 flip=%d' % f)
        rows.append('P2_KOGANE_FLIP generator=219001 source_id=9 flip=%d' % f)
        pv, pc, nc = table[f]
        rows.append('P2_KOGANE_DROP generator=219001 source_id=9 flip=%d pellet%d=%d nectar=%d'
                    % (f, pv, pc, nc))
    if flips == (1, 2, 3):
        rows += ['P2_KOGANE_ESCAPE generator=219001 source_id=9 flips=3',
                 'P2_KOGANE_NATURAL_ESCAPED tick=900 throws=3 beetle_alive=0']
    if completion:
        rows.append(PASS_MARKER)
    return '\n'.join(rows) + '\n'


def _tracked_fixture():
    return kogane.fixture_path().read_text(encoding='utf-8')


def test_audit_accepts_tracked_throw_fixture():
    audit = kogane.audit_fixture_source(_tracked_fixture())
    assert audit['passed'], audit['checks']


def test_audit_rejects_forced_ai_fixture():
    legacy = ('command(p,idx){p->resetPosition(spot);'
              'p->mActiveAction->startAction(PikiAction::Attack,beetle);p->mMode=PikiMode::AttackMode;}'
              'nudgeDrink(){p->resetPosition(Vector3f(wp.x,wp.y+1.0f,wp.z));}'
              'pinObservers();holdOthers();P2_KOGANE_NATURAL_COMMAND')
    audit = kogane.audit_fixture_source(legacy)
    assert not audit['passed']
    assert not audit['checks']['single_staged_reposition']
    assert not audit['checks']['no_attack_directive']
    assert not audit['checks']['no_mode_write']
    assert not audit['checks']['no_perframe_holders']


def test_audit_rejects_injected_press_fixture():
    audit = kogane.audit_fixture_source('InteractPress p(n,0.0f);actor->stimulate(p);pc_p2_kogane_pressed')
    assert not audit['passed']
    assert not audit['checks']['no_injected_press']


def test_sections_extract_room_app():
    includes, app = kogane.fixture_sections(_tracked_fixture())
    assert 'class RoomApp : public PlugPikiApp {' in app
    assert 'P2_KOGANE_THROW_STAGED' in app
    assert '#include "pc_p2_kogane.h"' in includes


def test_validate_accepts_clean_throw_run():
    evidence = kogane.validate_natural_throw(_throw_log(), 0, _tracked_fixture())
    assert evidence['passed'], evidence['checks']
    assert evidence['throws'] == [1, 2, 3]


def test_validate_rejects_forced_ai_log_with_identical_flips():
    # The legacy trigger emits the same native flip rows; without throw rows
    # and the staged marker it must not validate as a natural throw run.
    evidence = kogane.validate_natural_throw(_throw_log(forced=True), 0, _tracked_fixture())
    assert not evidence['passed']
    assert not evidence['checks']['staged_once']
    assert not evidence['checks']['throws_sequential']
    assert not evidence['checks']['no_forced_markers']


def test_validate_rejects_incomplete_flip_chain():
    bad = _throw_log(flips=(1, 2), completion=False)
    evidence = kogane.validate_natural_throw(bad, 0, _tracked_fixture())
    assert not evidence['passed']
    assert not evidence['checks']['natural_attacks']
    assert not evidence['checks']['escape']


def test_validate_rejects_wrong_drop_table():
    bad = _throw_log(drops={1: (5, 3, 0), 2: (0, 0, 3), 3: (0, 0, 3)})
    evidence = kogane.validate_natural_throw(bad, 0, _tracked_fixture())
    assert not evidence['passed']
    assert not evidence['checks']['drop_tables']


def test_validate_rejects_dirty_fixture_even_with_clean_log():
    evidence = kogane.validate_natural_throw(_throw_log(), 0, 'startAction(PikiAction::Attack,x)')
    assert not evidence['passed']
    assert not evidence['checks']['fixture_audit']


def test_drop_table_matches_legacy_audit():
    from experimental.pikmin2_kogane_behavior import EXPECTED_DROPS
    for f in (1, 2, 3):
        assert kogane.EXPECTED_DROPS_9[f] == EXPECTED_DROPS[(TARGET, f)]
