"""Prepare a fresh local-only Pikipelago Snow Dwarf campaign playtest (#342)."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from experimental.pikmin2_animation import parse_bank, validate_files
from randomizer.seed import generate, validate
from scripts.preview_pikmin2_room import overlay
from scripts.bundle_pikmin2_fixture import bundle, pe_imports


def prepare(assets, snow, exe, dll_root, objdump, output, seed):
    if output.exists():
        raise ValueError('Fresh output required; existing seeds are never replaced')
    metadata = json.loads((snow / 'snow.json').read_text())
    if metadata.get('species') != 'YellowKochappy':
        raise ValueError('Expected locally imported Snow Bulborb bank')
    bank = parse_bank((snow / 'p2-snow.txt').read_text())
    if any(info['frames'] is None for info in bank.values()):
        raise ValueError('Interpolation requires explicit source frames')
    files, _ = validate_files(snow, bank)
    manifest = generate(seed, slot='4laric', expanded=True, all_areas=True,
                        collection_checks=True, permanent_checks=True,
                        progressive_color_stats=True, starting_flarlic=1,
                        bomb_rock_weight=1, combined_captain=True,
                        goal_mode='emperor_bulblax')
    validate(manifest)
    output.mkdir(parents=True)
    overrides = {'dataDir/courses/pikmin2room/' + p.name: p.read_bytes() for p in files}
    overrides.update({'p2-snow.txt': (snow / 'p2-snow.txt').read_bytes(),
                      'p2-snow-all-dwarfs.txt': b'P2_SNOW_ALL_DWARFS_1\n',
                      'p2-snow-interpolation.txt': b'P2_SNOW_INTERPOLATION_1\n'})
    overlay(assets, output / 'assets', overrides)
    runtime = bundle(exe, [dll_root], Path('C:/Windows/System32'), output / 'bin',
                     lambda p: pe_imports(p, objdump))
    shutil.copytree(Path(__file__).resolve().parents[1] / 'randomizer', output / 'randomizer',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (output / 'seed.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'Play.cmd').write_text('@echo off\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Play.ps1"\n')
    (output / 'Play.ps1').write_text('''$ErrorActionPreference = 'Stop'
Remove-Item Env:PIKMIN_RANDOMIZER_TEST_BACKGROUND -ErrorAction SilentlyContinue
Remove-Item Env:PIKMIN_RANDOMIZER_TEST_SCRIPT -ErrorAction SilentlyContinue
Set-Location -LiteralPath $PSScriptRoot
Write-Host 'Pikipelago: Snow Day - all Dwarf Bulborbs use interpolated Snow visuals'
Write-Host 'Forest of Hope / red / 10 field capacity / normal initial stats + upgrades'
Write-Host 'Dwarf Bulborb checks and corpse rewards retain their native identities.'
Write-Host 'Keep this window open while playing.'
py -3.12 -m randomizer run "$PSScriptRoot/seed.json" --session-dir "$PSScriptRoot/session" --exe "$PSScriptRoot/bin/nectar.exe" --assets "$PSScriptRoot/assets"
if ($LASTEXITCODE -ne 0) { Read-Host 'Launch failed. Press Enter to close' }
''')
    (output / 'README.txt').write_text('''Pikipelago: Snow Day
Run Play.cmd. This local package depends on the extracted P1 assets on this computer.
Every native Dwarf Bulborb (Chappy) receives interpolated Snow Bulborb visuals,
including later births and other areas. Other species remain unchanged.
P1 AI, collision, corpse value and Dwarf Bulborb bestiary check identity remain.
Forest of Hope, red start, 10 field capacity, normal initial stats, 36 stat upgrades,
30 repair items / 25 required, Emperor finale. Enemy placement randomization is off.
This is an experimental P2-rendering playtest. Mid-day autosave is not provided.
Existing seeds and sessions are not modified. Imported assets are local only.
''')
    report = dict(seed=seed, executable=runtime['files'],
                  asset_overrides={k: hashlib.sha256(v).hexdigest() for k, v in overrides.items()},
                  scope='all native Chappy visuals; P1 gameplay and check identities')
    (output / 'playtest.json').write_text(json.dumps(report, indent=2) + '\n')
    return output / 'Play.cmd'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'snow', 'exe', 'dll-root', 'objdump', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--seed', default='pikipelago-snow-day-01')
    a = p.parse_args()
    print(prepare(a.assets.resolve(), a.snow.resolve(), a.exe.resolve(), a.dll_root.resolve(),
                  a.objdump.resolve(), a.output.resolve(), a.seed))
