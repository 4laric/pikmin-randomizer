"""Stage a private P2 room run for the Fuefuki real-GL runtime fixture (#245).

The lane's ``pikmin2_fuefuki_arena`` builds its roster on the P1 practice
stage, so a run staged with it never loads ``courses/pikmin2room/room.mod``
and ``treasure.mod``. ``pc_p2_preview_ready()`` then never completes and
``p2_fuefuki_runtime.cpp`` times out. This helper stages the converted P2
room with ``preview_pikmin2_room.prepare`` and only then layers the Fuefuki
actor generators into the same run directory, combining generator records
instead of overwriting the room's ``default.gen``.

No cargo config is written: ``pc_p2_preview_ready()`` requires
``previewShape`` (loaded only when the run is *not* cargo-free) and
``previewTreasure`` (the room generator's ``pr05`` pellet). A
``p2-cargo-free.txt`` would suppress the shape load and is refused.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.preview_pikmin2_room import generator, prepare as prepare_room, records
from experimental.pikmin2_generator_pose import validate_position
from experimental.pikmin2_fuefuki_install import install

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols).
P1_CHAPPY_TYPE = 3    # 3, Dwarf Bulborb (ordinary control)
P1_NAPKID_TYPE = 11   # 11, Swooping Snitchbug (placement vehicle only)

# Lane placement contract: ids/species/proxy are the Fuefuki lane's, but the
# coordinates sit on the converted room's validated ground (the original
# arena's z~1550-1850 are Impact Site practice coordinates). Both points are
# in collision-ground-validation.json's spawn list and stay outside the
# fixture's 130-unit scan ring around the (0,0) anchor.
IDS = (245001, 245002)
SPECIES = ('Fuefuki', 'P1 Chappy')
POSITIONS = ((-190., 30., 50.), (260., 30., -170.))
SOURCE_YAW = None
PROXY = {'Fuefuki': P1_NAPKID_TYPE, 'P1 Chappy': P1_CHAPPY_TYPE}
FAMILY = {P1_NAPKID_TYPE: 'Napkid (P1 Swooping Snitchbug)',
          P1_CHAPPY_TYPE: 'Chappy (P1 Dwarf Bulborb)'}

# The room generator's treasure model id, stored little-endian ('pr05').
TREASURE_MODEL = b'50rp'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fuefuki_records(assets, positions=POSITIONS):
    """Build the two Fuefuki enemy records from the room's ``iket`` template."""
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    entries, actors = [], []
    for identity, kind, xyz in zip(IDS, SPECIES, positions):
        teki_type = PROXY[kind]
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = teki_type
        struct.pack_into('>6f', row, 48, *xyz, 0, 0, 0)
        entries.append(bytes(row))
        actors.append(dict(generator=identity, species=kind,
                           native_family=FAMILY[teki_type], native_teki_type=teki_type,
                           proxy=('ordinary P1 control' if kind == 'P1 Chappy' else
                                  'P1 Napkid 11 placement vehicle only; species identity NOT claimed'),
                           expected_xyz=list(validate_position(row, xyz)),
                           offset=[0, 0, 0], source_yaw=SOURCE_YAW,
                           source_yaw_applied=False))
    return entries, actors


def combine(gen_path, extra):
    """Append records to a generator blob, preserving every existing record."""
    header = gen_path.read_bytes()[:20]
    entries = records(gen_path)
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    if used & {struct.unpack_from('<I', r, 8)[0] for r in extra}:
        raise ValueError('Fuefuki generator ID collides with a room record')
    merged = entries + list(extra)
    gen_path.write_bytes(header + struct.pack('>I', len(merged)) + b''.join(merged))
    return merged


