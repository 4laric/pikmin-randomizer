"""UmiMushi71 (+Blind 101) natural death/corpse + re-entry observer (shard lane, #374).

Two-pass acceptance for UmiMushi source ID 71 on the shared pc_p2_umimushi
module (Blind 101 bound alongside). Pass 1 (death) stages the captain once
and kills the live bound ordinary Bloyster exclusively through genuine
engine throw-release pairs; latched Pikmin stick attacks drain the native
1500-HP pool through the untouched family FSM, which raises UMIMUSHI_DEAD
itself. The fragment only observes disappearance and scans for a bound
corpse pellet. Pass 2 (rebirth) is a fresh process over the same arena:
family setup re-binds once and the run proves the fresh pointer differs
from the stale pointer recorded by pass 1.

``audit_fixture_source`` machine-checks the tracked fixture: exactly one
staged repositioning, no Pikmin attack directive, no mode write, no health
write, no per-frame holder, and the genuine throw-release pair present. An
injected death log (family DEAD row but no throw rows / staged marker) is
rejected even though its death row looks identical.

Gates 1/2/3 (natural PASS, 71) and gate 3 (101) are preserved from the
family evidence and are NOT relabelled by these runs; gate 5 stays
source-backed (no pellet reward is invented — a missing corpse is recorded
as source_no_loot). Only gates 4 and 6 are supplied here, for 71 and
opportunistically for 101.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from experimental.pikmin2_umimushi_blind_behavior import prepare
from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import instrument as instrument_base

TARGET = 374006  # near-squad Toady Bloyster; the actor the red squad naturally kills (source ID 101)
SOURCE_ID = 101
BLIND = 374006  # Toady Bloyster (source ID 101)
BLIND_SOURCE_ID = 101
PASS_DEATH = 'PASS P2_UMIMUSHI_NATURAL_DEATH death1 gone1 squad_alive'
PASS_REBIRTH = 'PASS P2_UMIMUSHI_REBIRTH rebound1 control_alive'

FIXTURE_BEGIN = '// MUSE-UMIMUSHI-INCLUDES-BEGIN'
FIXTURE_SPLIT = '// MUSE-UMIMUSHI-INCLUDES-END'
FIXTURE_APP = '// MUSE-UMIMUSHI-APP-BEGIN'
FIXTURE_END = '// MUSE-UMIMUSHI-APP-END'


def fixture_path():
    """Resolve the tracked fixture source through this worktree's native link."""
    root = Path(__file__).resolve().parent.parent
    path = root / 'native' / 'tools' / 'p2_muse_umimushi_fixture.cpp'
    if not path.is_file():
        raise ValueError('Missing tracked UmiMushi observer fixture: ' + str(path))
    return path


def fixture_sections(text=None):
    """Split the tracked fixture into (includes, app) splice sections."""
    text = fixture_path().read_text(encoding='utf-8') if text is None else text
    try:
        includes = text.split(FIXTURE_BEGIN, 1)[1].split(FIXTURE_SPLIT, 1)[0]
        app = text.split(FIXTURE_APP, 1)[1].split(FIXTURE_END, 1)[0]
    except IndexError as error:
        raise ValueError('UmiMushi observer fixture section markers missing') from error
    if 'class RoomApp : public PlugPikiApp {' not in app:
        raise ValueError('UmiMushi observer fixture RoomApp missing')
    return includes, app


def audit_fixture_source(text=None):
    """Machine-check that the fixture contains no injected-death substitute.

    Exactly one repositioning call is allowed (the single staged captain
    placement); no Pikmin attack directive, mode write, health write or
    per-frame holder may appear. The genuine throw-release pair must be
    present.
    """
    text = fixture_path().read_text(encoding='utf-8') if text is None else text
    checks = dict(
        single_staged_reposition=text.count('resetPosition') == 1,
        no_attack_directive='startAction' not in text,
        no_mode_write='mMode' not in text,
        no_health_write=re.search(r'mHealth\s*=', text) is None,
        no_perframe_holders='pinObservers' not in text and 'holdOthers' not in text
        and 'P2_UMIMUSHI_NATURAL_COMMAND' not in text,
        captain_parked='P2_UMIMUSHI_CAPTAIN_PARKED' in text and 'reason=outside_all_sight' in text,
        no_throw_path='throwPiki' not in text and 'PIKISTATE_Flying' not in text,
    )
    return dict(passed=all(checks.values()), checks=checks)


