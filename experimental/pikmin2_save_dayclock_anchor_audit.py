"""Day-clock/save-anchor field audit for the save-progression provider (#132).

Read-only inventory of retail save anchors in two research sources:
``src/plugProjectKandoU/singleGameSection.cpp`` and
``src/plugProjectKandoU/gamePlayData.cpp``. Consumes source text; never
writes research trees, runs the game or builds anything.

This module deliberately does NOT fork any existing parser. It reuses the
project's adapter framing -- stdlib-only, strict ``ValueError`` on missing
or malformed input, deterministic hashing -- and exposes a tiny line-index
scanner that callers (tests, report tooling) can drive with synthetic text.

Anchor groups (all lower-cased tokens matched literally):

- ``day_clock``: day count/advance and time-manager start anchors.
- ``sunset_loss``: cave-save time capture/restore and sun-gauge anchors.
- ``sprout_regeneration``: sprout creation/regeneration anchors (expected
  ABSENT from the two named files; recorded verbatim rather than invented).
- ``debt_equipment``: poko/debt progress flags and debt-level anchors.
- ``louie_president``: captain (Olimar/Louie/President) life/save anchors.
- ``save_migration``: cave/mail save-data lifecycle and STORYSAVE flags.
"""

import argparse
import hashlib
import json
from pathlib import Path

# Repository-relative research paths (read-only inputs).
RESEARCH_ROOT = Path('native/pikmin2-research')
SINGLE_GAME = 'src/plugProjectKandoU/singleGameSection.cpp'
GAME_PLAY_DATA = 'src/plugProjectKandoU/gamePlayData.cpp'

# The #132 anchor named a file that does not exist in the retail tree; the
# audit must record the verbatim absence instead of inventing it.
CLAIMED_ABSENT = 'gameSingleGameSection*.cpp'

ANCHORS = {
    'day_clock': [
        (SINGLE_GAME, 'advanceDayCount'),
        (SINGLE_GAME, 'CaveDayEndState::init'),
        (SINGLE_GAME, 'CaveDayEndState::exec'),
        (SINGLE_GAME, 'mTimeMgr->setStartTime'),
        (SINGLE_GAME, 'mTimeMgr->mDayCount'),
        (SINGLE_GAME, 'mDataGame.mDayNum'),
    ],
    'sunset_loss': [
        (SINGLE_GAME, 'mCaveSaveData.mTime'),
        (SINGLE_GAME, 'mCurrentTimeOfDay'),
        (SINGLE_GAME, 'mTimeMgr->setTime'),
        (SINGLE_GAME, 'getSunGaugeRatio'),
        (SINGLE_GAME, 'mSunGaugeRatio'),
    ],
    'sprout_regeneration': [
        (SINGLE_GAME, 'sprout'),
        (SINGLE_GAME, 'Sprout'),
        (GAME_PLAY_DATA, 'sprout'),
        (GAME_PLAY_DATA, 'Sprout'),
    ],
    'debt_equipment': [
        (GAME_PLAY_DATA, 'STORY_DebtPaid'),
        (GAME_PLAY_DATA, 'mDebtProgressFlags'),
        (GAME_PLAY_DATA, 'mBackupDebtProgressFlags'),
        (GAME_PLAY_DATA, 'mPokoCount'),
        (GAME_PLAY_DATA, 'mCavePokoCount'),
        (GAME_PLAY_DATA, 'mPokoCountOld'),
        (GAME_PLAY_DATA, '_aiConstants->mDebt.mData'),
        (SINGLE_GAME, 'mSMenuPause.mDebtRemaining'),
        (SINGLE_GAME, 'mSMenuMap.mDataMap.mPokos'),
    ],
    'louie_president': [
        (SINGLE_GAME, 'NAVIID_Olimar'),
        (SINGLE_GAME, 'NAVIID_Louie'),
        (SINGLE_GAME, 'NAVIID_President'),
        (SINGLE_GAME, 'mNaviLifeMax'),
        (SINGLE_GAME, 'mLouieData.mActiveNaviID'),
    ],
    'save_migration': [
        (GAME_PLAY_DATA, 'mCaveSaveData.clear'),
        (GAME_PLAY_DATA, 'mMailSaveData.clear'),
        (GAME_PLAY_DATA, 'mCaveSaveData.mCurrentCaveID'),
        (GAME_PLAY_DATA, 'mCaveSaveData.mCurrentFloor'),
        (GAME_PLAY_DATA, 'mCaveSaveData.mIsInCave'),
        (SINGLE_GAME, 'saveCaveMore'),
        (SINGLE_GAME, 'saveMainMapSituation'),
        (SINGLE_GAME, 'saveToGeneratorCache'),
        (SINGLE_GAME, 'caveSaveFormationPikmins'),
        (SINGLE_GAME, 'setSaveFlag(STORYSAVE_'),
    ],
}

