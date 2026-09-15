"""Private Mamuta natural-observation native arena runner (lane 19, #221/#168).

Stages the batch-4 arena + rules marker + 14-red starting squad and runs the
natural-observation fixture, which drives the captain into the bound Miurin's
territory without forcing any bury, lethal hit or Pikmin action. Validates the
emitted markers and classifies the natural flick/bury, natural-kill and
reset/re-entry gates honestly (behavioural gates stay UNPROVEN when the native
proxy AI does not reproduce them).
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_mamuta_rules import prepare
from scripts.test_pikmin2_surface_native import executable_identity


def validate(text):
    if 'PASS P2_MAMUTA_NATURAL_RUNTIME observe approach reset' not in text:
        raise ValueError('Missing natural runtime completion')
    rows = re.findall(r'P2_MAMUTA_NATURAL_BIRTH id=(\d+) type=(\d+) squad=(\d+) color=(\w+)', text)
    if len(rows) != 1 or rows[0] != ('221001', '24', '14', 'red'):
        raise ValueError('Missing unique identity/squad birth evidence')
    approach = re.findall(r'P2_MAMUTA_NATURAL_APPROACH_RESULT approached=(\d+) min=([-\d.]+) states=([0-9a-fA-F]+)', text)
    if len(approach) != 1 or approach[0][0] != '1':
        raise ValueError('Captain never naturally approached the Miurin territory')
    result = re.findall(
        r'P2_MAMUTA_NATURAL_RESULT died=(\d+) died_tick=(\d+) corpse=(\d+) carried=(\d+) goal=(\d+) control_alive=(\d+) squad=(\d+)',
        text)
    if len(result) != 1 or result[0][5] != '1':
        raise ValueError('Missing natural result with surviving control')
    if 'P2_MAMUTA_NATURAL_RESET' not in text:
        raise ValueError('Missing reset evidence')
    if '[PC GX] DESYNC' in text:
        raise ValueError('GX display list desync')
    # Natural bury events are emitted by the rules module only when the proxy AI
    # itself triggers InteractBury (no forced bury in this fixture).
    natural_plants = len(re.findall(r'^P2_MAMUTA_PLANT kind=\d+ happa=\d+ planted=\d+', text, re.M))
    natural_rejects = len(re.findall(r'^P2_MAMUTA_PLANT_REJECT reason=(\w+)', text, re.M))
    died, died_tick, corpse = int(result[0][0]), int(result[0][1]), int(result[0][2])
    carried, goal = int(result[0][3]), int(result[0][4])
    classify = dict(
        natural_flick_bury='PASS' if natural_plants > 0 else 'UNPROVEN',
        natural_kill='PASS' if died else 'UNPROVEN',
        natural_corpse='PASS' if corpse else 'UNPROVEN',
        natural_carry='PASS' if (carried and goal) else ('PARTIAL' if carried else 'UNPROVEN'),
        reset_reentry='PASS',
    )
    return dict(squad=int(rows[0][2]), approached=True, min_distance=float(approach[0][1]),
                states_seen=approach[0][2], natural_plants=natural_plants,
                natural_rejects=natural_rejects, died=bool(died), died_tick=died_tick,
                corpse=bool(corpse), carried=bool(carried), goal=bool(goal),
                control_alive=True, classify=classify)


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
    p.add_argument('--timeout', type=int, default=180)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if not 1 <= args.timeout <= 300:
        p.error('timeout must be 1..300')
    run(args)
