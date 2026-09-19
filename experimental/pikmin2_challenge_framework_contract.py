"""P2 Challenge framework contract (#136): source-backed machine-readable schema.

Decodes the retail Challenge stage table (user/Matoba/challenge/stages.txt,
GPVE01 rev 0) exactly as Game::ChallengeGame::StageData::read parses it
(version 4: PikiContainer 7 colors x 3 happa stages, caveinfo filename, time
limit, bitter/spicy starts, floor count, unused otakara count, 2D stage
index, per-floor timer extensions), cross-checks it against the canonical
content inventory, and encodes the engine-observed framework semantics
(scoring, timers, sprays, end conditions, 1P/2P boundaries, provider split)
for challenge-0/1/2/3 planners to consume. No runtime, no gameplay claims.
"""
import hashlib
import json
import re
from pathlib import Path

STAGE_TABLE_PATH = 'user/Matoba/challenge/stages.txt'
KFES_STAGE_TABLE_PATH = 'user/Matoba/challenge/kfes-stages.txt'
EXPECTED_VERSION = 4
COLORS = ('Blue', 'Red', 'Yellow', 'Purple', 'White', 'Bulbmin', 'Carrot')
HAPPA = ('Leaf', 'Bud', 'Flower')
CH_SCORE_POKO_MULTIPLIER = 10
CH_SCORE_PIKMIN_MULTIPLIER = 10
RUNTIME_DEPENDENCIES = [136, 137, 129, 130, 131]


class ContractError(ValueError):
    pass


def parse_stage_table(text):
    """Decode the Challenge stage table into a list of stage dicts.

    Mirrors StageData::read field order (version, caveinfo filename,
    PikiContainer col0-6 x happa0-2, time, bitter, spicy, floors, otakara,
    2D index, floor timers). Raises ContractError on any malformed input.
    """
    lines = [line.split('#')[0].strip() for line in text.splitlines()]
    lines = [line for line in lines if line not in ('', '{', '}')]
    if not lines:
        raise ContractError('Empty stage table')
    try:
        count = int(lines[0])
    except ValueError as exc:
        raise ContractError('Missing stage count') from exc
    if count <= 0 or count > 64:
        raise ContractError('Implausible stage count: %r' % lines[0])
    stages, at = [], 1
    for _ in range(count):
        try:
            version = int(lines[at]); at += 1
            caveinfo = lines[at]; at += 1
            roster = [[int(lines[at + c * 3 + h]) for h in range(3)] for c in range(7)]
            at += 21
            time, bitter, spicy = float(lines[at]), int(lines[at + 1]), int(lines[at + 2])
            floors, otakara, index = int(lines[at + 3]), int(lines[at + 4]), int(lines[at + 5])
            timers = [float(lines[at + 6 + f]) for f in range(floors)]
            at += 6 + floors
        except (IndexError, ValueError) as exc:
            raise ContractError('Truncated/malformed stage entry') from exc
        if version != EXPECTED_VERSION:
            raise ContractError('Unsupported stage version %d for %s' % (version, caveinfo))
        if not re.fullmatch(r'[A-Za-z0-9_]+\.txt', caveinfo):
            raise ContractError('Malformed caveinfo filename: %r' % caveinfo)
        if floors < 1 or any(v < 0 for row in roster for v in row):
            raise ContractError('Invalid floor/roster values for %s' % caveinfo)
        if time < 0 or bitter < 0 or spicy < 0 or otakara < 0 or index < 0:
            raise ContractError('Invalid scalar values for %s' % caveinfo)
        if any(v < 0 for v in timers):
            raise ContractError('Invalid floor timers for %s' % caveinfo)
        stages.append(dict(cave_id=caveinfo[:-len('.txt')], cave_path='user/Mukki/mapunits/caveinfo/' + caveinfo,
                           floors=floors, roster=roster, legacy_time=time,
                           bitter_sprays=bitter, spicy_sprays=spicy,
                           treasure_count_field=otakara, ui_index=index, floor_seconds=timers))
    if at != len(lines):
        raise ContractError('Trailing stage table data')
    return stages


