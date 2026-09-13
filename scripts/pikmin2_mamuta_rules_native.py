"""Private Mamuta P2-rules native arena runner (batch 4 + death gate, #221).

Stages the batch-2 arena plus rules marker plus the 10-red starting squad
(generator 221003), runs the privately built rules fixture, and validates the
log: exact identity, P2 bury -> flower-stage planted sprout with mePikis
counting, the 99-planted cap rejection, captain damage exactly 5.0 without
burial, the death/corpse gate (accepted non-invincible lethal attack, natural
death, and a native carryable Miurin carcass), and reset disabling the rules.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_mamuta_rules import prepare, parse_plant_events, validate_plant_events
from scripts.test_pikmin2_surface_native import executable_identity


def validate(text):
    if 'PASS P2_MAMUTA_RULES_RUNTIME bury flower_stage cap99 navi_damage5 death corpse reset' not in text:
        raise ValueError('Missing rules runtime completion')
    rows = re.findall(r'P2_MAMUTA_FIXTURE_BIRTH id=(\d+) type=(\d+) squad=(\d+) color=(\w+)', text)
    if len(rows) != 1 or rows[0] != ('221001', '24', '10', 'red'):
        raise ValueError('Missing unique identity/squad birth evidence')
    bury = re.findall(r'P2_MAMUTA_FIXTURE_BURY forced=(\d+) planted_before=(\d+)', text)
    if len(bury) != 1 or bury[0][0] != '3':
        raise ValueError('Missing forced bury evidence')
    if 'P2_MAMUTA_FIXTURE_CAP rejected_at=99' not in text:
        raise ValueError('Missing 99-planted cap rejection')
    navi = re.findall(r'P2_MAMUTA_FIXTURE_NAVI damage=5.0 health=([-\d.]+)', text)
    if len(navi) != 1:
        raise ValueError('Missing captain damage evidence')
    planted = re.findall(r'P2_MAMUTA_FIXTURE_PLANTED planted=(\d+) expected_min=(\d+)', text)
    if len(planted) != 1 or int(planted[0][0]) < int(planted[0][1]):
        raise ValueError('Missing planted-sprout count evidence')
    if 'P2_MAMUTA_CARCASS_CONFIG tkmu=1' not in text:
        raise ValueError('Missing native Miurin carcass config')
    corpse_type = re.findall(r'P2_MAMUTA_DEATH_CORPSETYPE corpse_type=(\d+)', text)
    if len(corpse_type) != 1 or corpse_type[0] != '1':
        raise ValueError('P1 Miurin corpse type must be LeaveCorpse')
    hit = re.findall(r'P2_MAMUTA_DEATH_HIT accepted=1 invincible=0 health_before=([-\d.]+) stored=([-\d.]+)', text)
    if len(hit) != 1 or float(hit[0][0]) <= 0.0:
        raise ValueError('Missing accepted lethal attack evidence')
    died = re.findall(r'P2_MAMUTA_DEATH_DIED tick=(\d+) health=0.0', text)
    if len(died) != 1:
        raise ValueError('Missing natural death evidence')
    result = re.findall(r'P2_MAMUTA_DEATH_RESULT died_tick=(\d+) corpse=(\d+)', text)
    if len(result) != 1 or result[0][1] != '1':
        raise ValueError('Mamuta corpse gate requires an observed carcass')
    pellets = re.findall(r'P2_MAMUTA_DEATH_PELLETS total=(\d+) withview=(\d+)', text)
    if len(pellets) != 1 or pellets[0][1] != '1':
        raise ValueError('Corpse pellet must carry the actor view')
    if 'P2_MAMUTA_FIXTURE_RESET' not in text:
        raise ValueError('Missing reset evidence')
    events = parse_plant_events(text)
    validate_plant_events(events, min_plants=3)
    if 'cap99' not in events['rejects']:
        raise ValueError('Native cap99 rejection not logged')
    if not events['navi'] or any(h['damage'] != 5.0 for h in events['navi']):
        raise ValueError('Captain damage events must be the P2 value 5.0')
    if '[PC GX] DESYNC' in text:
        raise ValueError('GX display list desync')
    return dict(squad=int(rows[0][2]), forced_buries=int(bury[0][0]),
                plants=events['plants'], rejects=events['rejects'],
                navi_health_after=float(navi[0]),
                planted_count=int(planted[0][0]),
                death_tick=int(died[0]), corpse=bool(int(result[0][1])),
                corpse_pellets_total=int(pellets[0][0]), reset=True)


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    identity = executable_identity(args.exe)
    stage = prepare(args.assets, args.imported, args.output)
    (args.output / 'launch.json').write_text(json.dumps(dict(executable=identity, stage=str(stage)), indent=2))
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540',
               PATH='C:/msys64/mingw64/bin;' + os.environ['PATH'])
    with (stage / 'native.log').open('w') as stream:
        process = subprocess.run([str(args.exe), '--experimental-pikmin2-room'], cwd=stage, env=env,
                                 stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
    if process.returncode:
        raise RuntimeError(f'Native exit {process.returncode}: {stage}')
    result = dict(executable=identity, stage=str(stage),
                  evidence=validate((stage / 'native.log').read_text(errors='replace')))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('assets', 'imported', 'exe', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--timeout', type=int, default=90)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if not 1 <= args.timeout <= 180:
        p.error('timeout must be 1..180')
    run(args)