# Non-fatal reads: these markers only produce notes, never PASS/FAIL gates.
EXPECTED_ABSENT_NOTES = {
    'sprout_regeneration': (
        'No sprout/regeneration anchor exists in the two named files; the '
        'retail anchor lives elsewhere (e.g. onyonMgr.cpp:67-73, '
        'itemPikihead.cpp:985-1000) and is recorded as an out-of-scope note.'
    ),
    'louie_president': (
        'NAVIID_President has no literal anchor in the two named files; only '
        'NAVIID_Olimar/NAVIID_Louie life anchors appear here.'
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def scan_text(text, rel):
    """Return anchors found in one named source text, line-indexed (1-based).

    ``rel`` is the source path the text belongs to; tokens are only matched
    for that source so the same module can audit either file independently.
    """
    if not isinstance(text, str):
        raise ValueError('source text must be str')
    if rel not in (SINGLE_GAME, GAME_PLAY_DATA):
        raise ValueError('unknown audit source: %r' % (rel,))
    lines = text.splitlines()
    found = []
    for group, specs in ANCHORS.items():
        for _source, token in specs:
            if _source != rel:
                continue
            for line_no, line in enumerate(lines, start=1):
                if token in line:
                    found.append({
                        'group': group,
                        'token': token,
                        'line': line_no,
                        'text': line.strip()[:160],
                    })
                    break
    return found


def audit(root, sources=(SINGLE_GAME, GAME_PLAY_DATA)):
    """Audit research sources; return an inventory plus verdict.

    ``root`` is the checkout containing ``native/pikmin2-research``.
    Missing source bytes raise ``ValueError`` (exact missing prerequisite).
    """
    root = Path(root)
    research = root / RESEARCH_ROOT
    if not research.is_dir():
        raise ValueError('missing research prerequisite: %s' % research)
    texts = {}
    for rel in sources:
        path = research / rel
        if not path.is_file():
            raise ValueError('missing research source: %s' % path)
        texts[rel] = path.read_text(encoding='utf-8', errors='replace')

    inventory = {}
    for rel, text in texts.items():
        inventory[rel] = {
            'sha256': digest(text.encode('utf-8', 'replace')),
            'anchors': scan_text(text, rel),
        }

    groups = {}
    for group in ANCHORS:
        groups[group] = sorted({
            rel for rel, data in inventory.items()
            for a in data['anchors'] if a['group'] == group
        })

    absent_claim_file = not any(
        p.name.startswith('gameSingleGameSection') and p.suffix == '.cpp'
        for p in research.rglob('*.cpp')
    )
    gaps = [group for group, rels in groups.items() if not rels]
    notes = [EXPECTED_ABSENT_NOTES[g] for g in gaps if g in EXPECTED_ABSENT_NOTES]
    unresolved = [g for g in gaps if g not in EXPECTED_ABSENT_NOTES]

    verdict = 'complete' if not unresolved else 'missing_prerequisite'
    return {
        'sources': inventory,
        'groups': groups,
        'claimed_absent_file': CLAIMED_ABSENT,
        'claimed_absent_verbatim': absent_claim_file,
        'gaps': gaps,
        'notes': notes,
        'unresolved_groups': unresolved,
        'verdict': verdict,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--report')
    args = parser.parse_args(argv)
    result = audit(args.root)
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.report:
        Path(args.report).write_text(text, encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
