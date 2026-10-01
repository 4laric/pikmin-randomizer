"""Stage all tutorial faces plus exact static source water; no retail generators."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from experimental.pikmin2_surface_water_runtime import serialize
from scripts.stage_pikmin2_full_surface import prepare as prepare_terrain


def prepare(assets, bundle, identity, output, species_probe=False):
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
    for name in ('default.gen', 'init.gen', 'plants.gen', 'day.gen'):
        path = run / 'assets/dataDir/stages/p2_tutorial' / name
        data = bytearray(path.read_bytes())
        if data[:4] != b'1.0v':
            raise ValueError('Unsupported private generator header')
        # GeneratorMgr::read sets the captain from this header, overriding stage
        # navi_start. Keep actor positions untouched except the disclosed probe.
        struct.pack_into('>3f', data, 4, 220, 56.0442, 1000)
        if name == 'default.gen' and species_probe:
            starts = [m.start() for m in re.finditer(b'    0.0v', data)]
            if len(starts) != 20:
                raise ValueError('Expected current twenty-Pikmin template')
            for i, offset in enumerate(starts):
                if (data[offset+72:offset+76] != b'ikip' or data[offset+80:offset+84] != b'p00\x04'
                        or data[offset+88:offset+92] != b'p01\x04'):
                    raise ValueError('Unsupported generator record')
                # 18 Reds stay free at the dry entrance; a Red and a Blue start
                # on the dry shoreline in formation. Native color0 is Blue.
                struct.pack_into('>i', data, offset+84, 2 if i<2 else 1)
                if i<2:
                    struct.pack_into('>3f', data, offset+48, 220, 56.0442, 995+i*10)
                struct.pack_into('>i', data, offset+92, 0 if i==1 else 1)
        path.write_bytes(data)
    inputs = run / 'full-surface-inputs.json'
    terrain_record = json.loads(inputs.read_text())
    terrain_record['files'] = {name: hashlib.sha256((run/'assets'/name).read_bytes()).hexdigest()
                               for name in terrain_record['files']}
    terrain_record.update(native_water_consumer=True, captain_start_xz=[220,1000],
                          species_probe=species_probe, water_record='surface-water-inputs.json')
    inputs.write_text(json.dumps(terrain_record, indent=2)+'\n')
    record = dict(schema=1, receipt_identity=identity, static_source_boxes=3,
                  native_water_consumer=True, dynamic_lowering=False,
                  native_body_convention='P1 feet position and collision radius',
                  captain_start_xz=[220, 1000], starting_squad='19 Reds/1 Blue disclosed probe' if species_probe else '20 Reds retained on dry entrance bank',
                  species_probe=species_probe,
                  species_probe_staging='19 Reds/1 Blue; 18 free dry-bank Reds, two shoreline followers' if species_probe else None,
                  water_sha256=hashlib.sha256(water).hexdigest(),
                  source_waterbox_sha256=hashlib.sha256((bundle/'texts/waterbox.txt').read_bytes()).hexdigest(),
                  source_volume_inventory_sha256=hashlib.sha256((bundle/'surface-water.json').read_bytes()).hexdigest(),
                  stage_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),
                  generators_sha256={name: hashlib.sha256((run/'assets/dataDir/stages/p2_tutorial'/name).read_bytes()).hexdigest()
                                     for name in ('default.gen','init.gen','plants.gen','day.gen')},
                  terrain_sha256=hashlib.sha256(target.with_suffix('.mod').read_bytes()).hexdigest(),
                  retail_generators=False, water_rendering=False, playable_level_admission=False)
    (run / 'surface-water-inputs.json').write_text(json.dumps(record, indent=2)+'\n')
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bundle', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--identity', required=True)
    parser.add_argument('--species-probe', action='store_true')
    args = parser.parse_args()
    print(prepare(args.assets.resolve(), args.bundle.resolve(), args.identity, args.output.resolve(), args.species_probe))
