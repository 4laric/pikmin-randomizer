"""Stage all tutorial faces plus exact static source water; no retail generators."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from experimental.pikmin2_surface_water_runtime import serialize
from scripts.stage_pikmin2_full_surface import prepare as prepare_terrain


def prepare(assets, bundle, identity, output):
    # Validate water before creating a runnable overlay; terrain preparation verifies
    # the complete source receipt. No centroid mapcode tagging or face changes.
    water = serialize((bundle / 'texts/waterbox.txt').read_text())
    run = prepare_terrain(assets, bundle, identity, output)
    target = run / 'assets/dataDir/courses/p2tutorial/full.water'
    # full.mod's override makes this directory private rather than an asset junction.
    if not target.parent.resolve().is_relative_to(run.resolve()):
        raise ValueError('Refusing water write through shared asset junction')
    target.write_bytes(water)
    stage = run / 'assets/dataDir/stages/p2_tutorial.ini'
    if not stage.resolve().is_relative_to(run.resolve()):
        raise ValueError('Refusing stage write through shared asset junction')
    stage.write_bytes(re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start 220.0 1000.0', stage.read_bytes()))
    record = dict(schema=1, receipt_identity=identity, static_source_boxes=3,
                  native_water_consumer=True, dynamic_lowering=False,
                  native_body_convention='P1 feet position and collision radius',
                  captain_start_xz=[220, 1000], starting_squad='20 Reds retained on dry entrance bank',
                  water_sha256=hashlib.sha256(water).hexdigest(),
                  terrain_sha256=hashlib.sha256(target.with_suffix('.mod').read_bytes()).hexdigest(),
                  retail_generators=False, water_rendering=False, playable_level_admission=False)
    (run / 'surface-water-inputs.json').write_text(json.dumps(record, indent=2)+'\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    print(prepare(args.assets.resolve(), args.bundle.resolve(), args.identity, args.output.resolve()))
