"""Natural-gameplay observation adapter for P2 Challenge 04 ch_NARI_01kusachi.

Lane kusachi-gameplay-obs (#780). Runtime slice, not gameplay acceptance: the
module parses a guarded headed run log produced by the lane observer
(native/tools offline fixture; see docs/content_lanes/
p2-challenge-ch_nari_01kusachi-gameplay.md) into the six arena gates. It never
invents values: a gate is PASS only when its receipt-parseable marker is
present in a run that also shows the bound live squad and no captain-down.
Absent events stay UNTESTED with the reason the run recorded.

The stage identity below is pinned from docs/PIKMIN_CONTENT_IMPORT_LANES.json
and docs/PIKMIN2_CONTENT_INVENTORY.json (challenge entry, ui_index 3).
"""
import re

CAVE_ID = 'ch_NARI_01kusachi'
UI_INDEX = 3
FLOORS = 1
FLOOR_SECONDS = [180.0]
LEGACY_TIME = 350.0
BITTER_SPRAYS = 1
SPICY_SPRAYS = 2
TREASURE_COUNT_FIELD = 0
EXPECTED_ROSTER = [[0, 0, 50], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]]
ROSTER_TARGET_COLOR = 0          # first nonzero row = blue
EXPECTED_SQUAD = 20
GUARD_SHA256 = 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474'

GATES = ('identity_spawn', 'movement_animation', 'attacks_receivers',
         'death_corpse', 'transport_reward', 'cleanup_reentry')


def stage_identity():
    return dict(cave_id=CAVE_ID, ui_index=UI_INDEX, floors=FLOORS,
                floor_seconds=list(FLOOR_SECONDS), legacy_time=LEGACY_TIME,
                bitter_sprays=BITTER_SPRAYS, spicy_sprays=SPICY_SPRAYS,
                treasure_count_field=TREASURE_COUNT_FIELD, roster=EXPECTED_ROSTER,
                roster_target_color=ROSTER_TARGET_COLOR, expected_squad=EXPECTED_SQUAD,
                guard_sha256=GUARD_SHA256)


def _int(pattern, text, group=1, default=None):
    match = re.search(pattern, text, re.MULTILINE)
    return int(match.group(group)) if match else default


def _float(pattern, text, group=1, default=None):
    match = re.search(pattern, text, re.MULTILINE)
    return float(match.group(group)) if match else default


def parse_run(log_text):
    """Extract the observer receipts from a native run log (no inference)."""
    return dict(
        stage=_int(r'^P2_KUSACHI_GAMEPLAY_STAGE .*ui_index=(\d+)', log_text)
            if 'P2_KUSACHI_GAMEPLAY_STAGE' in log_text else None,
        cave=(re.search(r'^P2_KUSACHI_GAMEPLAY_STAGE cave=(\S+)', log_text, re.MULTILINE) or [None, None])[1]
            if 'P2_KUSACHI_GAMEPLAY_STAGE' in log_text else None,
        window_960=bool(re.search(r'^P2_KUSACHI_GAMEPLAY_WINDOW size=960x540 .*centered=1', log_text, re.MULTILINE)),
        identity_total=_int(r'^P2_KUSACHI_IDENTITY tick=\d+ total=(\d+)', log_text),
        identity_blue=_int(r'^P2_KUSACHI_IDENTITY tick=\d+ total=\d+ blue=(\d+)', log_text),
        identity_wired=_int(r'^P2_KUSACHI_IDENTITY tick=\d+ total=\d+ blue=\d+ wired=(\d+)', log_text),
        movement_peak=_float(r'^P2_KUSACHI_MOVEMENT tick=\d+ samples=\d+ peak=([\d.]+)', log_text),
        movement_pass=_int(r'^P2_KUSACHI_MOVEMENT .* pass=(\d+)', log_text),
        teki_first=_int(r'^P2_KUSACHI_ENEMIES tick=\d+ teki=(-?\d+)', log_text),
        extinction=_int(r'^P2_KUSACHI_EXTINCTION tick=(\d+)', log_text),
        attack=bool(re.search(r'^P2_KUSACHI_ATTACK status=PASS', log_text, re.MULTILINE)),
        death=bool(re.search(r'^P2_KUSACHI_DEATH status=PASS', log_text, re.MULTILINE)),
        transport=bool(re.search(r'^P2_KUSACHI_TRANSPORT status=PASS', log_text, re.MULTILINE)),
        cleanup=bool(re.search(r'^P2_KUSACHI_CLEANUP status=PASS', log_text, re.MULTILINE)),
        captain_down='P2_FIXTURE_CAPTAIN_DOWN' in log_text,
        pass_line=bool(re.search(r'^PASS KUSACHI_GAMEPLAY ', log_text, re.MULTILINE)),
        fail_line=bool(re.search(r'^FAIL KUSACHI_GAMEPLAY ', log_text, re.MULTILINE)),
    )


