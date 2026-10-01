"""Private Mamuta revisit/re-entry runner (lane 19, #221/#168).

Re-runs the Mamuta Revisit fixture in the SAME Pod-arena stage directory that a
prior :mod:`scripts.pikmin2_mamuta_pod_native` natural run already credited, so a
fresh process re-births the Mamuta from the staged ``default.gen`` and re-observes
the natural sequence. The persisted ``p2-economy.txt`` (exactly-once ledger) makes
the re-delivery dedupe with ``new=0``, which this runner verifies as the
revisit/persistence gate. Nothing is forced; the validator classifies missing
behaviour as UNPROVEN.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from scripts.test_pikmin2_surface_native import executable_identity

REVISIT_FIXTURE = 'scripts/pikmin2_mamuta_revisit_fixture.inc'


def _line(text, pattern):
    matches = re.findall(pattern, text, re.M)
    if len(matches) != 1:
        raise ValueError('Expected exactly one ' + pattern)
    return matches[0]


def validate(text):
    """Parse the revisit markers and classify re-entry/reward honestly."""
    down = re.findall(r'P2_MAMUTA_REVISIT_CAPTAIN_DOWN tick=(\d+) health=([-\d.]+)', text)
    if len(down) > 1:
        raise ValueError('Expected at most one captain-down marker')
    captain_down = bool(down)
    if ('PASS P2_MAMUTA_REVISIT_RUNTIME observe approach receipt_revisit reset' not in text
            and 'PASS P2_MAMUTA_REVISIT_RUNTIME captain_down' not in text):
        raise ValueError('Missing revisit runtime completion')
    birth = _line(text, r'P2_MAMUTA_REVISIT_BIRTH id=(\d+) type=(\d+) squad=(\d+) color=(\w+)')
    if birth != ('221001', '24', '14', 'red'):
        raise ValueError('Missing re-birth identity/squad evidence')
    ready = _line(text, r'P2_MAMUTA_REVISIT_READY prior_pokos=(\d+)')
    prior_pokos = int(ready[0])
    if prior_pokos < 2:
        raise ValueError('Pod economy did not persist a prior reward')
    approach = _line(text, r'P2_MAMUTA_REVISIT_APPROACH_RESULT approached=(\d+) min=([-\d.]+) states=([0-9a-fA-F]+)')
    if approach[0] != '1':
        raise ValueError('Captain never naturally approached the Miurin territory')
    result = _line(text, r'P2_MAMUTA_REVISIT_RESULT died=(\d+) died_tick=(\d+) corpse=(\d+) '
                         r'carried=(\d+) goal=(\d+) pokos=(\d+) prior_pokos=(\d+) '
                         r'control_alive=(\d+) squad=(\d+)')
    died, died_tick, corpse, carried, goal, pokos, prior2, control = (int(result[i]) for i in range(8))
    if control != 1:
        raise ValueError('Missing revisit result with surviving control')
    if prior2 != prior_pokos:
        raise ValueError('Prior-Pokos marker mismatch')
    if 'P2_MAMUTA_REVISIT_RESET' not in text:
        raise ValueError('Missing reset evidence')
    if '[PC GX] DESYNC' in text:
        raise ValueError('GX display list desync')
    # The re-delivery is emitted by the shared preview as
    # "[Pikipelago] P2_POD_RECEIPT id=corpse:...mamuta:<gen> ... new=<0|1> ...".
    receipts = re.findall(
        r'P2_POD_RECEIPT id=corpse:\S*?mamuta:(\d+) value=(\d+) new=(\d+) pokos=(\d+)', text)
    mamuta = [row for row in receipts if row[0] == '221001']
    deduped = [row for row in mamuta if row[2] == '0']
    duplicated = [row for row in mamuta if row[2] == '1']
    # Exactly-once: the fixture hard-requires pokos==prior_pokos, and any observed
    # re-delivery must be deduped (new=0), never a fresh credit (new=1).
    if duplicated:
        raise ValueError('Reward was duplicated on re-entry')
    if mamuta and not deduped:
        raise ValueError('Re-delivery observed but not deduped')
    unchanged = (pokos == prior_pokos)
    if not unchanged:
        raise ValueError('Reward total changed across revisit')
    classify = dict(
        reentry_ready='PASS',
        fresh_identity='PASS',
        natural_rekill='PASS' if died else ('BLOCKED(captain_down)' if captain_down else 'UNPROVEN'),
        natural_recorpse='PASS' if corpse else 'UNPROVEN',
        natural_recarry='PASS' if (carried and goal) else 'UNPROVEN',
        reward_not_duplicated='PASS' if unchanged and not duplicated else 'FAIL',
        receipt_deduped='PASS' if deduped else 'UNPROVEN',
    )
    return dict(squad=int(birth[2]), approached=True, min_distance=float(approach[1]),
                states_seen=approach[2], prior_pokos=prior_pokos, final_pokos=pokos,
                died=bool(died), died_tick=died_tick, corpse=bool(corpse),
                carried=bool(carried), goal=bool(goal), control_alive=True,
                captain_down=captain_down, mamuta_receipts=mamuta,
                deduped_receipt=deduped[0] if deduped else None,
                classify=classify)


def run(args):
    """Re-run the revisit fixture inside an existing staged Pod-arena directory."""
    stage = args.stage.resolve()
    if not (stage / 'p2-pod.txt').is_file():
        raise ValueError('Stage directory is not a Pod arena: ' + str(stage))
    if not (stage / 'p2-economy.txt').is_file():
        raise ValueError('Stage directory has no persisted economy (run the natural Pod run first)')
    identity = executable_identity(args.exe)
    env = dict(args.env, SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540',
               PATH='C:/msys64/mingw64/bin;' + args.env.get('PATH', ''))
    log_path = stage / 'native-revisit.log'
    with log_path.open('w') as stream:
        process = subprocess.run([str(args.exe), '--experimental-pikmin2-room'], cwd=stage, env=env,
                                 stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
    if process.returncode:
        raise RuntimeError(f'Native revisit exit {process.returncode}: {stage}')
    result = dict(executable=identity, stage=str(stage),
                  evidence=validate(log_path.read_text(errors='replace')))
    (stage.parent / 'revisit-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--stage', type=Path, required=True,
                   help='stage directory produced by a prior natural Pod run')
    p.add_argument('--timeout', type=int, default=300)
    args = p.parse_args()
    args.exe = args.exe.resolve()
    if not 1 <= args.timeout <= 300:
        p.error('timeout must be 1..300')
    args.env = dict(__import__('os').environ)
    run(args)
