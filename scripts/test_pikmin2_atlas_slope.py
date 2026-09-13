"""Stage a private source-position Atlas haul; never edit an existing session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from experimental.pikmin2_campaign import install_snow
from experimental.pikmin2_generator_pose import write_position, validate_position
from experimental.pikmin2_roster import install
from scripts.preview_pikmin2_emergence import prepare
from scripts.preview_pikmin2_room import records
from scripts.preview_pikmin2_room import prepare as prepare_p1_control


def stage(root, assets, output, source=True, floor=2):
    imported = root / 'output/pikmin2-polish119/import'
    pod = root / ('output/pikmin2-purple113/atlas-01' if floor == 2 else 'output/pikmin2-pod111/import-02')
    run = prepare(assets, imported, root/'output/pikmin2-room105/treasure.mod', output,
                  floor=floor, pod=pod, purple=root/'output/pikmin2-purple113/import-05')
    roster = install(root/'output/p2-roster-batch/content', run, floor, assets, imported)
    install_snow(root/'output/p2-next/snow', run)
    if source and floor == 2:
        actor = next(a for a in roster['actors'] if a['catalog_id'] == 'map01')
        position = actor['source_projected_position']
        if position != [0, 10, 640]:
            raise ValueError('Unexpected Atlas source projection')
        gen = run/'assets/dataDir/stages/chal0/default.gen'
        rows = [bytearray(r) for r in records(gen)]
        found = [r for r in rows if struct.unpack_from('<I', r, 8)[0] == actor['native_generator_id']]
        if len(found) != 1:
            raise ValueError('Ambiguous Atlas generator')
        write_position(found[0], position)
        validate_position(found[0], position)
        # install() has already replaced this generator with a private file.
        gen.write_bytes(gen.read_bytes()[:24] + b''.join(rows))
        actor['position'] = position
        actor['placement_override'] = 'Private #123 source-position regression only'
        (run/'p2-roster.json').write_text(json.dumps(roster, indent=2)+'\n')
    (run/'p2-cargo-carry.txt').touch()
    return run


def validate(log, roster, economy):
    items = [a for a in roster['actors'] if a['category'] == 'treasure']
    target = items[1] if len(items) > 1 else items[0]
    if 'PASS P2 second cargo actual native transport and Pod delivery' not in log or 'FAIL ' in log:
        raise ValueError('Incomplete or failed native haul')
    start = re.search(r'P2_CARGO_START_XYZ ([-\d.]+) ([-\d.]+) ([-\d.]+)', log)
    if not start or any(abs(float(v)-expected) > .1 for v, expected in zip(start.groups(), target['position'])):
        raise ValueError('Native cargo start does not match staged position')
    events = re.findall(r'P2_POD_RECEIPT id=(\S+) value=(\d+) new=1 pokos=(\d+) seeds=0', log)
    expected = ('treasure:'+target['instance_id'], str(target['value']), str(target['value']))
    if events != [expected]:
        raise ValueError('Expected exactly one actual cargo receipt')
    if economy.split() != ['P2_ECONOMY_1', 'treasure:'+target['instance_id'], str(target['value'])]:
        raise ValueError('Persisted cargo economy differs')
    return dict(instance=target['instance_id'], value=target['value'], native_start=[float(v) for v in start.groups()])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'assets', 'output', 'exe'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--flat', action='store_true')
    p.add_argument('--floor', type=int, choices=(1, 2), default=2)
    p.add_argument('--p1-control', action='store_true', help='P1 scaffold hauling/combat/corpse control in the concrete preview room')
    p.add_argument('--timeout', type=int, default=360)
    a = p.parse_args()
    if a.p1_control and (a.flat or a.floor != 2):
        p.error('--p1-control cannot be combined with --flat or --floor 1')
    if a.p1_control:
        run = prepare_p1_control(a.assets.resolve(), a.root.resolve()/'output/pikmin2-room105', a.output.resolve())
    else:
        run = stage(a.root.resolve(), a.assets.resolve(), a.output.resolve(), not a.flat, a.floor)
    exe = a.exe.resolve()
    evidence = dict(run=str(run), executable=str(exe),
                    executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                    source_position=not (a.flat or a.p1_control), floor=None if a.p1_control else a.floor,
                    synthetic_purple_identity=a.floor == 2 and not a.p1_control, p1_control=a.p1_control,
                    injected_transport_assignment=True, natural_gameplay=False)
    print(run, flush=True)
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH', ''))
    with (run/'native.log').open('w') as log:
        try:
            result = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=run,
                                    env=env, stdout=log, stderr=subprocess.STDOUT, timeout=a.timeout)
            evidence['returncode'] = result.returncode
        except subprocess.TimeoutExpired:
            evidence['timeout'] = True
    text = (run/'native.log').read_text(errors='replace')
    evidence['passed'] = False
    if evidence.get('returncode') == 0:
        try:
            if a.p1_control:
                expected = 'PASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery'
                if expected not in text or 'FAIL ' in text or 'P2_POD_RECEIPT' in text:
                    raise ValueError('Incomplete P1 scaffold control or unexpected Pod reward')
            else:
                evidence['haul'] = validate(text, json.loads((run/'p2-roster.json').read_text()),
                                            (run/'p2-economy.txt').read_text())
            evidence['passed'] = True
        except (ValueError, OSError) as error:
            evidence['validation_error'] = str(error)
    evidence['log_sha256'] = hashlib.sha256((run/'native.log').read_bytes()).hexdigest()
    (run/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence), flush=True)
    raise SystemExit(0 if evidence['passed'] else 1)


if __name__ == '__main__':
    main()
