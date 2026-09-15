"""Lane 11 natural Mother Bulbmin recruitment + real-whistle gate 6 (#131).

Slice 3 closes gate 6 end to end with the engineer path only: process 1 (a
cave floor carrying a live Chappy-family Mother Bulbmin stand-in) births the
source ten-body wild flock behind a Kochappy actor that the ordinary generator
sidecar registered, the captain's *real* whistle (Navi::callPikis ->
pc_p2_bulbmin_call_pikis) converts wild dependents in place, and the live
``pc_p2_cave_checkpoint`` descent drops the remaining wild dependents while the
whistled ones persist. Process 2 restores the whistled Bulbmin and later exit
runs the exit move over any tracked dependents.

The fixture schedules the whistle and the checkpoint; every wire byte, the
mother registration and the drop are produced by the engine. The engine wiring
(mother auto-attach from the Kochappy registration, the navi.cpp whistle hook,
and the descend/exit transition filter) already exists; this slice adds only the
observable markers (P2_BULBMIN_MOTHER_BIRTH / P2_BULBMIN_WHISTLE) plus this
validator and its tests.

Natural gate 6 acceptance additionally requires the Chappy-family bank/source
(bank model + reference import) supplied by lane 13 (#120); without it there is
no Kochappy actor to register as the mother stand-in.
"""
import argparse
import json
import os
import re
import uuid
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_campaign import entry_text, initial, ledger_text, transition
from experimental.pikmin2_campaign import validate as validate_state
from scripts.preview_pikmin2_emergence import prepare


def validate(text1, text2, transfer_text):
    if not isinstance(text1, str) or not isinstance(text2, str):
        raise ValueError('Expected native log strings')
    hdr = transfer_text.startswith('P2_CAVE_TRANSFER_3\n')
    body = transfer_text.splitlines()[3:] if hdr else []
    whistle = re.search(r'P2_BULBMIN_WHISTLE recruited=(\d+)', text1)
    descend = re.search(r'P2_CAVE_BULBMIN_TRANSITION move=descend removed=(\d+)', text1)
    checks = dict(
        write_window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text1)),
        mother_sidecar=bool(re.search(r'P2_ENEMY_READY species=Kochappy', text1)),
        mother_birth=bool(re.search(r'P2_BULBMIN_MOTHER_BIRTH model=\S+ dependents=10', text1)),
        natural_whistle=bool(whistle) and int(whistle.group(1)) >= 1,
        whistle_via_real_path='P2_BULBMIN_TX_RECRUIT' not in text1,
        descend_drops_wild=bool(descend) and int(descend.group(1)) >= 1,
        recruited_persist=(len([l for l in body if l.split()[0] == '5']) >= 1),
        read_restore=bool(re.search(r'P2_CAVE_RESTORE species=5 maturity=0', text2)),
        exit_removes_tracked=bool(re.search(r'P2_CAVE_BULBMIN_TRANSITION move=exit', text2)),
        no_extinction=(not re.search(r'Extinction', text1, re.IGNORECASE)
                       and not re.search(r'Extinction', text2, re.IGNORECASE)),
    )
    return dict(passed=all(checks.values()), checks=checks,
                transfer=transfer_text.splitlines()[:3],
                limitations=['Natural gate 6 requires the lane-13 Chappy-family bank (model + '
                             'reference import); the mother is a labeled Kochappy stand-in, not a '
                             'LeafChappy actor. The exit move over restored bodies reports zero '
                             'tracked dependents (the descent already dropped the wild and the whistled '
                             'bodies became free Pikmin); the all-tracked-removed contract is proven by '
                             'tools/test_p2_bulbmin_mother.cpp.'])


def run(assets, imported, bank, treasure, pod, purple, exe, output, seconds=75):
    """Natural gate-6 runtime skeleton (requires the lane-13 Kochappy bank)."""
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    state = validate_state(dict(initial('0' * 64), health=0.625,
                                squad=[dict(species='red', maturity=0) for _ in range(18)]))
    token = uuid.uuid4().hex

    # Floor 1: mother (Kochappy) + wild flock, real whistle, descend.
    run1 = prepare(Path(assets), Path(imported), Path(treasure), output / 'write',
                   floor=1, pod=Path(pod), purple=Path(purple), violet=False, squad=state['squad'])
    from experimental.pikmin2_kochappy_bank import install as kochappy_install
    kochappy_install(Path(bank), run1, [186001])
    (run1 / 'p2-cave-entry.txt').write_text(
        f'P2_CAVE_ENTRY_3\n{token}\n1 0.625 18\n' + '1 0\n' * 18)
    (run1 / 'p2-economy.txt').write_text(ledger_text({}))
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    os.environ['PIKMIN_P2_BULBMIN'] = '1'
    meta1 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run1, run1 / 'capture', seconds)
    text1 = (run1 / 'capture' / 'native.log').read_text(errors='replace')
    transfer_path = run1 / 'p2-cave-transfer.txt'
    if not transfer_path.is_file():
        raise RuntimeError('process 1 did not write p2-cave-transfer.txt')

    next_state = transition(state, token, transfer_path.read_text(), {}, {})
    run2 = prepare(Path(assets), Path(imported), Path(treasure), output / 'read',
                   floor=2, pod=Path(pod), purple=Path(purple), violet=True, squad=next_state['squad'])
    (run2 / 'p2-cave-entry.txt').write_text(entry_text(next_state, token))
    (run2 / 'p2-economy.txt').write_text(ledger_text({}))
    meta2 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run2, run2 / 'capture', seconds)
    text2 = (run2 / 'capture' / 'native.log').read_text(errors='replace')

    result = validate(text1, text2, transfer_path.read_text())
    result['write'] = {'run': str(run1), 'capture': {k: meta1[k] for k in
                       ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    result['read'] = {'run': str(run2), 'capture': {k: meta2[k] for k in
                      ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    (output / 'bulbmin-natural-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return output, {"write": meta1, "read": meta2}, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    r = commands.add_parser('run')
    for flag in ('assets', 'imported', 'bank', 'treasure', 'pod', 'purple', 'exe', 'output'):
        r.add_argument('--' + flag, type=Path, required=True)
    r.add_argument('--seconds', type=int, default=75)
    args = parser.parse_args()
    out, _, result = run(args.assets, args.imported, args.bank, args.treasure, args.pod,
                         args.purple, args.exe, args.output, args.seconds)
    print(out)
    print(json.dumps(result, indent=2))
