"""Mixed-scene correctness + frame-time/memory harness for the P2 species lane.

The fan-out (``docs/PIKMIN2_IMPLEMENTATION_FANOUT.md``, "Sequence and
acceptance") requires mixed-scene correctness, frame-time and memory
measurements before any density scaling. Each family lane currently stages a
private single-family arena. This module merges the *implemented* families'
stage generation, actor registrations and pose banks into ONE private run
directory that both native registries read:

* ``pc_p2_batch2_setup`` reads ``p2-ground-actors.txt`` / ``p2-ground-bank.txt``
* ``pc_p2_batch3_setup`` reads ``p2-flying-*`` and ``p2-aquatic-*``
* ``pc_p2_<species>_setup`` drives the per-species source FSMs

Combined scene (13 actors: 12 species + one ordinary P1 control)::

    ground  (#346 / #165): Armor, ElecBug, Imomushi, TamagoMushi, Sokkuri, Hana
    flying  (#375 / #166): Mar, Hanachirashi
    aquatic (#374 / #167): Catfish, Tadpole, Jigumo, UmiMushi

Snagret (#376 / #174) is excluded because ``output/p2-lane-verify/snagret``
ships no ``snagret.json`` manifest and zero ``.mod`` poses, so the native bank
loader would abort on a missing pose bank. The batch-2 visual-only families
(dweevil, flora, cannon, waterwraith), whose source FSMs are not implemented,
are excluded as well.

``prepare`` writes ``mixed-scene.json`` (the staged contract);
``run`` writes ``mixed-scene-validation.json`` (the measured log). Budget
figures in :data:`PROPOSED_BUDGETS` are PROPOSED for integration review, not
accepted. This is a measurement fixture: engineered coordinates, zeroed
generator scatter, one disposable room, no saves and no player state.
"""
import argparse
import hashlib
import json
import os
import re
import struct
import uuid
from pathlib import Path

from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_animation_profile import capture_command, parse_log
from experimental.pikmin2_batch2_core import (
    install as batch2_install, verify_install as batch2_verify)
from experimental.pikmin2_batch2_families import FAMILIES as BATCH2_FAMILIES
from experimental.pikmin2_generator_pose import validate_position, write_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births
from experimental.pikmin2_aquatic_arena import (
    AQUATIC as AQUATIC_SPECIES, IDS as AQUATIC_IDS,
    POSITIONS as AQUATIC_POSITIONS, PROXY as AQUATIC_PROXY)
from experimental.pikmin2_aquatic_install import (
    install as aquatic_install, verify_install as aquatic_verify)
from experimental.pikmin2_flying_arena import (
    IDS as FLYING_IDS, POSITIONS as FLYING_POSITIONS,
    P1_CHAPPY_TYPE, P1_PUFFY_TYPE)
from experimental.pikmin2_flying_install import (
    SPAWNABLE as FLYING_SPECIES, install as flying_install,
    verify_install as flying_verify)
from experimental.pikmin2_ground_inverts_arena import (
    IDS as GROUND_IDS, POSITIONS as GROUND_POSITIONS,
    PROXY as GROUND_PROXY, SPECIES as GROUND_SPECIES)

WINDOW = '960x540'
CONTROL = 'P1 Chappy'


def _ground_actors():
    return [dict(generator=generator, species=species,
                 native_teki_type=GROUND_PROXY[species], xyz=tuple(xyz))
            for generator, species, xyz in zip(GROUND_IDS, GROUND_SPECIES, GROUND_POSITIONS)
            if species != CONTROL]


def _flying_actors():
    return [dict(generator=FLYING_IDS[index], species=species,
                 native_teki_type=P1_PUFFY_TYPE, xyz=tuple(FLYING_POSITIONS[index]))
            for index, species in enumerate(FLYING_SPECIES)]


def _aquatic_actors():
    return [dict(generator=generator, species=species,
                 native_teki_type=AQUATIC_PROXY[species], xyz=tuple(xyz))
            for generator, species, xyz in zip(AQUATIC_IDS, AQUATIC_SPECIES, AQUATIC_POSITIONS)
            if species != CONTROL]


