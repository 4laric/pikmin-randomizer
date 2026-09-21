"""Stage the data-driven campaign-proxy sidecars and pose files into a run.

The native ``proxy`` family reads three staged files from the session run
directory plus the sampled pose meshes:

* ``p2-proxy-campaign.txt``: ``P2_PROXY_CAMPAIGN_1 <count>`` then one
  ``<source_id> <Species> <host_teki_type>`` row per proxy species.
* ``p2-proxy-actors.txt``: ``P2_PROXY_ACTORS_1 <count>`` then one
  ``<generator_id> <Species>`` row per seed actor.
* ``p2-proxy-bank.txt``: the ``p2-ground-bank.txt`` grammar (one
  ``species <Species> <source_id>`` row plus one
  ``clip <Species> <name> <source_frames> <events|-> poses <n> converted``
  row per converted clip) under the ``P2_PROXY_BANK_1`` header.
* ``assets/dataDir/courses/pikmin2room/px_<Species>_<clip>_%02d.mod``: byte
  copies of the sampled pose meshes, hash-bound to each species' manifest.

The extractor (:mod:`experimental.pikmin2_proxy_assets`) produces the source
art under ``<content>/<Enum>/`` (``proxy.json`` plus the ``px_*.mod`` pose
meshes); this module carries that art to where the native loader opens it,
deriving the campaign/actors/bank rows in the exact shape the native parsers
accept. It never extracts assets and never commits retail data.

Source layout (extracted ``<content>/<Enum>/`` tree per proxy species):

* ``proxy.json`` (schema 1, species ``<Enum>``, enemy_id ``<source_id>``):
  per-clip ``file`` (``<clip>.bca``), ``events`` (``[[frame, kind], ...]``),
  ``source_frames`` (BCA duration), ``sha256`` (raw BCA hash), ``status``
  (``converted``) and ``poses`` (``frame``, ``file``
  (``px_<Enum>_<clip>_%02d.mod``), ``bytes``, ``sha256``).
* The referenced ``px_<Enum>_<clip>_%02d.mod`` pose meshes.

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

from experimental.pikmin2_staging import StagingError

MANIFEST = 'proxy.json'
CAMPAIGN_TXT = 'p2-proxy-campaign.txt'
ACTORS_TXT = 'p2-proxy-actors.txt'
BANK_TXT = 'p2-proxy-bank.txt'
CAMPAIGN_HEADER = 'P2_PROXY_CAMPAIGN_1'
ACTORS_HEADER = 'P2_PROXY_ACTORS_1'
BANK_HEADER = 'P2_PROXY_BANK_1'
ROOM = Path('assets/dataDir/courses/pikmin2room')

_ENUM_RE = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}')
# Clip stems keep the retail registry spelling, including the uppercase
# stems real species ship (BigTreasure preattackF/attackF/..., Kabuto
# K_wait/...). The native bank reader takes the clip name as an
# unrestricted whitespace-separated token (parseBank: `in >> name`) and
# formats it back into the pose filename, so anything but whitespace
# survives; this class matches the extractor's CLIP_STEM_RE so extraction
# output always passes staging.
_CLIP_RE = re.compile(r'[A-Za-z0-9_]+\.bca')
_HEX64_RE = re.compile(r'[0-9a-f]{64}')

# Native bank clip-row budget (pc_p2_batch2.cpp:152-155): poses in 0..64.
_MAX_BANK_POSES = 64

# Native sidecar caps (fail-closed here so staging never writes a file the
# native loader aborts on): p2-proxy-actors.txt holds at most 100 generator
# rows (pc_p2_batch2.cpp parseActors: count 1..100 else fail, and fail
# aborts), p2-proxy-campaign.txt at most 64 species rows
# (pc_p2_proxy_table.h: countValue 1..64 else the whole table is invalid and
# every proxy species silently unbinds). Anything past the cap is refused
# with StagingError -- never silently truncated -- whether or not the
# campaign path still reads the actors file (the table drives binding in
# campaign mode; the actors file is still written for the probe path).
_MAX_ACTORS_ROWS = 100
_MAX_CAMPAIGN_SPECIES = 64

# The native proxy path picks the clip from host state and falls back across
# these groups, so a staged species without a wait or a dead clip cannot
# serve the family.
WAIT_CLIPS = ('wait1', 'wait', 'wait2')
DEAD_CLIPS = ('dead', 'dead1', 'pdead1')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _proxy_rows():
    """Proxy declarations keyed by enum name (source_id, host_teki)."""
    from randomizer.p2_proxy import load_rows
    rows = {}
    for row in load_rows():
        rows[row['enum_name']] = (row['source_id'], row['host_teki'])
    if not rows:
        raise StagingError('Proxy family declares no species')
    return rows


def _normalize_actors(actors):
    """Accept a {generator: enum} mapping or [(generator, enum), ...] pairs."""
    rows = _proxy_rows()
    pairs = list(actors.items()) if isinstance(actors, dict) else list(actors)
    normalized = []
    for entry in pairs:
        try:
            generator, species = entry
        except (TypeError, ValueError):
            raise StagingError(f'Proxy actor entry malformed: {entry!r}') from None
        if type(generator) is not int or isinstance(generator, bool) \
                or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f'Proxy actor generator out of native range: {generator!r}')
        if not isinstance(species, str) or not _ENUM_RE.fullmatch(species):
            raise StagingError(f'Proxy actor species invalid: {species!r}')
        if species not in rows:
            raise StagingError(f'Proxy actor species not a proxy species: {species!r}')
        normalized.append((generator, species))
    if not normalized:
        raise StagingError('Proxy install requires at least one actor')
    if len({generator for generator, _ in normalized}) != len(normalized):
        raise StagingError('Proxy actor generators are not unique')
    if len(normalized) > _MAX_ACTORS_ROWS:
        raise StagingError(
            f'Proxy actor rows exceed the native 100-row cap: {len(normalized)}')
    return normalized


def _events_token(clip_name, events):
    """Encode one clip's events exactly as bank_text does (``-`` when empty)."""
    if not events:
        return '-'
    return ','.join(f'{frame}:{kind}' for frame, kind in events)


