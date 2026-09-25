"""Stage the own-identity Chappy-family sidecars and pose files into a run.

The native ``chappy`` family (``pc_p2_chappy``) reads three staged files
from the session run directory plus the sampled pose meshes:

* ``p2-chappy-actors.txt``: ``P2_CHAPPY_ACTORS_1 <count>`` then one
  ``<generator_id> <Species>`` row per seed actor.
* ``p2-chappy-bank.txt``: ``P2_CHAPPY_BANK_1`` then one
  ``species <Species> <source_id>`` row plus one
  ``clip <Species> <name> <source_frames> <events|-> poses <n> converted``
  row per converted clip (the batch-2 bank grammar the native parser
  accepts).
* ``assets/dataDir/courses/pikmin2room/ch_<Species>_<clip>_%02d.mod``:
  byte copies of the sampled pose meshes (renamed from the extracted
  ``px_<Species>_<clip>_%02d.mod`` names so the identity family owns its
  room files), hash-bound to each species' manifest.

The extractor (:mod:`experimental.pikmin2_chappy_assets`) produces the
source art under ``<content>/<Enum>/`` (``proxy.json`` plus the
``px_*.mod`` pose meshes, byte-identical to the retired proxy
extraction); this module carries that art to where the native loader
opens it. It never extracts assets and never commits retail data.

Idempotent like the Sokkuri stager: all payloads are computed and
validated before any mutation; a second call over the same run is a no-op
success when every staged file is byte-identical, and any conflicting
staged file is refused with ``StagingError`` before anything is written.
A missing or mismatched source file raises ``StagingError`` -- never
fabricates a pose or an event.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_chappy_assets import CHAPPY_ROWS
from experimental.pikmin2_staging import StagingError

MANIFEST = "proxy.json"
ACTORS_TXT = "p2-chappy-actors.txt"
BANK_TXT = "p2-chappy-bank.txt"
ACTORS_HEADER = "P2_CHAPPY_ACTORS_1"
BANK_HEADER = "P2_CHAPPY_BANK_1"
ROOM = Path("assets/dataDir/courses/pikmin2room")

_ENUM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,31}")
_CLIP_RE = re.compile(r"[A-Za-z0-9_]+\.bca")
_HEX64_RE = re.compile(r"[0-9a-f]{64}")

# Native bank clip-row budget mirrors pc_p2_batch2.cpp: poses in 0..64.
_MAX_BANK_POSES = 64

# Native sidecar cap mirrors pc_p2_batch2.cpp parseActors: count 1..100.
_MAX_ACTORS_ROWS = 100

# The native chappy draw picks the clip from host state and falls back
# across these groups, so a staged species without a wait or a dead clip
# cannot serve the family.
WAIT_CLIPS = ("wait1", "wait", "wait2")
DEAD_CLIPS = ("dead", "dead1", "pdead1")

SPECIES_FOR_ID = {source_id: row["enum_name"] for source_id, row in CHAPPY_ROWS.items()}
ID_FOR_SPECIES = {row["enum_name"]: source_id for source_id, row in CHAPPY_ROWS.items()}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _room_name(species, clip_stem, index):
    """Native room filename for one staged pose (chappy ``loadPose`` grammar)."""
    return f"ch_{species}_{clip_stem}_{index:02}.mod"


def _normalize_actors(actors):
    """Accept [(generator, enum), ...] pairs for Chappy-family species."""
    pairs = list(actors.items()) if isinstance(actors, dict) else list(actors)
    normalized = []
    for entry in pairs:
        try:
            generator, species = entry
        except (TypeError, ValueError):
            raise StagingError(f"Chappy actor entry malformed: {entry!r}") from None
        if type(generator) is not int or isinstance(generator, bool) \
                or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f"Chappy actor generator out of native range: {generator!r}")
        if not isinstance(species, str) or not _ENUM_RE.fullmatch(species):
            raise StagingError(f"Chappy actor species invalid: {species!r}")
        if species not in ID_FOR_SPECIES:
            raise StagingError(f"Chappy actor species not a Chappy-family species: {species!r}")
        normalized.append((generator, species))
    if not normalized:
        raise StagingError("Chappy install requires at least one actor")
    if len({generator for generator, _ in normalized}) != len(normalized):
        raise StagingError("Chappy actor generators are not unique")
    if len(normalized) > _MAX_ACTORS_ROWS:
        raise StagingError(
            f"Chappy actor rows exceed the native 100-row cap: {len(normalized)}")
    return normalized


def _events_token(clip_name, events):
    """Encode one clip's events exactly as bank_text does (``-`` when empty)."""
    if not events:
        return "-"
    return ",".join(f"{frame}:{kind}" for frame, kind in events)


