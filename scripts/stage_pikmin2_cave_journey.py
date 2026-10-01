"""Stage an opt-in generated two-floor journey into a fresh private package."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.cave_journey import create, identity, POLICY
from scripts.stage_pikmin2_playable_cave import stage


def stage_package(seed, slot, assets, pod, exe, generator, output, workspace):
    if output.exists():
        raise ValueError('use a fresh private journey package')
    output = output.resolve()
    workspace = workspace.resolve()
    if not output.is_relative_to(workspace/'output'):
        raise ValueError('journey package must be under private output/')
    journey = create(seed, slot)
    output.mkdir(parents=True)
    files, blueprints = {}, {}
    for n, spec in enumerate(journey['floors'], 1):
        directory = output/f'floor-{n}'
        meta = stage(spec['descriptor'], assets, pod, exe, generator, directory, spec['salt'])
        for name, digest in meta['files'].items():
            files[f'floor-{n}/{name}'] = digest
        files[f'floor-{n}/package.json'] = hashlib.sha256((directory/'package.json').read_bytes()).hexdigest()
        names = ('cave.json','layout.json','render.mod','collision.json',
                 'assets/dataDir/courses/pikmin2room/room.mod',
                 'assets/dataDir/stages/chal0/default.gen')
        for name in names:
            files[f'floor-{n}/{name}'] = hashlib.sha256((directory/name).read_bytes()).hexdigest()
        blueprints[str(n)] = {name: files[f'floor-{n}/{name}'] for name in names if 'default.gen' not in name}
    for source, name in ((exe,'nectar.exe'), (generator,'cave-generator.exe')):
        shutil.copy2(source, output/name)
    for dll in exe.parent.glob('*.dll'):
        shutil.copy2(dll, output/dll.name)
    (output/'journey.json').write_text(json.dumps(journey, indent=2)+'\n')
    launcher = Path(__file__).with_name('play_pikmin2_cave.py')
    (output/'Play.cmd').write_text('@echo off\r\npy -3.12 "'+str(launcher)+'" "'+str(output)+'"\r\npause\r\n')
    for path in output.iterdir():
        if path.is_file():
            files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = dict(schema=3, policy=POLICY, fingerprint=identity(journey),
                assets=str(assets.resolve()), pod=str(pod.resolve()), workspace=str(workspace),
                files=files, blueprints=blueprints, limitations=['Original engineered geometry, not retail rooms.',
                    'One floor1-to-floor2 transition only; no terminal return/campaign/AP persistence.'])
    (output/'package.json').write_text(json.dumps(meta, indent=2)+'\n')
    return meta


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('assets','pod','exe','generator','output','workspace'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--seed', default='1127'); p.add_argument('--slot', default='Player1')
    a = p.parse_args()
    print(json.dumps(stage_package(a.seed,a.slot,a.assets,a.pod,a.exe,a.generator,a.output,a.workspace),indent=2))


if __name__ == '__main__':
    main()