def prepare(assets, converted, output):
    run = prepare_room(assets.resolve(), converted.resolve(), output)
    private = run / 'assets/dataDir/courses/pikmin2room'
    gen = run / 'assets/dataDir/stages/chal0/default.gen'
    for name in ('p2-cargo-free.txt', 'p2-cargo.txt'):
        if (run / name).exists():
            raise ValueError(f'refusing staged cargo config that blocks preview_ready: {name}')
    extra, actors = fuefuki_records(assets.resolve())
    merged = combine(gen, extra)
    profile = install(run)
    manifest = dict(
        schema=1, scene='P2 room 4x4a prototype', stage_slot='chal0',
        fixture='p2_fuefuki_runtime',
        run=str(run),
        actors=actors,
        generator_ids=[a['generator'] for a in actors],
        generator_record_count=len(merged),
        generator_sha256=digest(gen),
        room_sha256=digest(private / 'room.mod'),
        room_ini_sha256=digest(private / 'room.ini'),
        treasure_sha256=digest(private / 'treasure.mod'),
        profile=profile,
        preview_ready_requires='previewShape (courses/pikmin2room/treasure.mod) + previewTreasure (pr05)',
        cargo_config='none: p2-cargo-free.txt would suppress previewShape and fail pc_p2_preview_ready',
        command=['fixture.exe', '--experimental-pikmin2-room'])
    (run / 'fuefuki-arena.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    return run


def verify(run):
    """Inspect the staged run for the exact inputs the fixture consumes."""
    run = Path(run)
    private = run / 'assets/dataDir/courses/pikmin2room'
    gen = run / 'assets/dataDir/stages/chal0/default.gen'
    stage_ini = (run / 'assets/dataDir/stages/chal0.ini').read_text()
    entries = records(gen)
    by_id = {struct.unpack_from('<I', r, 8)[0]: r for r in entries}
    treasure = [r for r in entries if r[72:76] == b'tlep' and r[80:84] == TREASURE_MODEL]
    report = dict(
        run=str(run),
        room_mod=(private / 'room.mod').is_file(),
        room_ini=(private / 'room.ini').is_file(),
        treasure_mod=(private / 'treasure.mod').is_file(),
        stage_maps_room='map_file courses/pikmin2room/room.mod' in stage_ini.splitlines(),
        treasure_records=len(treasure),
        squad_records=len([r for r in entries if r[72:76] == b'ikip']),
        fuefuki_ids=sorted(i for i in IDS if i in by_id),
        fuefuki_tags=sorted(by_id[i][72:76].decode('ascii') for i in IDS if i in by_id),
        profile=(run / 'p2-fuefuki-profile.txt').is_file(),
        install_receipt=(run / 'fuefuki-install.json').is_file(),
        cargo_config_absent=not any((run / n).exists() for n in ('p2-cargo-free.txt', 'p2-cargo.txt')),
        record_count=len(entries),
    )
    report['ok'] = (all((report['room_mod'], report['room_ini'], report['treasure_mod'],
                         report['stage_maps_room'], report['treasure_records'] == 1,
                         report['squad_records'] == 20, report['fuefuki_ids'] == list(IDS),
                         all(t == 'iket' for t in report['fuefuki_tags']),
                         report['profile'], report['install_receipt'], report['cargo_config_absent'])))
    report['sha256'] = {name: digest(p) for name, p in (
        ('assets/dataDir/stages/chal0/default.gen', gen),
        ('assets/dataDir/courses/pikmin2room/room.mod', private / 'room.mod'),
        ('assets/dataDir/courses/pikmin2room/room.ini', private / 'room.ini'),
        ('assets/dataDir/courses/pikmin2room/treasure.mod', private / 'treasure.mod'),
        ('p2-fuefuki-profile.txt', run / 'p2-fuefuki-profile.txt'),
        ('fuefuki-install.json', run / 'fuefuki-install.json'),
        ('fuefuki-arena.json', run / 'fuefuki-arena.json'))}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--converted', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run = prepare(args.assets, args.converted, args.output)
    report = verify(run)
    report['passed'] = report.pop('ok')
    print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit('staged run failed verification')


if __name__ == '__main__':
    main()
