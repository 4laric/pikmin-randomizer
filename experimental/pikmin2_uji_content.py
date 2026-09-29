"""Stage the Uji family (UjiA 12, UjiB 13, Tobi 14) campaign-identity files.

The campaign-identity Uji loader (``pc_p2_uji_*``, built alongside this lane)
opens two sidecars plus the sampled pose meshes, mirroring the shared batch-2
ground grammar exactly:

* ``p2-uji-actors.txt``: ``P2_UJI_ACTORS_1 <count>`` then one
  ``<generator> <Species>`` row per seed actor (grammar mirrors
  ``engine/pc_port/pc_p2_batch2.cpp:122-138`` ``parseActors``: ``P2_`` prefix,
  ``_ACTORS_1`` suffix, 1..100 rows, uint32 generators, no trailing data).
* ``p2-uji-bank.txt``: ``P2_UJI_BANK_1`` header, one
  ``species <Species> <id>`` row per staged species, then one
  ``clip <Species> <name> <source_frames> <events|-> poses <n> converted`` row
  per converted clip (grammar mirrors ``engine/pc_port/pc_p2_batch2.cpp:140-170``
  ``parseBank``: ``species`` rows before ``clip`` rows, ``poses`` marker,
  0..64 poses; events encoded ``frame:kind,...`` exactly as
  ``experimental.pikmin2_batch2_core.bank_text`` writes them).
* ``assets/dataDir/courses/pikmin2room/uji_<Species>_<clip>_%02d.mod``: byte
  copies of the sampled pose meshes, hash-bound to the manifest (filename shape
  mirrors ``engine/pc_port/pc_p2_batch2.cpp:95-120`` ``loadPose`` with the
  ``uji`` family prefix, and the proxy-visual precedent that opens the same
  shape: ``engine/pc_port/pc_p2_sheargrub.cpp:34``
  ``assets/.../pikmin2room/uji_<Species>_<clip>_%02d.mod``).

The extractor (:mod:`experimental.pikmin2_uji_assets`) produces one source art
tree per species under the content root (``<content>/UjiA/``, ``<content>/UjiB/``,
``<content>/Tobi/``: ``uji.json`` plus the ``uji_<Species>_<clip>_%02d.mod``
pose meshes); this module carries that art to where the native loader opens
it. It never extracts assets and never commits retail data.

Source layout (one extracted ``<content>/<Species>/`` tree per bound species):

* ``uji.json`` (schema 1, species ``<Species>``, matching enemy_id): per-clip
  ``file`` (``<clip>.bca``), ``events`` (``[[frame, kind], ...]``),
  ``source_frames`` (BCA duration), ``sha256`` (raw BCA hash), ``status``
  (``converted``) and ``poses`` (``frame``, ``file``
  (``uji_<Species>_<clip>_%02d.mod``), ``bytes``, ``sha256``).
* The referenced ``uji_<Species>_<clip>_%02d.mod`` pose meshes.

Staged layout (run directory): ``p2-uji-actors.txt`` + ``p2-uji-bank.txt`` +
the room meshes for the bound species only (bank blocks in canonical
UjiA/UjiB/Tobi order, so the bytes are independent of binding order).

Idempotent like the Sokkuri adapter: all payloads are computed and validated
before any mutation; a second call over the same run is a no-op success when
every staged file is byte-identical, and any conflicting staged file is
refused with ``StagingError`` before anything is written. A missing or
mismatched source file raises ``StagingError`` -- never fabricates a pose or
an event.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_animation import frames_trailer
from experimental.pikmin2_staging import StagingError

UJI_SPECIES = {'UjiA': 12, 'UjiB': 13, 'Tobi': 14}
CANONICAL_ORDER = ('UjiA', 'UjiB', 'Tobi')
MANIFEST = 'uji.json'
ACTORS_TXT = 'p2-uji-actors.txt'
BANK_TXT = 'p2-uji-bank.txt'
ACTORS_HEADER = 'P2_UJI_ACTORS_1'
BANK_HEADER = 'P2_UJI_BANK_1'
ROOM = Path('assets/dataDir/courses/pikmin2room')

_CLIP_RE = re.compile(r'[a-z0-9_]+\.bca')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')
# Native loadPose grammar with the uji family prefix
# (engine/pc_port/pc_p2_batch2.cpp:95-120; proxy precedent
# engine/pc_port/pc_p2_sheargrub.cpp:34): uji_<Species>_<clip>_%02d.mod.
_POSE_RES = {species: re.compile(r'uji_%s_([a-z0-9_]+)_([0-9]{2})\.mod' % species)
             for species in UJI_SPECIES}

# Native bank clip-row budget (pc_p2_batch2.cpp:152-155): poses in 0..64.
_MAX_BANK_POSES = 64

# The staged bank must serve the family arena without the native draw path
# falling back to nothing: every Uji species walks (move) and dies (dead), so
# both anchors are required converted. (The proxy-visual installer requires the
# same two source poses: experimental/pikmin2_sheargrub_install.py plan.)
REQUIRED_CLIPS = {'UjiA': ('move', 'dead'), 'UjiB': ('move', 'dead'),
                  'Tobi': ('move', 'dead')}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _events_token(clip_name, events):
    """Encode one clip's events exactly as bank_text does (``-`` when empty)."""
    if not events:
        return '-'
    return ','.join(f'{frame}:{kind}' for frame, kind in events)


