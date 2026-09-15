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
from experimental.pikmin2_seed_evidence import cohort_markers, find_mingw, ready_species  # noqa: E402
from scripts.preview_pikmin2_room import (  # noqa: E402
    generator, overlay, prototype_routes, records, replace_embedded_routes)

SNOW_ID = 5001
DWARF_ID = 211001
POD_CONFIG = 'p2-pod.txt'
PLACEMENT_SIDECAR = 'p2-placement-slots.txt'
PLACEMENT_HEADER = 'P2_PLACEMENT_SLOTS_1'
# source_id -> (generator id, display name, actor position)
IDENTITY_ROWS = {
    44: (DWARF_ID, 'Dwarf Orange Bulborb', (-150.0, 30.0, 1850.0)),
    45: (SNOW_ID, 'Snow Bulborb', (-150.0, 30.0, 1700.0)),
}
GENERATOR_FOR_SOURCE = {44: DWARF_ID, 45: SNOW_ID}


def _writer(record, position):
    from experimental.pikmin2_generator_pose import write_position
    write_position(record, position)


def build_retail(assets, converted, pod_root, out, identities=(44, 45)):
    """Build a retail asset tree the runner overlays: converted room + a curated
    actor roster carrying exactly one clean Chappy row per ``identities`` source,
    plus the Pod model and a single treasure."""
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
    enemy = next(r for r in entries if r[72:76] == b'iket' and r[80] == 3)
    kept = [e for e in entries if not (e[72:76] == b'iket' and e[80] == 3)]
    for source_id in sorted(identities):
        gid, name, position = IDENTITY_ROWS[source_id]
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, gid)
        row[16:48] = name.encode('ascii')[:32].ljust(32, b'\0')
        _writer(row, position)
        kept.append(bytes(row))
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


def build_content(bank, profile_ref, snow_run, out, identities=(44, 45)):
    """Assemble the identity-keyed content_root (bank/profile and/or Snow flat bank)."""
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if 44 in identities:
        bank = Path(bank).resolve()
        profile_ref = Path(profile_ref).resolve()
        src = out / 'BlueKochappy'
        b, p = src / 'bank', src / 'profile'
        b.mkdir(parents=True, exist_ok=True)
        p.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bank / 'dwarf-orange-bank.json', b / 'dwarf-orange-bank.json')
        shutil.copyfile(bank / 'p2-dwarf-orange-bank.txt', b / 'p2-dwarf-orange-bank.txt')
        shutil.copyfile(bank / 'p2-dwarf-orange-profile.txt', b / 'p2-dwarf-orange-profile.txt')
        for m in sorted(bank.glob('dwarf_orange_*.mod')):
            shutil.copyfile(m, b / m.name)
        shutil.copyfile(profile_ref / 'dwarf-orange-profile.json', p / 'dwarf-orange-profile.json')

    if 45 in identities:
        snow_run = Path(snow_run).resolve()
        s = out / 'YellowKochappy'
        s.mkdir(parents=True, exist_ok=True)
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


def write_placement_sidecar(directory, generator_slots):
    """Write the lane-04 ``p2-placement-slots.txt`` sidecar (generator -> slot uid)."""
    path = Path(directory) / PLACEMENT_SIDECAR
    lines = [PLACEMENT_HEADER]
    lines += [f'{int(g)} {int(s)}' for g, s in generator_slots]
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    return path


def stage(assets, converted, bank, profile, snow, pod, out, identities=(44, 45)):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    retail = out / 'retail'
    build_retail(assets, converted, pod, retail, identities)
    content = build_content(bank, profile, snow, out / 'content', identities)
    run = out / 'run'
    layout = {'bindings': [
        {'target': kind, 'source_id': source_id, 'enum_name': enum}
        for kind, source_id, enum in
        (('orange', 44, 'BlueKochappy'), ('snow', 45, 'YellowKochappy'))
        if source_id in identities
    ]}
    family_install.install_layout(
        run, layout, content,
        actor_bindings={b['target']: GENERATOR_FOR_SOURCE[b['source_id']] for b in layout['bindings']},
        retail_assets=retail)
    if 45 in identities:
        (run / POD_CONFIG).write_text((Path(pod).resolve() / POD_CONFIG).read_text())
    (run / 'preview.json').write_text(json.dumps(
        dict(room='room_4x4a_4_conc', experimental=True, ap=False, save_resume=False), indent=2))
    (out / 'stage.json').write_text(json.dumps(dict(
        run=str(run), identities=list(identities),
        command=['nectar.exe', '--experimental-pikmin2-room']), indent=2))
    return run


def run(stage_dir, exe, out, seconds=45):
    stage_dir = Path(stage_dir).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    mingw = find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    kw = dict(cwd=stage_dir, env=env)
    if os.name == 'nt':
        kw['startupinfo'] = startup
    log_path = out / 'native.log'
    timed_out = False
    with log_path.open('w', encoding='utf-8') as lg:
        proc = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                stdout=lg, stderr=subprocess.STDOUT, **kw)
        try:
            proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    text = log_path.read_text(encoding='utf-8', errors='replace')
    marks = cohort_markers(text)
    passed = (timed_out or proc.returncode == 0) and all(marks.values())
    result = dict(passed=passed, timed_out=timed_out, exit_code=proc.returncode,
                  checks=marks, ready_species=ready_species(text))
    (out / 'evidence.json').write_text(json.dumps(result, indent=2))
    for keep in (stage_dir / 'p2-binding-receipt.json', stage_dir.parent / 'stage.json'):
        if keep.is_file() and not (out / keep.name).exists():
            shutil.copyfile(keep, out / keep.name)
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