FAMILIES = (
    dict(name='ground', batch=2, imported='ground', manifest='ground_inverts.json',
         prefix='ginv', cfg=BATCH2_FAMILIES['ground'], actors=_ground_actors(),
         native_setup='pc_p2_batch2_setup'),
    dict(name='flying', batch=3, imported='flying', manifest='flying.json',
         prefix='fly', cfg=None, actors=_flying_actors(),
         native_setup='pc_p2_batch3_setup'),
    dict(name='aquatic', batch=3, imported='aquatic', manifest='aquatic.json',
         prefix='aquatic', cfg=None, actors=_aquatic_actors(),
         native_setup='pc_p2_batch3_setup'),
)

# One ordinary P1 dwarf bulborb control for the whole scene, taken from the
# ground arena. The flying/aquatic arena controls are deliberately omitted so
# the baseline is a single ordinary actor rather than three duplicates.
CONTROL_ACTOR = dict(generator=GROUND_IDS[-1], species=CONTROL,
                     native_teki_type=P1_CHAPPY_TYPE, xyz=tuple(GROUND_POSITIONS[-1]))

EXPECTED_BINDS = tuple(f"{family['name']}|{actor['species']}"
                       for family in FAMILIES for actor in family['actors'])
EXPECTED_SPECIES = tuple(actor['species'] for family in FAMILIES
                         for actor in family['actors'])

EXCLUDED = {
    'snagret': ('output/p2-lane-verify/snagret has no snagret.json manifest and '
                'zero .mod poses; the native bank loader would abort on a missing pose bank'),
    'batch2_visual_only': ('dweevil/flora/cannon/waterwraith are visual-only '
                           '(no implemented source FSM) and are out of scope for the '
                           'implemented-species mixed scene'),
}

# PROPOSED for integration review; not accepted. Values are anchored on the
# staged bank size (ground 1,838,080 + flying 1,072,512 + aquatic 1,973,024 =
# 4,883,616 B) and a 60 fps target at 960x540.
PROPOSED_BUDGETS = {
    'status': 'proposed_not_accepted',
    'controlled_variables': '960x540 windowed, 20-red fixture squad, one private '
                            'Impact Site room, PIKMIN_PERF_STATS=1/PIKMIN_TICK_STATS=1',
    'total_pose_bank_bytes_max': 8 * 1024 * 1024,
    'current_total_pose_bank_bytes': 4883616,
    'target_mean_frame_ms_max': 16.7,
    'slowest_window_mean_ms_max': 20.0,
    'tracked_texture_peak_mib_max': 64,
    'notes': [
        'Mean frame time budget is a 60 fps window mean, not a per-frame p99.',
        'Process RSS is not printed by the native runtime; only renderer-tracked '
        'texture MiB is available as a coarse memory figure.',
        'Native per-setup pose-bank guard remains 48 MiB (pc_p2_batch2/batch3 ClipBytes '
        'budget); the proposed total is the committed on-disk bank, not the load ceiling.',
    ],
}

_BIND = re.compile(r'P2_BATCH([23])_BIND generator=(\d+) key=(\S+) '
                   r'visual_only=(\d) native_fsm=(\S+)')
_BANK2 = re.compile(r'P2_BATCH2_BANK total_mod_bytes=(\d+) species=(\d+)')
_BANK3 = re.compile(r'P2_BATCH3_BANK total_mod_bytes=(\d+) species=(\d+)')
_READY = re.compile(r'P2_ENEMY_READY species=(\S+)')
_WINDOW = re.compile(r'Experimental preview window set to 960x540 windowed and centered')
_EXTINCTION = re.compile(r'Extinction', re.IGNORECASE)