def read_stage_table(iso_path, kfes=False):
    """Read and hash-verify the stage table from a local GPVE01 disc image."""
    from experimental.pikmin2_assets import disc_files
    path = KFES_STAGE_TABLE_PATH if kfes else STAGE_TABLE_PATH
    catalog = disc_files(Path(iso_path))
    if path not in catalog:
        raise ContractError('Stage table absent from disc image: ' + path)
    at, size = catalog[path]
    with open(iso_path, 'rb') as disc:
        disc.seek(at)
        data = disc.read(size)
    if len(data) != size:
        raise ContractError('Truncated disc source: ' + path)
    return data, hashlib.sha256(data).hexdigest()


def cross_check_inventory(stages, inventory):
    """Compare decoded stages against the canonical content inventory.

    Returns per-stage mismatches (empty means full agreement). The inventory
    is the curated baseline; this function reports drift, never edits it.
    """
    entries = {e['cave_id']: e for e in inventory.get('challenge', {}).get('stages', [])}
    mismatches = []
    for stage in stages:
        entry = entries.get(stage['cave_id'])
        if entry is None:
            mismatches.append(dict(cave_id=stage['cave_id'], reason='missing from inventory'))
            continue
        for key in ('floors', 'legacy_time', 'bitter_sprays', 'spicy_sprays',
                    'treasure_count_field', 'ui_index', 'floor_seconds'):
            if entry.get(key) != stage[key]:
                mismatches.append(dict(cave_id=stage['cave_id'], reason='field %s differs' % key))
        if entry.get('pikmin_by_native_color_and_maturity') != stage['roster']:
            mismatches.append(dict(cave_id=stage['cave_id'], reason='roster differs'))
        if entry.get('cave_path') != stage['cave_path']:
            mismatches.append(dict(cave_id=stage['cave_id'], reason='cave_path differs'))
    return mismatches


def compute_score(pokos, time_left, pikmin_left):
    """Retail result formula (vsGS_Result): pokos*10 + timeLeft + pikminLeft*10."""
    for value in (pokos, time_left, pikmin_left):
        if not isinstance(value, int) or value < 0:
            raise ContractError('Score inputs must be nonnegative ints')
    return pokos * CH_SCORE_POKO_MULTIPLIER + time_left + pikmin_left * CH_SCORE_PIKMIN_MULTIPLIER


def framework_providers():
    """Provider split: existing generic providers vs missing framework behavior."""
    return dict(
        existing={
            'cave_generation_129': 'Floor layout/unit pools, hole descent (goNextFloor), seams.',
            'actor_species_130_131': 'Enemy/family actors, receivers, parms, banks.',
            'surface_saves_132': 'Day/save persistence incl. challenge clear flags and highscores (PlayCommonData).',
            'treasure_140': 'Treasure/held-object/drop/carry/reward ledger.',
            'content_p0': 'Per-stage caveinfo decode + resource closure (30/30 complete).',
        },
        missing={
            'challenge_host_mode': '1P Challenge host: stage select by 2D index, squad/spray application (PikiContainer, setDopeCount), mTimeLimit countdown, per-floor extensions.',
            'result_screen': 'Score/highscore/clear/perfect/pink-flower/unlock computation per vsGS_Result semantics.',
            'coop_2p': 'Two-player shared stage table, dual captains/camera, separate highscore slots (engine files exist; no port evidence).',
            'key_completion': 'Per-stage completion predicate (key/treasure/exit rules; treasure_count_field semantics unproven).',
        })


def first_slice_spec():
    """Smallest executable vertical slice plus ownership (planning input)."""
    return dict(
        name='1P single-floor timed stage with score',
        stage_example='ch_MUKI_bombing (1 floor, 255 s) or ch_NARI_01kusachi (1 floor, 180 s)',
        steps=[
            'Apply starting squad (PikiContainer) and sprays (setDopeCount) at stage start.',
            'Enforce mTimeLimit countdown with per-floor extension on descent.',
            'Descend/exit via existing hole contract (#129); end on timer/extinction/give-up/captain-down.',
            'Compute score/highscore/clear/perfect flags per compute_score and result semantics.',
        ],
        owners=dict(host_mode='new framework lane (to dispatch)', generation_holes='#129',
                    actors='#130/#131', saves_unlocks='#132', treasure='#140',
                    stage_content='challenge-0/1/2/3 planners (P0 complete)'),
        acceptance=[
            'Starting squad/sprays/timers match the decoded stage entry exactly.',
            'Timeout, extinction, give-up and captain-down end states observed distinctly.',
            'Score reproduces compute_score on observed pokos/time/pikmin counts.',
        ])