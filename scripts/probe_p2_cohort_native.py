"""Lane 05 slice-3b native cohort proof: Snow Bulborb + Dwarf Orange Bulborb + Pod.

Stages the two-identity cohort through the lane-05 runner binding
(``install_layout``) using the *preview-generator* room (``scripts/preview_pikmin2_room``
overlay with the converted room + curated actor roster) and the REAL banks, then
launches ``nectar.exe --experimental-pikmin2-room`` and asserts the native
bank/sidecar load markers.

The Pod is not a family-installer sidecar: its ``p2-pod.txt`` config is copied to
the run root and its ``pod.mod`` is placed in the private model room (its native
consumer is ``pc_p2_preview``, not a lane-05 adapter). All asset paths are caller
supplied; nothing here is lane-specific.

    py -3.12 scripts/probe_p2_cohort_native.py stage --assets <P1> --converted <c> \
        --bank <bank> --profile <ref> --snow <cohort-run> --pod <cohort-run> --out <dir>
    py -3.12 scripts/probe_p2_cohort_native.py run --stage <dir> --exe <nectar.exe> --out <dir>
"""
import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental import pikmin2_family_install as family_install  # noqa: E402
from experimental.pikmin2_animation import parse_bank as parse_snow_bank  # noqa: E402
from scripts.preview_pikmin2_room import (  # noqa: E402
    generator, overlay, prototype_routes, records, replace_embedded_routes)

SNOW_ID = 5001
DWARF_ID = 211001
POD_CONFIG = 'p2-pod.txt'


def build_retail(assets, converted, pod_root, out):
    """Build a retail asset tree the runner will overlay: converted room + a
    curated actor roster with one Dwarf Orange Chappy (211001) and one Snow
    Chappy (5001) added to the preview generator, plus the Pod model."""
    assets = Path(assets).resolve()
    converted = Path(converted).resolve()
    stage = re.sub(rb'(?m)^map_file[^\r\n]*', b'map_file courses/pikmin2room/room.mod',
                   (assets / 'dataDir/stages/chal0.ini').read_bytes())
    stage = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start -85.0 0.0', stage)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    routes = prototype_routes((converted / 'room.ini').read_bytes())
    room_model = replace_embedded_routes((converted / 'room.mod').read_bytes(), routes)

    blob = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', blob)]
    entries = [blob[a:(starts[i + 1] if i + 1 < len(starts) else len(blob))]
               for i, a in enumerate(starts)]
    # Re-key the audited enemy template into clean Dwarf Orange + Snow rows.
    enemy = next(r for r in entries if r[72:76] == b'iket' and r[80] == 3)
    dwarf = bytearray(enemy)
    struct.pack_into('<I', dwarf, 8, DWARF_ID)
    dwarf[16:48] = b'Dwarf Orange Bulborb'.ljust(32, b'\0')
    writer(dwarf, (-150.0, 30.0, 1850.0))
    snow = bytearray(enemy)
    struct.pack_into('<I', snow, 8, SNOW_ID)
    snow[16:48] = b'Snow Bulborb'.ljust(32, b'\0')
    writer(snow, (-150.0, 30.0, 1700.0))
    # Drop the generator's own extra enemy rows (single dwarf from challenge[9]),
    # keeping the reds / onion / ship / treasure and our two clean Chappy rows.
    kept = [e for e in entries if not (e[72:76] == b'iket' and e[80] == 3)]
    kept += [bytes(dwarf), bytes(snow)]
    blob = blob[:20] + struct.pack('>I', len(kept)) + b''.join(kept)

    pod_mod = Path(pod_root).resolve() / 'assets/dataDir/courses/pikmin2room/pod.mod'
    overrides = {
        'dataDir/stages/chal0.ini': stage,
        'dataDir/stages/chal0/default.gen': blob,
        'dataDir/stages/chal0/plants.gen': empty,
        'dataDir/courses/pikmin2room/room.mod': room_model,
        'dataDir/courses/pikmin2room/room.ini': routes,
        'dataDir/courses/pikmin2room/treasure.mod': (converted / 'treasure.mod').read_bytes(),
        'dataDir/courses/pikmin2room/pod.mod': pod_mod.read_bytes(),
    }
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    out = Path(out).resolve()
    overlay(assets, out, overrides)
    return out


def writer(record, position):
    from experimental.pikmin2_generator_pose import write_position
    write_position(record, position)