def roster(assets):
    """Append the combined 13-actor roster to the original practice records.

    The original map/collision/routes are preserved byte-identical. Generator
    position plus offset is translation only (zero offset); no source yaw is
    applied. The default generator scatter circle is zeroed by the deterministic
    fixture override, which is an engineered choice, not production placement.
    """
    assets = Path(assets)
    source = assets / 'dataDir/stages/practice/default.gen'
    header = source.read_bytes()[:24]
    practice = records(source)
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    enemy = next(r for r in candidates if r[72:76] == b'iket')
    used = {struct.unpack_from('<I', r, 8)[0] for r in practice}
    entries = list(practice)
    placements = []
    for family in FAMILIES:
        for actor in family['actors']:
            identity = actor['generator']
            if identity in used:
                raise ValueError('Arena generator ID collision: ' + str(identity))
            used.add(identity)
            row = bytearray(enemy)
            struct.pack_into('<I', row, 8, identity)
            row[16:48] = actor['species'].encode('ascii').ljust(32, b'\0')
            row[80] = actor['native_teki_type']
            write_position(row, actor['xyz'])
            entries.append(bytes(row))
            placements.append(dict(generator=identity, species=actor['species'],
                                   family=family['name'],
                                   native_teki_type=actor['native_teki_type'],
                                   expected_xyz=list(validate_position(row, actor['xyz'])),
                                   offset=[0, 0, 0], source_yaw=None,
                                   source_yaw_applied=False,
                                   proxy='P1 proxy placement vehicle; source P2 FSM '
                                         'registered separately by the native lane'))
    control = bytearray(enemy)
    struct.pack_into('<I', control, 8, CONTROL_ACTOR['generator'])
    control[16:48] = b'P1 Chappy control'.ljust(32, b'\0')
    control[80] = CONTROL_ACTOR['native_teki_type']
    write_position(control, CONTROL_ACTOR['xyz'])
    entries.append(bytes(control))
    placements.append(dict(generator=CONTROL_ACTOR['generator'], species=CONTROL,
                           family='control', native_teki_type=CONTROL_ACTOR['native_teki_type'],
                           expected_xyz=list(validate_position(control, CONTROL_ACTOR['xyz'])),
                           offset=[0, 0, 0], source_yaw=None, source_yaw_applied=False,
                           proxy='ordinary P1 control'))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def normalize_pose_names(run, prefix, bank_name):
    """Copy misindexed pose files to the contiguous names the native loader builds.

    The converted banks may name a clip's first pose ``_01`` where the native
    loader reconstructs ``_00``. This is a private fixture normalization only; no
    shared converter, install receipt or committed asset is changed.
    """
    room = Path(run) / 'assets/dataDir/courses/pikmin2room'
    bank = (Path(run) / bank_name).read_text().splitlines()
    normalized = []
    for line in bank:
        tokens = line.split()
        if not tokens or tokens[0] != 'clip':
            continue
        species, clip, poses = tokens[1], tokens[2], int(tokens[6])
        for index in range(poses):
            expected = room / f'{prefix}_{species}_{clip}_{index:02d}.mod'
            if expected.exists():
                continue
            candidates = sorted(room.glob(f'{prefix}_{species}_{clip}_*.mod'))
            if not candidates:
                continue
            expected.write_bytes(candidates[0].read_bytes())
            normalized.append(dict(species=species, clip=clip, index=index,
                                   source=candidates[0].name, target=expected.name))
    return normalized


def _family_metrics(imported, manifest, species):
    metadata = json.loads((Path(imported) / manifest).read_text())
    files = 0
    size = 0
    for name in species:
        for clip in metadata['species'][name].get('clips', []):
            for pose in clip.get('poses', []):
                if 'file' in pose:
                    files += 1
                    size += pose.get('bytes', 0)
    return dict(pose_files=files, pose_bytes=size)