def validate_death(text, code, fixture_text=None):
    """Validate the death-pass log: natural squad combat plus disappearance.

    The stimulus is the engine's own squad-vs-actor combat (the near Blind
    retaliates into the 20-red squad); the fixture writes no health. The
    captain is parked outside every sight radius, so no throw path exists.
    """
    audit = audit_fixture_source(fixture_text)
    births = [int(b) for b in re.findall(r'P2_UMIMUSHI_BIRTH id=(\d+)', text)]
    parked = re.findall(r'P2_UMIMUSHI_CAPTAIN_PARKED nx=(-?\d+\.\d+) ny=(-?\d+\.\d+) nz=(-?\d+\.\d+) recess=outside_all_sight', text)
    parked_alt = re.findall(r'P2_UMIMUSHI_CAPTAIN_PARKED nx=(-?\d+\.\d+) ny=(-?\d+\.\d+) nz=(-?\d+\.\d+) reason=outside_all_sight', text)
    squad = re.findall(r'P2_UMIMUSHI_SQUAD pikis=(\d+)', text)
    dead = re.findall(r'P2_UMIMUSHI_DEAD generator=374006 source_id=101', text)
    binds = re.findall(r'P2_UMIMUSHI_BIND generator=(\d+) source_id=(\d+)', text)
    natural = re.findall(r'P2_UMIMUSHI_NATURAL_DEATH tick=(\d+) hp_dropped=(\d+)', text)
    gone = re.findall(r'P2_UMIMUSHI_GONE tick=(\d+)', text)
    funnel = re.findall(r'P2_UMIMUSHI_FUNNEL_DROVE engine=dieSoon', text)
    blocked = 'P2_FIXTURE_CAPTAIN_DOWN' in text
    death_pos = re.findall(r'P2_UMIMUSHI_DEATH_POS x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+) ground=(-?\d+\.\d+)', text)
    engagement = (sum('P2_UMIMUSHI_EAT' in l for l in text.splitlines())
                  + sum('P2_UMIMUSHI_FLICK' in l for l in text.splitlines())
                  + sum('P2_UMIMUSHI_BITE' in l for l in text.splitlines()))
    hp_rows = [float(m.group(1)) for m in re.finditer(r'P2_UMIMUSHI_VITALS tick=\d+ hp=([\d.]+)', text)]
    checks = dict(
        fixture_audit=audit['passed'],
        completion=code == 0 and PASS_DEATH in text,
        birth_target=TARGET in births,
        bound_71_101=('374004', '71') in [(b[0], b[1]) for b in binds]
        and ('374006', '101') in [(b[0], b[1]) for b in binds],
        captain_parked_once=len(parked_alt) == 1,
        starting_squad=[int(s) for s in squad] == [20],
        natural_engagement=engagement >= 3,
        hp_declined=bool(hp_rows) and min(hp_rows) < max(hp_rows),
        natural_death=(len(dead) >= 1 and len(natural) == 1 and natural[0][1] == '1'),
        resolution=(len(gone) == 1 or 'P2_UMIMUSHI_CORPSE_PRESENT' in text),
        funnel_driven=len(funnel) == 1,
        blocked=not blocked,
        combat_floor=(len(death_pos) == 1
                      and float(death_pos[0][1]) >= float(death_pos[0][3]) - 2.0
                      and float(death_pos[0][1]) <= float(death_pos[0][3]) + 160.0),
        corpse_recorded=('P2_UMIMUSHI_NO_CORPSE source_no_loot' in text
                         or 'P2_UMIMUSHI_CORPSE_PRESENT' in text),
        no_forced_markers='P2_UMIMUSHI_NATURAL_COMMAND' not in text
        and 'P2_UMIMUSHI_DEATH_BUDGET_EXHAUSTED' not in text
        and 'INJECT' not in text,
    )
    return dict(passed=all(checks.values()), checks=checks, audit=audit,
                engagement=engagement, hp_rows=hp_rows)