def build_content(retail_root, bank, profile_ref, snow_run, out):
    """Assemble the identity-keyed content_root (bank/profile + Snow flat bank)."""
    bank = Path(bank).resolve()
    profile_ref = Path(profile_ref).resolve()
    snow_run = Path(snow_run).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True)

    src = out / 'BlueKochappy'
    b, p = src / 'bank', src / 'profile'
    b.mkdir(parents=True)
    p.mkdir()
    shutil.copyfile(bank / 'dwarf-orange-bank.json', b / 'dwarf-orange-bank.json')
    shutil.copyfile(bank / 'p2-dwarf-orange-bank.txt', b / 'p2-dwarf-orange-bank.txt')
    shutil.copyfile(bank / 'p2-dwarf-orange-profile.txt', b / 'p2-dwarf-orange-profile.txt')
    for m in sorted(bank.glob('dwarf_orange_*.mod')):
        shutil.copyfile(m, b / m.name)
    shutil.copyfile(profile_ref / 'dwarf-orange-profile.json', p / 'dwarf-orange-profile.json')

    s = out / 'YellowKochappy'
    s.mkdir()
    snow_txt = (snow_run / 'p2-snow.txt').read_text(encoding='ascii')
    bank_map = parse_snow_bank(snow_txt)
    motions = {n: {'poses': i['poses'], 'source_frames': i['source_frames'], 'frames': i['frames']}
               for n, i in bank_map.items()}
    (s / 'p2-snow.txt').write_text(snow_txt, encoding='ascii')
    (s / 'snow.json').write_text(json.dumps(
        {'schema': 1, 'species': 'YellowKochappy', 'motions': motions}), encoding='utf-8')
    room = snow_run / 'assets/dataDir/courses/pikmin2room'
    for m in sorted(room.glob('snow_*.mod')):
        shutil.copyfile(m, s / m.name)
    return out


def stage(assets, converted, bank, profile, snow, pod, out):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    retail = out / 'retail'
    build_retail(assets, converted, pod, retail)
    content = build_content(retail, bank, profile, snow, out / 'content')
    run = out / 'run'
    layout = {'bindings': [
        {'target': 'orange', 'source_id': 44, 'enum_name': 'BlueKochappy'},
        {'target': 'snow', 'source_id': 45, 'enum_name': 'YellowKochappy'},
    ]}
    family_install.install_layout(
        run, layout, content,
        actor_bindings={'orange': DWARF_ID, 'snow': SNOW_ID},
        retail_assets=retail)
    (run / POD_CONFIG).write_text((Path(pod).resolve() / POD_CONFIG).read_text())
    (run / 'preview.json').write_text(json.dumps(
        dict(room='room_4x4a_4_conc', experimental=True, ap=False, save_resume=False), indent=2))
    (out / 'stage.json').write_text(json.dumps(dict(
        run=str(run), identities=[DWARF_ID, SNOW_ID],
        command=['nectar.exe', '--experimental-pikmin2-room']), indent=2))
    return run


def run(stage_dir, exe, out, seconds=45):
    stage_dir = Path(stage_dir).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    mingw = Path(r'C:/msys64/mingw64/bin')
    if mingw.is_dir():
        env['PATH'] = str(mingw) + os.pathsep + env.get('PATH', '')
    log_path = out / 'native.log'
    with log_path.open('w', encoding='utf-8') as lg:
        proc = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                cwd=stage_dir, env=env, stdout=lg, stderr=subprocess.STDOUT)
        try:
            proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    text = log_path.read_text(encoding='utf-8', errors='replace')
    checks = {
        'window_960x540': '960x540' in text,
        'snow_bank': 'P2_SNOW_BANK poses=' in text,
        'snow_ready': 'P2_ENEMY_READY species=YellowKochappy' in text,
        'dwarf_bank': 'P2_DWARF_ORANGE_BANK poses=' in text,
        'dwarf_ready': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in text,
        'no_retail_fallback': 'duplicate treasure' not in text and 'abort' not in text,
    }
    result = dict(exit_code=proc.returncode, passed=all(checks.values()), checks=checks)
    (out / 'evidence.json').write_text(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('stage')
    for name in ('assets', 'converted', 'bank', 'profile', 'snow', 'pod', 'out'):
        s.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'out'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=45)
    a = parser.parse_args()
    if a.command == 'stage':
        print(stage(a.assets, a.converted, a.bank, a.profile, a.snow, a.pod, a.out))
    else:
        print(json.dumps(run(a.stage, a.exe, a.out, a.seconds), indent=2))


if __name__ == '__main__':
    main()
