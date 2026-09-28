"""Stage a verified Queen specular bank into a fresh, private room-preview run."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_bulblax_bank import parse_bank, validate_files
from experimental.pikmin2_queen_actor import QUEEN_CLIPS_REQUIRED, protocol
from experimental.pikmin2_queen_specular import BTK, POLICY
from scripts.preview_pikmin2_room import overlay


def stage(bank, assets, output, xyz):
    bank, assets, output = (Path(p).resolve() for p in (bank, assets, output))
    if output.exists():
        raise ValueError('Output must be fresh')
    report = json.loads((bank / 'bulblax-bank.json').read_text(encoding='utf-8'))
    specular = report.get('queen_specular', {})
    if specular.get('policy') != POLICY or specular.get('source_btk') != BTK:
        raise ValueError('Expected prepared Queen specular bank')
    animation = (bank / 'p2-queen-specular.txt').read_bytes()
    if hashlib.sha256(animation).hexdigest() != specular.get('animation_sha256'):
        raise ValueError('Animation hash mismatch')
    parsed = parse_bank((bank / 'p2-bulblax-bank.txt').read_text(encoding='ascii'))
    files, _ = validate_files(bank, parsed)
    overrides = {}
    for path in files:
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != report['file_sha256'].get(path.name):
            raise ValueError('Model hash mismatch: ' + path.name)
        if path.parent.name == 'Queen':
            overrides['dataDir/courses/pikmin2room/' + path.name] = data
    clips = [dict(species='Queen', name=name, duration=parsed['Queen'][name]['source_frames'],
                  frames=parsed['Queen'][name]['frames']) for name in QUEEN_CLIPS_REQUIRED]
    actor = protocol(clips, [dict(placement_id=399, xyz=xyz, variant='f_01', larvae=False)])
    if not (assets / 'dataDir/courses/pikmin2room').is_dir():
        raise ValueError('Expected existing private room-preview assets')
    # All checks precede output creation; overlay writes only owned replacements.
    output.mkdir(parents=True)
    overlay(assets, output / 'assets', overrides)
    (output / 'p2-queen-specular.txt').write_bytes(animation)
    (output / 'p2-queen-actor.txt').write_bytes(actor)
    (output / 'queen-specular-stage.json').write_text(json.dumps(dict(
        policy=POLICY, bank=str(bank), files={key: hashlib.sha256(value).hexdigest()
                                           for key, value in overrides.items()},
        animation_sha256=specular['animation_sha256']), indent=2) + '\n', encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--xyz', type=float, nargs=3, required=True)
    args = parser.parse_args()
    print(stage(args.bank, args.assets, args.output, args.xyz))
