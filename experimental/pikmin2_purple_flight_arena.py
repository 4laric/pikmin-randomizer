"""Regenerate a private Purple flight arena with the current starting-squad overlay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

from experimental.pikmin2_purple_direct import write_profile
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from scripts.preview_pikmin2_room import prepare, records


def stage(assets, converted, presentation, output, motion=None):
    # Presentation contributes only known imported models/configs. The stage,
    # squad and overlay are freshly generated, never copied from an old arena.
    source_models = presentation / 'assets/dataDir/courses/pikmin2room'
    configs = {name: (presentation / name).read_bytes() for name in ('p2-purple.txt', 'p2-pod.txt')}
    models = list(source_models.glob('purple_*.mod')) + [source_models / 'pod.mod', source_models / 'treasure.mod']
    if not models or any(not path.is_file() for path in models):
        raise ValueError('Missing imported Purple/Pod presentation')
    motion_models = list(motion.glob('purple_*.mod')) if motion else []
    if motion:
        configs['p2-purple-motion.txt'] = (motion / 'p2-purple-motion.txt').read_bytes()
        if not motion_models:
            raise ValueError('Missing Purple motion models')
    run = prepare(assets, converted, output)
    gen = run / 'assets/dataDir/stages/chal0/default.gen'
    entries = [bytearray(row) for row in records(gen)]
    adults = []
    pikis = 0
    for row in entries:
        if row[72:76] == b'ikip':
            pikis += 1
        if row[16:48].rstrip(b'\0') == b'preview dwarf bulborb':
            if row[72:76] != b'iket' or row[80] != 3:
                raise ValueError('Unexpected native adult template')
            row[80] = 4  # Generator v10 byte enum: TEKI_Swallow.
            adults.append(struct.unpack_from('<I', row, 8)[0])
    if pikis != 20 or len(adults) != 1:
        raise ValueError('Expected 20 starting Pikmin and one adult')
    gen.write_bytes(gen.read_bytes()[:24] + b''.join(entries))
    birth = deterministic_births(gen, adults)
    purple = configs['p2-purple.txt'].decode().replace('\r\n', '\n')
    if 'impact red_earthquake_v1' not in purple.splitlines():
        purple += '\nimpact red_earthquake_v1\n'
    configs['p2-purple.txt'] = purple.encode()
    configs['p2-purple-flight.txt'] = b'P2_PURPLE_FLIGHT_1\n'
    for name, data in configs.items():
        (run / name).write_bytes(data)
    dest = run / 'assets/dataDir/courses/pikmin2room'
    for source in models + motion_models:
        target = dest / source.name
        if target.exists():
            target.unlink()  # Break any inherited hard link before writing.
        shutil.copyfile(source, target)
    write_profile(run / 'p2-purple-direct.txt', adults)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(schema=1, root_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  overlay_sha256=sha(Path('scripts/preview_pikmin2_room.py')),
                  starting_red_records=pikis, adult_runtime_ids=adults,
                  generator_sha256=sha(gen), birth_area_override=birth,
                  window_required='960x540 centered; runtime observation pending',
                  configs={p.name: sha(p) for p in run.glob('p2-*.txt')},
                  presentation_models={p.name: sha(dest / p.name) for p in models + motion_models},
                  intervention='Fresh engineering arena, deterministic actor birth; no flight trajectory staging')
    (run / 'purple-flight-arena.json').write_text(json.dumps(report, indent=2) + '\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'converted', 'presentation', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--motion', type=Path)
    args = parser.parse_args()
    print(stage(args.assets, args.converted, args.presentation, args.output, args.motion))
