"""Private Mamuta Pod-arena native runner (lane 19, #221/#168).

Stages the batch-4 arena + rules marker + 10-red starting squad *with* the
cargo-enabled Pod (converted ``treasure.mod``/``pod.mod`` + single ``pr05``
treasure actor) and runs the Pod-observation fixture. The fixture drives the
captain into the bound Miurin's territory without forcing any bury, lethal hit
or Pikmin action, so natural pickup and the Pod family receipt are observed on
their own.

The unassisted variant never claims natural acceptance: its validator classifies
missing behaviour as UNPROVEN. The ``--assisted`` variant assigns native
Transport directly after a grace period and is labelled ``assisted=1``.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_mamuta_rules import prepare
from scripts.test_pikmin2_surface_native import executable_identity

POD_FIXTURE = 'scripts/pikmin2_mamuta_pod_fixture.inc'
ASSISTED_FIXTURE = 'scripts/pikmin2_mamuta_pod_assisted_fixture.inc'


def _line(text, pattern):
    matches = re.findall(pattern, text, re.M)
    if len(matches) != 1:
        raise ValueError('Expected exactly one ' + pattern)
    return matches[0]


def validate(text, assisted=False):
    """Parse the Pod-arena markers and classify carry/receipt honestly."""
    down = re.findall(r'P2_MAMUTA_POD_CAPTAIN_DOWN tick=(\d+) health=([-\d.]+)', text)
    if len(down) > 1:
        raise ValueError('Expected at most one captain-down marker')
    captain_down = bool(down)
    if assisted:
        if 'PASS P2_MAMUTA_POD_RUNTIME assisted approach receipt reset' not in text:
            raise ValueError('Missing Pod runtime completion')
    elif ('PASS P2_MAMUTA_POD_RUNTIME observe approach receipt reset' not in text
          and 'PASS P2_MAMUTA_POD_RUNTIME captain_down' not in text):
        raise ValueError('Missing Pod runtime completion')
    birth = _line(text, r'P2_MAMUTA_POD_BIRTH id=(\d+) type=(\d+) squad=(\d+) color=(\w+)')
    if birth != ('221001', '24', '10', 'red'):
        raise ValueError('Missing unique identity/squad birth evidence')
    ready = _line(text, r'P2_POD_READY treasure=(\S+) value=(\d+) weight=(\d+) capacity=(\d+) pokos=(\d+)')
    approach = _line(text, r'P2_MAMUTA_POD_APPROACH_RESULT approached=(\d+) min=([-\d.]+) states=([0-9a-fA-F]+)')
    if approach[0] != '1':
        raise ValueError('Captain never naturally approached the Miurin territory')
    result = _line(text, r'P2_MAMUTA_POD_RESULT (?:assisted=(\d+) )?died=(\d+) died_tick=(\d+) '
                         r'corpse=(\d+) carried=(\d+) goal=(\d+) pokos=(\d+) control_alive=(\d+) squad=(\d+)')
    if assisted:
        if result[0] != '1':
            raise ValueError('Assisted variant must record assisted=1')
    elif result[0] not in (None, ''):
        raise ValueError('Unassisted variant must not report assisted transport')
    died, died_tick, corpse, carried, goal, pokos, control = (int(result[i]) for i in range(1, 8))
    if control != 1:
        raise ValueError('Missing Pod result with surviving control')
    if 'P2_MAMUTA_POD_RESET' not in text:
        raise ValueError('Missing reset evidence')
    if '[PC GX] DESYNC' in text:
        raise ValueError('GX display list desync')
    # Native emits this receipt through pc_p2_preview as "[Pikipelago] P2_POD_RECEIPT ...",
    # so do not anchor to the line start.
    receipt = re.findall(
        r'P2_POD_RECEIPT id=corpse:\S*?mamuta:(\d+) value=(\d+) new=(\d+) pokos=(\d+)', text)
    mamuta = [row for row in receipt if row[0] == '221001']
    if len(mamuta) != 1:
        mamuta = []
    assist_markers = len(re.findall(r'^P2_MAMUTA_POD_ASSIST carriers=\d+ assisted=1', text, re.M))
    classify = dict(
        pod_ready='PASS',
        natural_kill='PASS' if died else ('BLOCKED(captain_down)' if captain_down else 'UNPROVEN'),
        natural_corpse='PASS' if corpse else 'UNPROVEN',
        natural_carry='PASS' if (not assisted and carried and goal) else 'UNPROVEN',
        assisted_carry='PASS' if (assisted and assist_markers and carried) else 'UNPROVEN',
        pod_receipt='PASS' if mamuta else 'UNPROVEN',
    )
    return dict(squad=int(birth[2]), approached=True, min_distance=float(approach[1]),
                states_seen=approach[2], pod_treasure=ready[0], pod_weight=int(ready[2]),
                pod_capacity=int(ready[3]), died=bool(died), died_tick=died_tick,
                corpse=bool(corpse), carried=bool(carried), goal=bool(goal), pokos=pokos,
                control_alive=True, assisted=bool(assisted), assist_markers=assist_markers,
                captain_down=captain_down, mamuta_receipt=mamuta[0] if mamuta else None,
                classify=classify)


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    identity = executable_identity(args.exe)
    stage = prepare(args.assets, args.imported, args.output,
                    cargo=dict(pod_package=args.pod_package))
    (args.output / 'launch.json').write_text(json.dumps(dict(
        executable=identity, stage=str(stage), assisted=bool(args.assisted),
        fixture=ASSISTED_FIXTURE if args.assisted else POD_FIXTURE), indent=2))
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540',
               PATH='C:/msys64/mingw64/bin;' + os.environ['PATH'])
    with (stage / 'native.log').open('w') as stream:
        process = subprocess.run([str(args.exe), '--experimental-pikmin2-room'], cwd=stage, env=env,
                                 stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
    if process.returncode:
        raise RuntimeError(f'Native exit {process.returncode}: {stage}')
    result = dict(executable=identity, stage=str(stage), assisted=bool(args.assisted),
                  evidence=validate((stage / 'native.log').read_text(errors='replace'),
                                    assisted=bool(args.assisted)))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('assets', 'imported', 'exe', 'output', 'pod_package'):
        p.add_argument('--' + key.replace('_', '-'), dest=key, type=Path, required=True)
    p.add_argument('--assisted', action='store_true')
    p.add_argument('--timeout', type=int, default=300)
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.resolve())
    if not 1 <= args.timeout <= 300:
        p.error('timeout must be 1..300')
    run(args)
