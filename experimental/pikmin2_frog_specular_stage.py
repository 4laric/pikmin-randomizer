"""Stage the profiled Frog bank into a fresh private room-preview run.

Produces the actor/content layout the Frog specular-acceptance fixture loads
(`courses/pikmin2room/frog_Frog_wait1_00.mod`). Mirrors the Queen
`pikmin2_queen_specular_stage` shape: only owned replacements are written; the
shared room-preview asset tree is read-only.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts.preview_pikmin2_room import overlay

POLICY = 'P2_FROG_SOURCE_MATERIAL_1'


def profiled_bank(bank):
    report = json.loads((bank / 'frogs.json').read_text(encoding='utf-8'))
    profile = report.get('material_profile', {})
    if profile.get('policy') != POLICY:
        raise ValueError('Expected a prepared Frog material-profile bank')
    return report


def stage(bank, assets, output):
    bank, assets, output = (Path(p).resolve() for p in (bank, assets, output))
    if output.exists():
        raise ValueError('Output must be fresh')
    report = profiled_bank(bank)
    if not (assets / 'dataDir/courses/pikmin2room').is_dir():
        raise ValueError('Expected existing private room-preview assets')
    overrides = {}
    for species in ('Frog', 'MaroFrog'):
        pose = bank / species / ('frog_%s_wait1_00.mod' % species)
        if not pose.is_file():
            raise ValueError('Missing profiled pose: ' + pose.name)
        overrides['dataDir/courses/pikmin2room/' + pose.name] = pose.read_bytes()
    # All checks precede output creation; overlay writes only owned replacements.
    output.mkdir(parents=True)
    overlay(assets, output / 'assets', overrides)
    (output / 'frog-specular-stage.json').write_text(json.dumps(dict(
        policy=POLICY, bank=str(bank),
        files={key: hashlib.sha256(value).hexdigest() for key, value in overrides.items()},
        rendered_material='Frog diffuse+specular profile (control 0x93)',
        fixture='scripts/pikmin2_frog_specular_fixture.cpp'), indent=2) + '\n', encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'assets', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(stage(args.bank, args.assets, args.output))