def _check_events(species, clip_name, duration, events):
    """Mirror the native bank/event grammar so every staged row always parses.

    Covers ``parseEvents`` (``pc_p2_batch2_clock.h:102-136``: ``-`` or
    ``frame:key,...`` with a digit frame in 0..100000 and any non-empty
    string key) and the per-species consumer
    (``pc_p2_sokkuri.cpp:357-371``: comma/colon split, ``atoi`` both sides).
    The native parser accepts unordered frames, any key string, and events
    at any frame regardless of the clip duration, and ``makeClip`` never
    validates events against duration -- so this check enforces no
    duration relation and no kind-0/1 loop-pairing rule. What stays is
    fail-closed in the safe direction: frames must be non-negative
    100000-bounded digits in strictly increasing order, kinds must be
    0..999 (written as ``frame:kind`` string keys the native side
    accepts), at most 4096 events per clip.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f'{species} clip duration out of native range: {clip_name}')
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f'{species} clip event budget exceeded: {clip_name}')
    previous = -1
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f'{species} clip event malformed: {clip_name}')
        frame, kind = entry
        if frame < previous or frame < 0 or frame > 100000:
            raise StagingError(f'{species} clip event outside the native clip: {clip_name}')
        if not 0 <= kind < 1000:
            raise StagingError(f'{species} clip event kind outside the native range: {clip_name}')
        previous = frame


def _load_manifest(species, source_id, source):
    """Read and validate one extracted proxy manifest; fail closed on mismatch."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f'Proxy manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Proxy manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1:
        raise StagingError(f'Proxy manifest schema mismatch for identity content: {path}')
    if document.get('species') != species or document.get('enemy_id') != source_id:
        raise StagingError(f'Proxy manifest identity mismatch for identity content: {path}')
    clips = document.get('clips')
    if not isinstance(clips, list) or not clips:
        raise StagingError(f'Proxy manifest carries no clips for identity content: {path}')
    return document, raw


