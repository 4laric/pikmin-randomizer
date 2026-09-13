"""Shared hash-bound installer and private-arena builder for the P2 batch-2 lanes.

Batch 2 (pipeline section 4) takes a batch-1 source-contract manifest into the
runtime: it installs exact-byte visual/config artifacts into a private run and
stages an engineered original-map arena. This module is the common engine shared
by the remaining lanes - #349 Dweevil, #353 Flora/Candypop, #346 Ground
invertebrates, #350 Cannon/projectile and #352 Waterwraith/Tyre - modeled on the
completed ``pikmin2_aquatic_install.py`` (#374), ``pikmin2_flying_install.py``
(#375) and ``pikmin2_snagret_install.py`` (#376).

Family facts live in ``pikmin2_batch2_families.py``; the thin per-family modules
just bind a config. Native registration/hook wiring is integration-lead work
(#186) and is never performed here. No shared/native code is touched and no disc
assets or generated models are committed.
"""
import hashlib
import json
import struct
from pathlib import Path

from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_generator_pose import validate_position, write_position
from experimental.pikmin2_uji_grounded_fixture import deterministic_births

# P1 teki types from engine/include/teki.h (GPVE01/GPIP01 symbols). The value 3
# (Chappy, Dwarf Bulborb) is the ordinary control / neutral placement vehicle
# used by every lane here; family actors with a P1 ancestor may use that
# ancestor's type as an explicit proxy.
P1_CHAPPY_TYPE = 3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _num(value):
    return f'{value:g}'


def _parm(block):
    return ' '.join(f'{key}={_num(block[key])}' for key in sorted(block))