def _install_family(family, imported, run):
    fam_imported = Path(imported) / family['imported']
    actors = [(actor['generator'], actor['species']) for actor in family['actors']]
    if family['batch'] == 2:
        receipt = batch2_install(family['cfg'], fam_imported, run, actors)
        verified = batch2_verify(family['cfg'], fam_imported, run, actors)
    elif family['name'] == 'flying':
        receipt = flying_install(fam_imported, run, actors)
        verified = flying_verify(fam_imported, run, actors)
    else:
        receipt = aquatic_install(fam_imported, run, actors)
        verified = aquatic_verify(fam_imported, run, actors)
    normalized = normalize_pose_names(run, family['prefix'],
                                      f"p2-{family['name']}-bank.txt")
    return receipt, verified, normalized


def prepare(assets, imported, output, families=FAMILIES):
    """Build one private mixed-scene run directory both native registries read."""
    assets = Path(assets).resolve()
    imported = Path(imported).resolve()
    output = Path(output).resolve()
    data, actors = roster(assets)
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): _sha(path.read_bytes())
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    output.mkdir(parents=True, exist_ok=True)
    run = output / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt': b'P1 original stage arena\n'}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'assets/dataDir/courses/pikmin2room').mkdir(parents=True, exist_ok=True)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [actor['generator'] for actor in actors])
    receipts = {}
    verified = {}
    normalized = {}
    for family in families:
        receipt, proof, fixes = _install_family(family, imported, run)
        receipts[family['name']] = receipt
        verified[family['name']] = proof
        normalized[family['name']] = fixes
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if _sha((run / 'assets' / name).read_bytes()) != value:
            raise ValueError('Original course changed')
    scene = dict(
        schema=1, scene='P1 Impact Site', stage_slot='chal0', window=WINDOW,
        actor_count=len(actors), species_count=sum(len(f['actors']) for f in families),
        control=CONTROL_ACTOR, control_omitted_families=['flying', 'aquatic'],
        families={family['name']: dict(
            batch=family['batch'], imported=family['imported'],
            manifest=family['manifest'], prefix=family['prefix'],
            native_setup=family['native_setup'],
            registered=[[actor['generator'], actor['species']] for actor in family['actors']],
            receipt_visuals=receipts[family['name']].get('visuals'),
            **_family_metrics(imported / family['imported'], family['manifest'],
                              [actor['species'] for actor in family['actors']]))
            for family in families},
        actors=actors, expected_binds=list(EXPECTED_BINDS),
        excluded=EXCLUDED,
        install_receipts={name: receipts[name] for name in receipts},
        install_verified={name: verified[name] for name in verified},
        pose_name_normalization={name: normalized[name] for name in normalized},
        source_stage_sha256=_sha(stage.read_bytes()),
        preserved_course_sha256=preserved,
        birth_policy=birth,
        scatter='Default generator scatter circle zeroed by deterministic fixture '
                'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                'production placement evidence',
        command=['nectar.exe', '--experimental-pikmin2-room'],
        placement_choice='Engineered arena coordinates; terrain/physical spawn '
                         'acceptance unmeasured',
        proposed_budgets=PROPOSED_BUDGETS,
        gates=dict(
            mixed_scene_correctness='untested: collected by mixed-scene-validation.json',
            frame_time='untested: collected by mixed-scene-validation.json',
            memory='untested: collected by mixed-scene-validation.json'),
        limitations=['Measurement fixture, not production placement evidence.',
                     'Process RSS is not printed; only renderer-tracked texture MiB is available.',
                     'Single disposable room with a 20-red starting squad; not a campaign scene.',
                     'Source yaw unapplied and generator scatter zeroed by fixture override.',
                     'Snagret excluded (no manifest / zero poses); batch-2 visual-only '
                     'families excluded (no implemented source FSM).'])
    (run / 'mixed-scene.json').write_text(json.dumps(scene, indent=2, sort_keys=True) + '\n')
    return run