def _clip_poses(species, document):
    """Return the validated converted clips in manifest order with their poses."""
    seen = set()
    converted = []
    for clip in document.get('clips', []):
        name = clip.get('file')
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(
                f'{species} clip name rejected by the native bank grammar: {name!r}')
        if name in seen:
            raise StagingError(f'{species} clip ambiguous for identity content: {name}')
        seen.add(name)
        if clip.get('status') != 'converted':
            continue
        poses = clip.get('poses')
        if not isinstance(poses, list) or not poses:
            raise StagingError(
                f'{species} clip carries no poses for identity content: {name}')
        if len(poses) > _MAX_BANK_POSES:
            raise StagingError(f'{species} clip exceeds the native bank budget: {name}')
        stem = name[:-4]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get('frame')
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(
                    f'{species} pose frames are not strictly increasing in {name}')
            previous = frame
            filename = pose.get('file')
            # The native loadPose opens exactly px_<species>_<clip>_%02d.mod
            # for 0..poseCount-1, so the manifest must name that exact
            # sequence. An exact comparison (not a regex) is required here:
            # clip stems legitimately contain underscores (Kabuto K_pivot,
            # hit_start), which a greedy species/clip split misparses.
            if filename != f'px_{species}_{stem}_{index:02}.mod':
                raise StagingError(
                    f'{species} pose filename breaks the native loadPose sequence: {filename!r}')
            digest = pose.get('sha256')
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(
                    f'{species} pose SHA-256 missing for identity content: {filename}')
        _check_events(species, name, clip.get('source_frames'), clip.get('events', []))
        converted.append(clip)
    if not converted:
        raise StagingError(f'{species} manifest carries no converted clips')
    present = {Path(clip['file']).stem for clip in converted}
    if not present & set(WAIT_CLIPS):
        raise StagingError(f'{species} proxy anchor unavailable for identity content: wait')
    if not present & set(DEAD_CLIPS):
        raise StagingError(f'{species} proxy anchor unavailable for identity content: dead')
    return converted


def _campaign_payload(species_list, rows):
    """Render P2_PROXY_CAMPAIGN_1 with one row per proxy species present."""
    lines = [CAMPAIGN_HEADER, str(len(species_list))]
    for species in species_list:
        source_id, host_teki = rows[species]
        lines.append(f'{source_id} {species} {host_teki}')
    return ('\n'.join(lines) + '\n').encode('ascii')


def _actors_payload(actors):
    """Render P2_PROXY_ACTORS_1 from the proxy generator bindings."""
    lines = [ACTORS_HEADER, str(len(actors))]
    lines.extend(f'{generator} {species}'
                 for generator, species in sorted(actors, key=lambda pair: pair[0]))
    return ('\n'.join(lines) + '\n').encode('ascii')


def _bank_payload(documents):
    """Render P2_PROXY_BANK_1 with one species row plus clip rows per species."""
    lines = [BANK_HEADER]
    for species in sorted(documents):
        document, source_id = documents[species]
        lines.append(f'species {species} {source_id}')
        for clip in _clip_poses(species, document):
            name = Path(clip['file']).stem
            poses = clip['poses']
            token = _events_token(clip['file'], clip.get('events', []))
            lines.append(f'clip {species} {name} {clip["source_frames"]} '
                         f'{token} poses {len(poses)} converted')
    return ('\n'.join(lines) + '\n').encode('ascii')


def _mesh_bytes(source, species, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose['file']
    if not path.is_file():
        raise StagingError(f'{species} pose mesh missing for identity content: {path}')
    if path.is_symlink():
        raise StagingError(f'{species} pose mesh escapes the source tree: {path}')
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f'{species} pose mesh unreadable for identity content: {path}') from error
    if _sha(data) != pose['sha256']:
        raise StagingError(f'{species} pose hash mismatch for identity content: {path}')
    if not data:
        raise StagingError(f'{species} pose mesh empty for identity content: {path}')
    return data