def _check_events(species, clip_name, duration, events):
    """Mirror the native bank/event grammar so every staged row always parses.

    Covers ``parseEvents`` (``pc_p2_batch2_clock.h:102-136``: ``-`` or
    ``frame:key,...`` with frame in 0..100000) and the per-species consumer
    (comma/colon split, ``atoi`` both sides, as in
    ``pc_p2_sokkuri.cpp:357-371``), plus the loop-pairing rule the Sokkuri
    adapter enforces for kinds 0/1.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'Uji {species} clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'Uji {species} clip event budget exceeded: {clip_name}')
    previous, loop_start = -1, None
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'Uji {species} clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame >= duration or frame > 100000:
            raise StagingError(f'Uji {species} clip event outside the native clip: {clip_name}')
        if not 0 <= kind < 1000:
            raise StagingError(f'Uji {species} clip event kind outside the native range: {clip_name}')
        if kind == 0:
            loop_start = frame
        if kind == 1 and (loop_start is None or frame <= loop_start):
            raise StagingError(f'Uji {species} clip event loop unmatched: {clip_name}')
        previous = frame


def _load_manifest(species_dir, species):
    """Read and validate one extracted Uji species manifest; fail closed."""
    species_dir = Path(species_dir)
    path = species_dir / MANIFEST
    if not path.is_file():
        raise StagingError(f'Uji {species} manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Uji {species} manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Uji {species} manifest schema mismatch for identity content: {path}')
    if document.get('species') != species or document.get('enemy_id') != UJI_SPECIES[species]:
        raise StagingError(f'Uji {species} manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'Uji {species} manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(species, document):
    """Return the validated converted clips in manifest order with their poses."""
    seen = set()
    converted = []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(
                f'Uji {species} clip name rejected by the native bank grammar: {name!r}')
        if name in seen:
            raise StagingError(f'Uji {species} clip ambiguous for identity content: {name}')
        seen.add(name)
        if clip.get('status') != 'converted':
            continue
        poses = clip.get('poses')
        if not isinstance(poses, list) or not poses:
            raise StagingError(f'Uji {species} clip carries no poses for identity content: {name}')
        if len(poses) > _MAX_BANK_POSES:
            raise StagingError(f'Uji {species} clip exceeds the native bank budget: {name}')
        stem = name[:-4]
        pose_re = _POSE_RES[species]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get('frame')
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(f'Uji {species} pose frames are not strictly increasing in {name}')
            previous = frame
            filename = pose.get('file')
            match = pose_re.fullmatch(filename) if isinstance(filename, str) else None
            if match is None or match.group(1) != stem or int(match.group(2)) != index:
                raise StagingError(
                    f'Uji {species} pose filename breaks the native loadPose sequence: {filename!r}')
            digest = pose.get('sha256')
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(
                    f'Uji {species} pose SHA-256 missing for identity content: {filename}')
        _check_events(species, name, clip.get('source_frames'), clip.get('events', []))
        converted.append(clip)
    present = {Path(clip['file']).stem for clip in converted}
    for required in REQUIRED_CLIPS[species]:
        if required not in present:
            raise StagingError(
                f'Uji {species} anchor unavailable for identity content: {required}')
    return converted


def _mesh_bytes(species_dir, species, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(species_dir) / pose['file']
    if not path.is_file():
        raise StagingError(f'Uji {species} pose mesh missing for identity content: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'Uji {species} pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'Uji {species} pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'Uji {species} pose mesh empty for identity content: {path}')
    return data


def validate_source(source):
    """Pre-flight check for one extracted Uji species tree, without writing.

    ``source`` is the ``<content>/<Species>/`` directory. Mirrors the
    source-side requirements of :func:`stage_uji` so a wrong/missing source is
    rejected before any run destination is prepared; the stager re-checks the
    full contract and remains authoritative.
    """
    source = Path(source)
    species = source.name
    if species not in UJI_SPECIES:
        raise StagingError(f'Uji source directory names no Uji species: {source}')
    document, _raw = _load_manifest(source, species)
    clips = _clip_poses(species, document)
    for clip in clips:
        for pose in clip['poses']:
            _mesh_bytes(source, species, pose)
    return True


def _species_source(content_root, species):
    """Resolve one bound species' source dir under the content root."""
    path = Path(content_root) / species
    if not (path / MANIFEST).is_file():
        raise StagingError(f'Uji {species} manifest missing for identity content: {path / MANIFEST}')
    return path