def run(assets, imported, output, exe, seconds=90):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = WINDOW
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text)
    result['capture'] = {key: meta[key] for key in
                         ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}
    (run_dir / 'mixed-scene-validation.json').write_text(
        json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text):
    """Parse a native log against the mixed-scene contract.

    Confined to bind/bank/enemy-ready/perf markers so it makes no claim about
    unrelated families, production placement or unmeasured subsystems.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    binds = {}
    for match in _BIND.finditer(text):
        binds[match.group(3)] = dict(batch=int(match.group(1)), generator=int(match.group(2)),
                                     visual_only=int(match.group(4)), native_fsm=match.group(5))
    bound = set(binds)
    missing = sorted(set(EXPECTED_BINDS) - bound)
    unexpected = sorted(bound - set(EXPECTED_BINDS))
    ready = sorted({match.group(1) for match in _READY.finditer(text)})
    bank2 = _BANK2.search(text)
    bank3 = _BANK3.search(text)
    batch2_bank = dict(total_mod_bytes=int(bank2.group(1)), species=int(bank2.group(2))) if bank2 else None
    batch3_bank = dict(total_mod_bytes=int(bank3.group(1)), species=int(bank3.group(2))) if bank3 else None
    total = sum(x['total_mod_bytes'] for x in (batch2_bank, batch3_bank) if x)
    profile = parse_log(text, warmup_windows=1)
    frame = profile['presentation']
    tick = profile['last_tick_window']
    textures = profile['texture_memory']
    checks = dict(
        binds=not missing,
        bank=bool(batch2_bank and batch3_bank),
        enemy_ready=set(EXPECTED_SPECIES) <= set(ready),
        window=bool(_WINDOW.search(text)),
        frame_time=frame is not None,
        no_extinction=not _EXTINCTION.search(text),
    )
    return dict(
        passed=all(checks.values()), checks=checks,
        expected_binds=list(EXPECTED_BINDS), bound_binds=sorted(bound), binds=binds,
        missing_binds=missing, unexpected_binds=unexpected,
        enemy_ready=ready,
        batch2_bank=batch2_bank, batch3_bank=batch3_bank, total_pose_bank_bytes=total,
        frame_time=frame, tick=tick, texture_memory=textures,
        perf_windows_seen=profile['perf_windows_seen'],
        proposed_budgets=PROPOSED_BUDGETS,
        budget_assessment=_assess(total, frame, textures),
        unmeasured=['total process RSS', 'per-frame presentation p99',
                    'long-duration soak / re-entry', 'camera-driven density sweep'],
        limitations=['Native log markers describe this 960x540 fixture room only.',
                     'Frame-time window means are not individual frame samples.',
                     'Renderer-tracked texture MiB is not total process memory.'])


def _assess(total, frame, textures):
    budgets = PROPOSED_BUDGETS
    result = {'total_pose_bank_bytes': dict(
        measured=total, budget=budgets['total_pose_bank_bytes_max'],
        within=total <= budgets['total_pose_bank_bytes_max'])}
    if frame is not None:
        result['mean_frame_ms'] = dict(
            measured=frame['mean_frame_ms'],
            budget=budgets['target_mean_frame_ms_max'],
            within=frame['mean_frame_ms'] <= budgets['target_mean_frame_ms_max'])
        result['slowest_window_mean_ms'] = dict(
            measured=frame['slowest_window_mean_ms'],
            budget=budgets['slowest_window_mean_ms_max'],
            within=frame['slowest_window_mean_ms'] <= budgets['slowest_window_mean_ms_max'])
    else:
        result['mean_frame_ms'] = dict(measured=None, budget=budgets['target_mean_frame_ms_max'],
                                       within=None)
    if textures is not None:
        last = textures.get('last') or {}
        peak = last.get('peak_mib_rounded_down', textures.get('maximum_reported_mib'))
        result['tracked_texture_peak_mib'] = dict(
            measured=peak, budget=budgets['tracked_texture_peak_mib_max'],
            within=peak is not None and peak <= budgets['tracked_texture_peak_mib_max'])
    else:
        result['tracked_texture_peak_mib'] = dict(
            measured=None, budget=budgets['tracked_texture_peak_mib_max'], within=None)
    result['status'] = 'proposed_not_accepted'
    return result


def _sha(data):
    return hashlib.sha256(data).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=90)
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output,
                                    args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