def _check_events(species, clip_name, duration, events):
    """Mirror the native bank/event grammar so every staged row always parses.

    Same contract as ``pikmin2_proxy_content._check_events``: frames are
    non-negative 100000-bounded digits in non-decreasing order, kinds are
    0..999, at most 4096 events per clip, durations 1..10000. No duration
    relation is enforced (the native side accepts events at any frame).
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise StagingError(f"{species} clip duration out of native range: {clip_name}")
    if not isinstance(events, list) or len(events) > 4096:
        raise StagingError(f"{species} clip event budget exceeded: {clip_name}")
    previous = -1
    for entry in events:
        if (not isinstance(entry, list) or len(entry) != 2
                or type(entry[0]) is not int or type(entry[1]) is not int):
            raise StagingError(f"{species} clip event malformed: {clip_name}")
        frame, kind = entry
        if frame < previous or frame < 0 or frame > 100000:
            raise StagingError(f"{species} clip event outside the native clip: {clip_name}")
        if not 0 <= kind < 1000:
            raise StagingError(f"{species} clip event kind outside the native range: {clip_name}")
        previous = frame


def _load_manifest(species, source_id, source):
    """Read and validate one extracted Chappy-family manifest; fail closed."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f"Chappy manifest missing for identity content: {path}")
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as error:
        raise StagingError(f"Chappy manifest unreadable for identity content: {path}") from error
    if document.get("schema") != 1:
        raise StagingError(f"Chappy manifest schema mismatch for identity content: {path}")
    if document.get("species") != species or document.get("enemy_id") != source_id:
        raise StagingError(f"Chappy manifest identity mismatch for identity content: {path}")
    clips = document.get("clips")
    if not isinstance(clips, list) or not clips:
        raise StagingError(f"Chappy manifest carries no clips for identity content: {path}")
    return document, raw


def _clip_poses(species, document):
    """Return the validated converted clips in manifest order with poses."""
    seen = set()
    converted = []
    for clip in document.get("clips", []):
        name = clip.get("file")
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(
                f"{species} clip name rejected by the native bank grammar: {name!r}")
        if name in seen:
            raise StagingError(f"{species} clip ambiguous for identity content: {name}")
        seen.add(name)
        if clip.get("status") != "converted":
            continue
        poses = clip.get("poses")
        if not isinstance(poses, list) or not poses:
            raise StagingError(
                f"{species} clip carries no poses for identity content: {name}")
        if len(poses) > _MAX_BANK_POSES:
            raise StagingError(f"{species} clip exceeds the native bank budget: {name}")
        stem = name[:-4]
        previous = -1
        for index, pose in enumerate(poses):
            frame = pose.get("frame")
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(
                    f"{species} pose frames are not strictly increasing in {name}")
            previous = frame
            filename = pose.get("file")
            # The extractor names poses px_<species>_<clip>_%02d.mod in exact
            # sequence; the stager renames them to the ch_ room grammar.
            if filename != f"px_{species}_{stem}_{index:02}.mod":
                raise StagingError(
                    f"{species} pose filename breaks the expected sequence: {filename!r}")
            digest = pose.get("sha256")
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(
                    f"{species} pose SHA-256 missing for identity content: {filename}")
        _check_events(species, name, clip.get("source_frames"), clip.get("events", []))
        converted.append(clip)
    if not converted:
        raise StagingError(f"{species} manifest carries no converted clips")
    present = {Path(clip["file"]).stem for clip in converted}
    if not present & set(WAIT_CLIPS):
        raise StagingError(f"{species} chappy anchor unavailable for identity content: wait")
    if not present & set(DEAD_CLIPS):
        raise StagingError(f"{species} chappy anchor unavailable for identity content: dead")
    return converted


def _actors_payload(actors):
    """Render P2_CHAPPY_ACTORS_1 from the Chappy-family generator bindings."""
    lines = [ACTORS_HEADER, str(len(actors))]
    lines.extend(f"{generator} {species}"
                 for generator, species in sorted(actors, key=lambda pair: pair[0]))
    return ("\n".join(lines) + "\n").encode("ascii")


def _bank_payload(documents):
    """Render P2_CHAPPY_BANK_1 with species rows plus clip rows per species."""
    lines = [BANK_HEADER]
    for species in sorted(documents, key=lambda name: ID_FOR_SPECIES[name]):
        document, source_id = documents[species]
        lines.append(f"species {species} {source_id}")
        for clip in _clip_poses(species, document):
            name = Path(clip["file"]).stem
            poses = clip["poses"]
            token = _events_token(clip["file"], clip.get("events", []))
            lines.append(f"clip {species} {name} {clip['source_frames']} "
                         f"{token} poses {len(poses)} converted")
    return ("\n".join(lines) + "\n").encode("ascii")


