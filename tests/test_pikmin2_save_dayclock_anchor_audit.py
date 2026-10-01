"""Focused tests for the day-clock/save-anchor audit adapter (#132).

Synthetic text only: malformed/missing input must fail closed, real token
shapes must be indexed with line numbers, and the retail research tree is
audited read-only for the report.
"""
from pathlib import Path

import pytest

from experimental import pikmin2_save_dayclock_anchor_audit as audit

REPO_ROOT = Path(__file__).resolve().parent.parent
SINGLE = audit.SINGLE_GAME
DATA = audit.GAME_PLAY_DATA


def test_scan_indexes_tokens_with_line_numbers():
    text = 'a\nsection->advanceDayCount();\nmTimeMgr->mDayCount\n'
    found = audit.scan_text(text, SINGLE)
    by_token = {a['token']: a['line'] for a in found}
    assert by_token['advanceDayCount'] == 2
    assert by_token['mTimeMgr->mDayCount'] == 3
    assert all(a['group'] == 'day_clock' for a in found)


def test_scan_respects_source_membership():
    # debt anchors belong to gamePlayData; the same text under singleGame
    # must not claim them.
    line = 'mPokoCount += pellet->mConfig->mParams.mMoney.mData;\n'
    assert audit.scan_text(line, DATA), 'expected debt anchor for gamePlayData'
    assert not [a for a in audit.scan_text(line, SINGLE)
                if a['group'] == 'debt_equipment']


def test_scan_rejects_non_string_and_unknown_source():
    with pytest.raises(ValueError):
        audit.scan_text(None, SINGLE)
    with pytest.raises(ValueError):
        audit.scan_text('x', 'src/not/a/source.cpp')


def test_digest_is_deterministic():
    assert audit.digest(b'abc') == audit.digest(b'abc')
    assert audit.digest(b'abc') != audit.digest(b'abd')


def test_audit_missing_tree_fails_closed(tmp_path):
    with pytest.raises(ValueError):
        audit.audit(tmp_path)


def test_audit_missing_source_fails_closed(tmp_path):
    (tmp_path / audit.RESEARCH_ROOT / 'src/plugProjectKandoU').mkdir(parents=True)
    with pytest.raises(ValueError):
        audit.audit(tmp_path)


def test_audit_reports_absent_claimed_file_and_verdict(tmp_path):
    src = tmp_path / audit.RESEARCH_ROOT / 'src/plugProjectKandoU'
    src.mkdir(parents=True)
    (src / 'singleGameSection.cpp').write_text(
        'advanceDayCount();\nmCaveSaveData.mTime = mCurrentTimeOfDay;\n'
        'mNaviLifeMax[NAVIID_Louie] = 1.0f;\nsetSaveFlag(STORYSAVE_Cave, 0);\n',
        encoding='utf-8')
    (src / 'gamePlayData.cpp').write_text(
        'mPokoCount = 0;\nmCaveSaveData.clear();\n', encoding='utf-8')
    result = audit.audit(tmp_path)
    assert result['claimed_absent_verbatim'] is True
    assert result['claimed_absent_file'] == 'gameSingleGameSection*.cpp'
    # sprout has no anchor anywhere in the two files. It is recorded as an
    # expected-absent note (the retail anchor lives elsewhere), so it is not
    # invented and not counted as an unresolved gap -> verdict stays complete.
    assert 'sprout_regeneration' in result['gaps']
    assert 'sprout_regeneration' not in result['unresolved_groups']
    assert result['verdict'] == 'complete'
    assert result['groups']['day_clock'] == [SINGLE]
    assert result['groups']['debt_equipment'] == [DATA]


def _canonical_root():
    candidates = [REPO_ROOT, REPO_ROOT.parent, Path('C:/Users/alari/pikmin-randomizer')]
    for candidate in candidates:
        if (candidate / audit.RESEARCH_ROOT).is_dir():
            return candidate
    return None


def test_audit_real_research_tree_has_core_groups():
    root = _canonical_root()
    if root is None:
        pytest.skip('research tree unavailable')
    result = audit.audit(root)
    assert result['claimed_absent_verbatim'] is True
    for group in ('day_clock', 'sunset_loss', 'debt_equipment',
                  'louie_president', 'save_migration'):
        assert result['groups'][group], 'missing %s anchors' % group
    assert all(a['line'] > 0 for data in result['sources'].values()
               for a in data['anchors'])