def profile_text(cfg, manifest):
    """Canonical LF per-species parameter/profile contract from the manifest.

    The general block is always ``parameter_blocks[1]``. A proper block is
    written only when the manifest carries retail proper values (``proper_retail``);
    prop flora has no proper block and is written as ``-``.
    """
    rows = [cfg['profile_header']]
    for species, identity in cfg['species'].items():
        info = manifest['species'][species]
        blocks = info.get('parameter_blocks', [])
        if not 1 < len(blocks) <= 3:
            raise ValueError('Unexpected parameter block framing: ' + species)
        rows.append(f'species {species} {identity}')
        role = info.get('role') or info.get('classification', '')
        rows.append(f'role {species} {role}'.rstrip())
        rows.append(f'general {species} {_parm(blocks[1])}')
        proper = info.get('proper_retail')
        if proper is None and len(blocks) == 3:
            proper = blocks[2]
        rows.append(f'proper {species} {_parm(proper) if proper else "-"}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def bank_text(cfg, manifest):
    """Canonical LF clip/frame/event/pose listing for every sourced species."""
    rows = [cfg['bank_header']]
    for species in cfg['species']:
        info = manifest['species'][species]
        rows.append(f'species {species} {info["enemy_id"]}')
        for clip in info.get('clips', []):
            pose_list = clip.get('poses', [])
            poses = sum(1 for pose in pose_list if 'file' in pose)
            # The native bank loads pose `NN` by contiguous 0-based index, so a
            # clip is banked only when its first `poses` slots are all sampled
            # (no leading/interior gap); unsupported or gapped clips are skipped.
            if poses == 0 or any('file' not in pose for pose in pose_list[:poses]):
                continue
            events = ','.join(f'{frame}:{event}' for frame, event in clip.get('events', []))
            rows.append(f'clip {species} {clip["name"]} {clip.get("source_frames", 0)} '
                        f'{events or "-"} poses {poses} {clip.get("status", "unknown")}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def actors_text(cfg, actors):
    rows = [cfg['actors_header'], str(len(actors))]
    rows += [f'{generator} {species}' for generator, species in actors]
    return ('\n'.join(rows) + '\n').encode('ascii')


def _actor_species(cfg, actors):
    used = {species for _, species in actors}
    return [species for species in cfg['species'] if species in used]


def _visual_files(cfg, imported, manifest, species_list):
    """Return installed-name -> exact bytes, or {} for a preserved baseline.

    The bank is all-or-nothing over the actor species: a partial bank, a stray
    ``.mod`` or any SHA-256 mismatch is refused before the caller mutates
    anything.
    """
    expected = {}
    for species in species_list:
        info = manifest['species'][species]
        for clip in info.get('clips', []):
            for pose in clip.get('poses', []):
                if 'file' not in pose:
                    continue
                name = pose['file']
                digest = pose.get('sha256')
                if Path(name).name != name or not name.endswith('.mod'):
                    raise ValueError('Unsafe pose filename')
                if not isinstance(digest, str) or len(digest) != 64:
                    raise ValueError('Missing pose SHA-256: ' + name)
                if (species, name) in expected:
                    raise ValueError('Duplicate pose entry: ' + name)
                expected[(species, name)] = digest
    found = {key for key in expected if (imported / key[0] / key[1]).is_file()}
    stray = sorted(f'{species}/{path.name}'
                   for species in species_list
                   for path in (imported / species).glob('*.mod')
                   if (species, path.name) not in expected)
    files = {}
    if found or stray:
        if found != set(expected) or stray:
            raise ValueError('Incomplete/unexpected ' + cfg['name'] + ' visual bank: '
                             + ', '.join(stray))
        for (species, name), digest in expected.items():
            data = (imported / species / name).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + name)
            files[name] = data
    return files


def _check_sibling_overlap(run, ids):
    for other in sorted(run.glob('p2-*-actors.txt')):
        tokens = other.read_text().split()
        if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_1'):
            raise ValueError('Invalid existing actor bindings: ' + other.name)
        used = set()
        for token in tokens[2:]:
            try:
                used.add(int(token))
            except ValueError:
                pass  # species/id columns in legacy row formats
        if used & set(ids):
            raise ValueError('Generator ID overlap with ' + other.name)


def plan(cfg, imported, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(profile_payload, bank_payload, actors_payload, files, metadata)``.
    """
    actors = list(actors)
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = set()
    for generator_id, species in actors:
        if (type(generator_id) is not int or not 0 <= generator_id <= 0xffffffff
                or generator_id in ids):
            raise ValueError('Invalid/duplicate actor identity')
        if species not in cfg['species']:
            raise ValueError('Unsupported ' + cfg['name'] + ' actor species: ' + str(species))
        ids.add(generator_id)
    metadata = json.loads((imported / cfg['manifest']).read_bytes())
    if metadata.get('schema') != 1 or metadata.get('policy') != cfg['policy']:
        raise ValueError('Unsupported ' + cfg['name'] + ' import schema/policy')
    if metadata.get('disc_id') != 'GPVE01' or metadata.get('disc_revision') != 0:
        raise ValueError('Unexpected ' + cfg['name'] + ' disc identity')
    if set(metadata.get('species', {})) != set(cfg['species']):
        raise ValueError(cfg['name'] + ' species set mismatch')
    for species, identity in cfg['species'].items():
        if metadata['species'][species].get('enemy_id') != identity:
            raise ValueError(cfg['name'] + ' species/ID mismatch: ' + species)
    species_list = _actor_species(cfg, actors)
    for species in species_list:
        by_clip = {clip['name']: clip for clip in metadata['species'][species].get('clips', [])}
        for anchor in cfg['anchors'][species]:
            clip = by_clip.get(anchor)
            if clip is None or clip.get('status') != 'converted' or not clip.get('poses'):
                raise ValueError(f'Required {species} source anchor unavailable: ' + anchor)
    profile_payload = profile_text(cfg, metadata)
    bank_payload = bank_text(cfg, metadata)
    actors_payload = actors_text(cfg, actors)
    files = _visual_files(cfg, Path(imported), metadata, species_list)
    return profile_payload, bank_payload, actors_payload, files, metadata


def install(cfg, imported, run, actors):
    """Install validated configs (and optional visuals) into a private run."""
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, metadata = plan(cfg, imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / cfg['profile_txt'], run / cfg['bank_txt'], run / cfg['actors_txt'],
               run / cfg['install_json']]
    targets += [room / name for name in files]
    if any(target.exists() or target.is_symlink() for target in targets):
        raise ValueError('Refusing existing/conflicting ' + cfg['name'] + ' installation')
    ids = [generator_id for generator_id, _ in actors]
    _check_sibling_overlap(run, ids)
    for name, data in files.items():
        (room / name).write_bytes(data)
    (run / cfg['profile_txt']).write_bytes(profile_payload)
    (run / cfg['bank_txt']).write_bytes(bank_payload)
    (run / cfg['actors_txt']).write_bytes(actors_payload)
    receipt = dict(schema=1, policy=cfg['policy'], species=cfg['species'],
                   generators=ids,
                   actors=[[generator_id, species] for generator_id, species in actors],
                   manifest_sha256=sha((imported / cfg['manifest']).read_bytes()),
                   profile_config_sha256=sha(profile_payload),
                   bank_config_sha256=sha(bank_payload),
                   actors_config_sha256=sha(actors_payload),
                   visuals='installed' if files else 'absent_baseline_preserved',
                   file_sha256={name: sha(data) for name, data in files.items()},
                   gameplay_events_executed=False, native_ready=False,
                   native_registration='integration lead (#186); flagged on the lane issue; '
                                       'not installed here')
    (run / cfg['install_json']).write_bytes(
        (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode('ascii'))
    return receipt


def verify_install(cfg, imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    imported = Path(imported)
    run = Path(run)
    profile_payload, bank_payload, actors_payload, files, metadata = plan(cfg, imported, actors)
    room = run / 'assets/dataDir/courses/pikmin2room'
    if (run / cfg['profile_txt']).read_bytes() != profile_payload:
        raise ValueError('Installed profile config mismatch')
    if (run / cfg['bank_txt']).read_bytes() != bank_payload:
        raise ValueError('Installed bank config mismatch')
    if (run / cfg['actors_txt']).read_bytes() != actors_payload:
        raise ValueError('Installed actor config mismatch')
    if not (run / cfg['install_json']).is_file():
        raise ValueError('Installed receipt missing')
    receipt = json.loads((run / cfg['install_json']).read_text())
    if receipt.get('manifest_sha256') != sha((imported / cfg['manifest']).read_bytes()):
        raise ValueError('Installed receipt manifest mismatch')
    if receipt.get('actors_config_sha256') != sha(actors_payload):
        raise ValueError('Installed receipt actor hash mismatch')
    for name, data in files.items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed visual mismatch: ' + name)
    return {'verified': sorted(files), 'config': cfg['actors_txt'],
            'visuals': 'installed' if files else 'absent_baseline_preserved'}


def roster(cfg, assets):
    """Append the family roster to the original practice stage records.

    Original map/collision/routes are preserved byte-identical; one explicit
    actor per family species plus one ordinary P1 control. Generator position
    plus offset is translation only (zero offset); source yaw is recorded as
    unapplied metadata.
    """
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
    for identity, kind, xyz in zip(cfg['arena_ids'], cfg['arena_species'],
                                   cfg['arena_positions']):
        if identity in used:
            raise ValueError('Arena generator ID collision')
        used.add(identity)
        teki_type = cfg['arena_proxy'][kind]
        row = bytearray(enemy)
        struct.pack_into('<I', row, 8, identity)
        row[16:48] = kind.encode('ascii').ljust(32, b'\0')
        row[80] = teki_type
        write_position(row, xyz)
        entries.append(bytes(row))
        if kind == cfg['control']:
            proxy = 'ordinary P1 control'
        elif teki_type == P1_CHAPPY_TYPE:
            proxy = 'P1 Chappy placement vehicle only; species identity NOT claimed'
        else:
            proxy = (f'P1 {cfg["arena_family"][teki_type]} proxy; native ancestor, '
                     'not source P2 FSM')
        placements.append(dict(generator=identity, species=kind,
                               native_family=cfg['arena_family'][teki_type],
                               native_teki_type=teki_type,
                               proxy=proxy, expected_xyz=list(validate_position(row, xyz)),
                               offset=[0, 0, 0], source_yaw=cfg.get('source_yaw'),
                               source_yaw_applied=False))
    return header[:20] + struct.pack('>I', len(entries)) + b''.join(entries), placements


def prepare(cfg, assets, imported, output, installer=None, verifier=None):
    """Build a private arena run directory with the family visual bank installed.

    ``installer``/``verifier`` default to this module's generic operations; a
    family with a bespoke install schema (Long Legs, #312) passes its own.
    """
    installer = installer or install
    verifier = verifier or verify_install
    assets = assets.resolve()
    imported = imported.resolve()
    data, actors = roster(cfg, assets)
    family = tuple(s for s in cfg['arena_species'] if s != cfg['control'])
    registered = [(a['generator'], a['species']) for a in actors if a['species'] in family]
    stage = assets / 'dataDir/stages/practice.ini'
    course = assets / 'dataDir/courses/practice'
    preserved = {str(path.relative_to(assets)).replace('\\', '/'): sha(path.read_bytes())
                 for path in course.rglob('*') if path.is_file()}
    if not preserved:
        raise ValueError('Original Impact Site course missing')
    run = output.resolve() / __import__('uuid').uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': stage.read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/arena-private.txt':
                     b'P1 original stage arena\n'}
    for path in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + path.name, empty)
    overlay(assets, run / 'assets', overrides)
    birth = deterministic_births(run / 'assets/dataDir/stages/chal0/default.gen',
                                 [a['generator'] for a in actors])
    receipt = installer(imported, run, registered)
    verified = verifier(imported, run, registered)
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    for name, value in preserved.items():
        if sha((run / 'assets' / name).read_bytes()) != value:
            raise ValueError('Original course changed')
    result = dict(schema=1, scene='P1 Impact Site', stage_slot='chal0', actors=actors,
                  enemy_count=len(registered), control=cfg['control'],
                  source_stage_sha256=sha(stage.read_bytes()),
                  preserved_course_sha256=preserved,
                  import_sha256=sha((imported / cfg['manifest']).read_bytes()),
                  install=receipt, install_verified=verified, birth_policy=birth,
                  scatter='Default generator scatter circle zeroed by deterministic fixture '
                          'override (PRIVATE_CIRCLE_RADIUS_ZERO_1); engineered choice, not '
                          'production placement evidence',
                  command=['nectar.exe', '--experimental-pikmin2-room'],
                  placement_choice='Engineered arena coordinates; terrain/physical spawn '
                                   'acceptance unmeasured',
                  gates={key: cfg['blocked'].get(key, 'untested') for key in cfg['gates']},
                  limitations=list(cfg['limitations']))
    (run / 'arena.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    return run