def classify_gates(log_text):
    """Map receipts to the six arena gates with honest UNTESTED fallbacks.

    PASS requires the event plus a clean guarded run (no captain-down). A run
    without the bound live squad cannot substantiate any gate.
    """
    r = parse_run(log_text)
    guard_clean = not r['captain_down']
    squad_ok = (r['identity_total'] == EXPECTED_SQUAD and r['identity_blue'] == EXPECTED_SQUAD
                and (r['identity_wired'] or 0) > 0)

    def gate(status, method, detail):
        return dict(status=status, method=method, detail=detail)

    gates = {}
    if squad_ok and guard_clean:
        gates['identity_spawn'] = gate('PASS', 'natural',
            'bound live squad total=%d blue=%d wired=%d on %s ui_index=%d'
            % (r['identity_total'], r['identity_blue'], r['identity_wired'], CAVE_ID, UI_INDEX))
    else:
        gates['identity_spawn'] = gate('UNTESTED', 'unobserved',
            'no bound 20-blue live squad receipt in a guard-clean run')

    if r['movement_pass'] == 1 and squad_ok and guard_clean:
        gates['movement_animation'] = gate('PASS', 'natural',
            'squad position delta observed (peak=%.3f units)' % (r['movement_peak'] or 0.0))
    else:
        gates['movement_animation'] = gate('UNTESTED', 'unobserved',
            'no natural squad movement sampled before the run ended')

    teki = r['teki_first']
    enemy_note = ('%d live receiver(s) present' % teki) if teki else 'no live receiver present'
    for name, observed in (('attacks_receivers', r['attack']), ('death_corpse', r['death']),
                           ('cleanup_reentry', r['cleanup'])):
        if observed and guard_clean:
            gates[name] = gate('PASS', 'natural', 'natural engine event observed')
        else:
            gates[name] = gate('UNTESTED', 'unobserved',
                'no natural event before the run ended (%s)' % enemy_note)
    if r['transport'] and guard_clean:
        gates['transport_reward'] = gate('PASS', 'natural', 'natural transport observed')
    elif TREASURE_COUNT_FIELD == 0:
        gates['transport_reward'] = gate('UNTESTED', 'unobserved',
            'source treasure_count_field=0; no verified source loot to transport')
    else:
        gates['transport_reward'] = gate('UNTESTED', 'unobserved',
            'no natural transport before the run ended')
    return gates


def run_summary(log_text):
    """Compact, JSON-serializable summary for evidence bundles."""
    r = parse_run(log_text)
    return dict(cave=r['cave'], ui_index=r['stage'], window_960=r['window_960'],
                squad=dict(total=r['identity_total'], blue=r['identity_blue'], wired=r['identity_wired']),
                movement_peak=r['movement_peak'], teki_first=r['teki_first'],
                extinction_tick=r['extinction'], captain_down=r['captain_down'],
                fixture_pass=r['pass_line'], gates=classify_gates(log_text))