def validate_species_dir(source, species=None, source_id=None):
    """Pre-flight check for one extracted ``<content>/<Enum>/`` proxy tree."""
    source = Path(source)
    if species is None or source_id is None:
        rows = _proxy_rows()
        candidate = source.name
        if candidate not in rows:
            raise StagingError(f'Proxy source is not a declared species dir: {source}')
        species = candidate
        source_id = rows[candidate][0]
    document, _raw = _load_manifest(species, source_id, source)
    clips = _clip_poses(species, document)
    for clip in clips:
        for pose in clip['poses']:
            _mesh_bytes(source, species, pose)
    return True


def plan(content_root, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(campaign_payload, actors_payload, bank_payload, mesh_files,
    digests)`` where ``mesh_files`` maps room-relative mesh names to bytes
    and ``digests`` maps species to manifest SHA-256.
    """
    content_root = Path(content_root)
    rows = _proxy_rows()
    actors = _normalize_actors(actors)
    present = sorted({species for _, species in actors},
                     key=lambda name: rows[name][0])
    if len(present) > _MAX_CAMPAIGN_SPECIES:
        raise StagingError(
            f'Proxy species exceed the native 64-species cap: {len(present)}')
    documents = {}
    digests = {}
    mesh_files = {}
    for species in present:
        source_id, _host = rows[species]
        source = content_root / species
        if not source.is_dir():
            raise StagingError(f'Proxy content source missing: {source}')
        document, raw = _load_manifest(species, source_id, source)
        documents[species] = (document, source_id)
        digests[species] = _sha(raw)
        for clip in _clip_poses(species, document):
            for pose in clip['poses']:
                data = _mesh_bytes(source, species, pose)
                if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                    raise StagingError(f'Proxy pose mesh name collision: {pose["file"]}')
                mesh_files[pose['file']] = data
    campaign_payload = _campaign_payload(present, rows)
    actors_payload = _actors_payload(actors)
    bank_payload = _bank_payload(documents)
    return campaign_payload, actors_payload, bank_payload, mesh_files, digests


def stage_proxy(content_root, run, actors):
    """Stage the proxy campaign/actors/bank sidecars plus pose meshes.

    ``content_root`` is the identity-keyed content root holding one
    ``<content_root>/<Enum>/`` tree per proxy species present; ``run`` is the
    run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` maps every proxy generator id to its enum name. All proxy
    species present are staged in one call (one shared actors/bank/campaign
    file, not one per species). Idempotent: a second call over the same run
    is a no-op success when every staged file is byte-identical; a
    conflicting staged file is refused with ``StagingError`` before any
    write.
    """
    content_root, run = Path(content_root), Path(run)
    actors = _normalize_actors(actors)
    if not run.is_dir():
        raise StagingError(f'Proxy run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Proxy room directory missing for run staging: {room}')
    campaign_payload, actors_payload, bank_payload, mesh_files, digests = plan(
        content_root, actors)
    targets = {CAMPAIGN_TXT: campaign_payload, ACTORS_TXT: actors_payload,
               BANK_TXT: bank_payload}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    blocked = sorted(name for name in targets
                     if (run / name).exists() and not (run / name).is_file())
    if blocked:
        raise StagingError(
            'Refusing proxy staging over non-file targets: ' + ', '.join(blocked))
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting proxy staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    receipt = dict(family='proxy', staged=staged,
                   manifest_sha256=dict(digests),
                   generators=[int(generator) for generator, _species in actors],
                   species=sorted({species for _, species in actors}),
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content-root', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--actor', action='append', required=True,
                        help='generator:species, e.g. 219079:Chappy')
    args = parser.parse_args()
    actors = [(int(value.split(':')[0]), value.split(':')[1]) for value in args.actor]
    print(json.dumps(stage_proxy(args.content_root, args.run, actors),
                     sort_keys=True, indent=2))