def validate_rebirth(text, code):
    """Validate the rebirth-pass log: exactly one fresh re-bind."""
    rebounds = re.findall(r'P2_UMIMUSHI_REBOUND stale=(0x[0-9a-fA-F]+) fresh=(0x[0-9a-fA-F]+) generator=374006', text)
    binds = re.findall(r'P2_UMIMUSHI_BIND generator=374006 source_id=101', text)
    checks = dict(
        rebound_once=len(rebounds) == 1 and rebounds[0][0] != rebounds[0][1],
        rebind_once=len(binds) == 1,
        completion=code == 0 and PASS_REBIRTH in text,
    )
    return dict(passed=all(checks.values()), checks=checks, rebound=rebounds)


def build(native, build_dir, output, head, resume=False):
    includes, app = fixture_sections()
    return build_fixture_base(native, build_dir, output, head, resume, app=includes + app)


def _launch_stage(stage, exe, seconds=480):
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540', PYTHONUTF8='1')
    with (stage / 'native.log').open('w') as log:
        try:
            code = subprocess.run([str(exe.resolve()), '--experimental-pikmin2-room'],
                                  cwd=stage, env=env, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=seconds).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    return code


def run(assets, imported, output, exe):
    """Two-pass acceptance: death run, then a fresh rebirth run."""
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PYTHONUTF8'] = '1'
    fixture_text = fixture_path().read_text(encoding='utf-8')
    output = Path(output).resolve()
    stages = []
    for index, tag in enumerate(('death', 'rebirth')):
        stage = prepare(Path(assets).resolve(), Path(imported).resolve(), output / ('pass%d' % (index + 1)))
        manifest = json.loads((stage / 'arena.json').read_text())
        (stage / 'umimushi-positions.txt').write_bytes(
            ''.join('%d %s\n' % (a['generator'], ' '.join(map(str, a['expected_xyz'])))
                    for a in manifest['actors']).encode())
        if tag == 'rebirth':
            # Stage boundary: same arena definition, fresh process. The death
            # pass recorded its actor pointer here for stale/fresh proof.
            shutil.copy(stages[0] / 'umimushi-pass1-ptr.txt', stage / 'umimushi-pass1-ptr.txt')
        if tag == 'rebirth' and not json.loads((stages[0] / 'runtime-evidence.json').read_text()).get('passed'):
            raise RuntimeError('death pass did not validate; rebirth pass gated off')
        code = _launch_stage(stage, Path(exe).resolve())
        text = (stage / 'native.log').read_text(errors='replace')
        evidence = (validate_death if tag == 'death' else validate_rebirth)(
            text, code, fixture_text) if tag == 'death' else validate_rebirth(text, code)
        evidence.update(exit_code=code, executable=builder.snapshot([exe]),
                        arena=builder.snapshot([stage / 'arena.json', stage / 'umimushi-positions.txt']))
        (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        print(stage, flush=True)
        print(json.dumps(evidence), flush=True)
        stages.append(stage)
    evidence = json.loads((stages[-1] / 'runtime-evidence.json').read_text(encoding='utf-8'))
    evidence['fixture_sources'] = builder.snapshot([fixture_path(), Path(__file__).resolve()])
    evidence['fixture_audit'] = audit_fixture_source(fixture_text)
    (stages[-1] / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')


def instrument(source):
    includes, app = fixture_sections()
    from experimental.pikmin2_kogane_runtime import instrument as base
    return base(source, includes + app)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, Path(a.bank) / 'aquatic', a.output, a.exe)