def plan(content_root, actors):
    """Validate everything and return exact payloads; never writes.

    ``content_root`` is the identity-keyed root whose ``<Species>/`` children
    hold every bound species' ``uji.json``; ``actors`` is the seed's
    ``[(generator_id, <Species>), ...]`` bindings. Returns
    ``(actors_payload, bank_payload, mesh_files, manifest_digests)`` where
    ``mesh_files`` maps room-relative mesh names to bytes and
    ``manifest_digests`` maps species to its manifest sha256.
    """
    content_root = Path(content_root)
    actors = list(actors)
    if not actors:
        raise StagingError('Uji install requires at least one generator')
    seen_generators = set()
    bound_species = []
    for generator, species in actors:
        if species not in UJI_SPECIES:
            raise StagingError(f'Uji adapter got non-Uji species: {species!r}')
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'Uji actor generator out of native range: {generator!r}')
        if generator in seen_generators:
            raise StagingError('Uji actor generators are not unique')
        seen_generators.add(generator)
        if species not in bound_species:
            bound_species.append(species)
    ordered = [species for species in CANONICAL_ORDER if species in bound_species]

    manifests = {}
    for species in ordered:
        species_dir = _species_source(content_root, species)
        document, raw = _load_manifest(species_dir, species)
        manifests[species] = (species_dir, document, _sha(raw))

    actor_lines = [ACTORS_HEADER, str(len(actors))]
    actor_lines.extend(f'{generator} {species}' for generator, species in actors)
    actors_payload = ('\n'.join(actor_lines) + '\n').encode('ascii')

    bank_lines = [BANK_HEADER]
    mesh_files = {}
    for species in ordered:
        species_dir, document, _digest = manifests[species]
        bank_lines.append(f'species {species} {UJI_SPECIES[species]}')
        for clip in _clip_poses(species, document):
            name = Path(clip['file']).stem
            poses = clip['poses']
            token = _events_token(clip['file'], clip.get('events', []))
            bank_lines.append(f'clip {species} {name} {clip["source_frames"]} '
                              f'{token} poses {len(poses)} converted'
                              + frames_trailer(poses, clip['source_frames']))
            for pose in poses:
                data = _mesh_bytes(species_dir, species, pose)
                if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                    raise StagingError(f'Uji pose mesh name collision: {pose["file"]}')
                mesh_files[pose['file']] = data
    bank_payload = ('\n'.join(bank_lines) + '\n').encode('ascii')
    return (actors_payload, bank_payload, mesh_files,
            {species: digest for species, (_, _, digest) in manifests.items()})


def stage_uji(content_root, run, actors):
    """Stage the campaign-identity Uji files from extracted Uji trees.

    ``content_root`` is the identity-keyed root holding each bound species'
    ``<Species>/uji.json`` tree; ``run`` is the run directory whose text-bank
    slots and ``assets/dataDir/courses/pikmin2room/`` room receive the staged
    files; ``actors`` is the seed's ``[(generator_id, <Species>), ...]``
    bindings. Idempotent: a second call over the same run is a no-op success
    when every staged file is byte-identical; a conflicting staged file is
    refused with ``StagingError`` before any write.
    """
    content_root, run = Path(content_root), Path(run)
    actors = list(actors)
    if not run.is_dir():
        raise StagingError(f'Uji run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Uji room directory missing for run staging: {room}')
    actors_payload, bank_payload, mesh_files, digests = plan(content_root, actors)
    targets = {ACTORS_TXT: actors_payload, BANK_TXT: bank_payload}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Uji staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(family='uji', staged=staged, manifest_sha256=digests,
                   generators=[int(generator) for generator, _species in actors],
                   species=sorted({species for _, species in actors}),
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content-root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 219012:UjiA')
    args = parser.parse_args()
    actors = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(stage_uji(args.content_root, args.run, actors),
                     sort_keys=True, indent=2))