def _mesh_bytes(source, species, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / pose["file"]
    if not path.is_file():
        raise StagingError(f"{species} pose mesh missing for identity content: {path}")
    if path.is_symlink():
        raise StagingError(f"{species} pose mesh escapes the source tree: {path}")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f"{species} pose mesh unreadable for identity content: {path}") from error
    if _sha(data) != pose["sha256"]:
        raise StagingError(f"{species} pose hash mismatch for identity content: {path}")
    if not data:
        raise StagingError(f"{species} pose mesh empty for identity content: {path}")
    return data


def validate_source(source, species=None, source_id=None):
    """Pre-flight check for one extracted ``<content>/<Enum>/`` Chappy tree."""
    source = Path(source)
    if species is None or source_id is None:
        candidate = source.name
        if candidate not in ID_FOR_SPECIES:
            raise StagingError(f"Chappy source is not a Chappy-family species dir: {source}")
        species = candidate
        source_id = ID_FOR_SPECIES[candidate]
    document, _raw = _load_manifest(species, source_id, source)
    clips = _clip_poses(species, document)
    for clip in clips:
        for pose in clip["poses"]:
            _mesh_bytes(source, species, pose)
    return True


def plan(content_root, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(actors_payload, bank_payload, mesh_files, digests)`` where
    ``mesh_files`` maps room-relative ``ch_*.mod`` names to bytes and
    ``digests`` maps species to manifest SHA-256.
    """
    content_root = Path(content_root)
    actors = _normalize_actors(actors)
    present = sorted({species for _, species in actors},
                     key=lambda name: ID_FOR_SPECIES[name])
    documents = {}
    digests = {}
    mesh_files = {}
    for species in present:
        source_id = ID_FOR_SPECIES[species]
        source = content_root / species
        if not source.is_dir():
            raise StagingError(f"Chappy content source missing: {source}")
        document, raw = _load_manifest(species, source_id, source)
        documents[species] = (document, source_id)
        digests[species] = _sha(raw)
        for clip in _clip_poses(species, document):
            stem = Path(clip["file"]).stem
            for index, pose in enumerate(clip["poses"]):
                data = _mesh_bytes(source, species, pose)
                room_name = _room_name(species, stem, index)
                if room_name in mesh_files and mesh_files[room_name] != data:
                    raise StagingError(f"Chappy pose mesh name collision: {room_name}")
                mesh_files[room_name] = data
    actors_payload = _actors_payload(actors)
    bank_payload = _bank_payload(documents)
    return actors_payload, bank_payload, mesh_files, digests


def stage_chappy(content_root, run, actors):
    """Stage the Chappy-family actors/bank sidecars plus pose meshes.

    ``content_root`` is the identity-keyed content root holding one
    ``<content_root>/<Enum>/`` tree per Chappy-family species present;
    ``run`` is the run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` maps every Chappy-family generator id to its enum name.
    Idempotent: a second call over the same run is a no-op success when
    every staged file is byte-identical; a conflicting staged file is
    refused with ``StagingError`` before any write.
    """
    content_root, run = Path(content_root), Path(run)
    actors = _normalize_actors(actors)
    if not run.is_dir():
        raise StagingError(f"Chappy run directory missing: {run}")
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f"Chappy room directory missing for run staging: {room}")
    actors_payload, bank_payload, mesh_files, digests = plan(content_root, actors)
    targets = {ACTORS_TXT: actors_payload, BANK_TXT: bank_payload}
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    blocked = sorted(name for name in targets
                     if (run / name).exists() and not (run / name).is_file())
    if blocked:
        raise StagingError(
            "Refusing Chappy staging over non-file targets: " + ", ".join(blocked))
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError("Refusing conflicting Chappy staging: " + ", ".join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = "existing_identical"
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = "written"
    receipt = dict(family="chappy", staged=staged,
                   manifest_sha256=dict(digests),
                   generators=[int(generator) for generator, _species in actors],
                   species=sorted({species for _, species in actors}),
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--content-root", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--actor", action="append", required=True,
                        help="generator:species, e.g. 219079:Chappy")
    args = parser.parse_args()
    actors = [(int(value.split(":")[0]), value.split(":")[1]) for value in args.actor]
    print(json.dumps(stage_chappy(args.content_root, args.run, actors),
                     sort_keys=True, indent=2))
