"""Stage the snagret pair (SnakeCrow 34 / SnakeWhole 70) bank rows into a run.

The native snakejoint path opens ``p2-snagret-actors.txt`` plus
``p2-snagret-bank.txt`` (``engine/pc_port/pc_p2_snakejoint.cpp``
``pc_p2_snakejoint_setup``: ``P2_SNAGRET_BANK_1`` header, ``species`` rows,
``clip`` rows with the ``poses``/``status`` shape) and the sampled pose
meshes ``assets/dataDir/courses/pikmin2room/snake_<Species>_<clip>_%02d.mod``
(opened by ``engine/pc_port/pc_p2_batch3.cpp`` ``loadPose`` with the
``snake`` family prefix). The shared-contract installer
(:mod:`experimental.pikmin2_snagret_install`) stages actors + meshes but no
bank, so a 34/70-only binding draws without its own model; the extractor
(:mod:`experimental.pikmin2_snagret_assets`) produces the source art under
``<content>/<Enum>/`` (``snagret.json`` plus per-species pose meshes). This
module carries that art to where the native loader opens it, deriving the
actors/bank rows in the exact shape the native parsers accept. It never
extracts assets and never commits retail data.

Source layout (extracted ``<content>/SnakeCrow/`` tree; ``SnakeWhole/``
carries the same full import tree, see ``scripts/p2_prepare_content``
``extract_snagret``):

* ``snagret.json`` (schema 1, policy ``P2_SNAGRET_1``): per-species
  ``enemy_id``, ``clips`` (``name``, ``source_frames``, ``events``
  (``[[frame, kind], ...]``), ``status``, ``poses`` (``frame``, ``file``
  (``snake_<Species>_<clip>_%02d.mod``), ``bytes``, ``sha256``)).
* ``<Species>/snake_<Species>_<clip>_%02d.mod`` pose meshes, hash-bound.

Staged layout (run directory):

* ``p2-snagret-actors.txt`` / ``p2-snagret-bank.txt`` in the canonical
  shared shapes (merge helpers shared with
  :mod:`experimental.pikmin2_dangomushi_content`, canonical
  SnakeCrow/SnakeWhole/DangoMushi order), merged with other snagret-family
  staged rows when present.
* ``assets/dataDir/courses/pikmin2room/snake_<Species>_<clip>_%02d.mod``:
  byte copies of the sampled pose meshes, hash-bound to the manifest.

Idempotent like the other identity adapters: all payloads are computed and
validated before any mutation; a second call over the same run is a no-op
success when every staged file is byte-identical. A restaged own-species
block must equal what is already there, and a mesh file that exists with
different bytes is refused with ``StagingError`` before anything is written.
A missing or mismatched source file raises ``StagingError`` -- never
fabricates a pose or an event.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_dangomushi_content import (
    _check_events as _check_clip_events,
)
from experimental.pikmin2_dangomushi_content import (
    _check_events_token,
    _merge_actors,
    _merge_bank,
)
from experimental.pikmin2_staging import StagingError

SPECIES_IDS = {"SnakeCrow": 34, "SnakeWhole": 70}
MANIFEST = "snagret.json"
POLICY = "P2_SNAGRET_1"
ACTORS_TXT = "p2-snagret-actors.txt"
BANK_TXT = "p2-snagret-bank.txt"
ROOM = Path("assets/dataDir/courses/pikmin2room")

_CLIP_RE = re.compile(r"[a-z0-9_]+")
_HEX64_RE = re.compile(r"[0-9a-f]{64}")

# Native bank clip-row budget (pc_p2_batch3.cpp parseBank): poses in 0..64.
_MAX_BANK_POSES = 64
# Native actor-row budget (parseActors): 1..100 rows.
_MAX_ACTORS = 100

# Anchors: the native setup draws spawn on "appear1"
# (P2_SNAKEJOINT_DRAW clip=appear1) and the corpse on "dead"; a staged bank
# without these two cannot serve the pair.
REQUIRED_CLIPS = ("dead", "appear1")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _events_token(clip_name, events):
    """Encode one clip's events exactly as the behavior bank_text does."""
    if not events:
        return "-"
    return ",".join(f"{frame}:{kind}" for frame, kind in events)


def _pose_pattern(species):
    return re.compile(rf"snake_{species}_([a-z0-9_]+)_([0-9]{{2}})\.mod")


def _load_manifest(source):
    """Read and validate the extracted snagret manifest; fail closed."""
    source = Path(source)
    path = source / MANIFEST
    if not path.is_file():
        raise StagingError(f"Snagret manifest missing for identity content: {path}")
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as error:
        raise StagingError(f"Snagret manifest unreadable for identity content: {path}") from error
    if document.get("schema") != 1 or document.get("policy") != POLICY:
        raise StagingError(f"Snagret manifest schema/policy mismatch for identity content: {path}")
    species = document.get("species")
    if not isinstance(species, dict):
        raise StagingError(f"Snagret manifest carries no species for identity content: {path}")
    for name, want in SPECIES_IDS.items():
        info = species.get(name)
        if not isinstance(info, dict) or info.get("enemy_id") != want:
            raise StagingError(f"Snagret manifest identity mismatch for {name}: {path}")
    return document, raw


def _converted_poses(clip):
    """Yield ``(sample_index, pose)`` for poses the extractor converted.

    A sampled frame the extractor could not convert is recorded as
    ``{frame, unsupported_reason}`` with no ``file``; the bank counts
    converted poses only (mirroring the behavior ``bank_text``) and the
    mesh index is the full-sample position (the extractor numbers every
    sampled frame).
    """
    for position, pose in enumerate(clip.get("poses", [])):
        if not isinstance(pose, dict) or "file" not in pose:
            continue
        yield position, pose


def _clip_poses(species, info):
    """Return the validated converted clips for one species with their poses."""
    pattern = _pose_pattern(species)
    seen = set()
    converted = []
    for clip in info.get("clips", []):
        name = clip.get("name")
        if not isinstance(name, str) or not _CLIP_RE.fullmatch(name):
            raise StagingError(
                f"Snagret clip name rejected by the native bank grammar: {name!r}")
        if name in seen:
            raise StagingError(f"Snagret clip ambiguous for identity content: {name}")
        seen.add(name)
        if clip.get("status") != "converted":
            continue
        poses = clip.get("poses")
        if not isinstance(poses, list) or not poses:
            raise StagingError(f"Snagret clip carries no poses for identity content: {name}")
        converted_count = sum(1 for _pos, _pose in _converted_poses(clip))
        if not converted_count:
            raise StagingError(f"Snagret clip carries no poses for identity content: {name}")
        if converted_count > _MAX_BANK_POSES:
            raise StagingError(f"Snagret clip exceeds the native bank budget: {name}")
        previous = -1
        for position, pose in _converted_poses(clip):
            frame = pose.get("frame")
            if type(frame) is not int or frame <= previous or frame > 100000:
                raise StagingError(f"Snagret pose frames are not strictly increasing in {name}")
            previous = frame
            filename = pose.get("file")
            match = pattern.fullmatch(filename) if isinstance(filename, str) else None
            if match is None or match.group(1) != name or int(match.group(2)) != position:
                raise StagingError(
                    f"Snagret pose filename breaks the native loadPose sequence: {filename!r}")
            digest = pose.get("sha256")
            if not isinstance(digest, str) or not _HEX64_RE.fullmatch(digest):
                raise StagingError(
                    f"Snagret pose SHA-256 missing for identity content: {filename}")
        _check_clip_events(name, clip.get("source_frames"), clip.get("events", []))
        converted.append(clip)
    present = {clip["name"] for clip in converted}
    for required in REQUIRED_CLIPS:
        if required not in present:
            raise StagingError(
                f"Snagret anchor unavailable for identity content: {required}")
    return converted


def _mesh_bytes(source, species, pose):
    """Read one pose mesh and bind it to the manifest hash; fail closed."""
    path = Path(source) / species / pose["file"]
    if not path.is_file():
        raise StagingError(f"Snagret pose mesh missing for identity content: {path}")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise StagingError(f"Snagret pose mesh unreadable for identity content: {path}") from error
    if _sha(data) != pose["sha256"]:
        raise StagingError(f"Snagret pose hash mismatch for identity content: {path}")
    if not data:
        raise StagingError(f"Snagret pose mesh empty for identity content: {path}")
    return data


def validate_source(source):
    """Pre-flight check for the snagret content tree without writing anything."""
    source = Path(source)
    document, _raw = _load_manifest(source)
    for species in SPECIES_IDS:
        for clip in _clip_poses(species, document["species"][species]):
            for _position, pose in _converted_poses(clip):
                _mesh_bytes(source, species, pose)
    return True


def plan(source, actors):
    """Validate everything and return exact payloads; never writes.

    Returns ``(manifest_digest, per_species)`` where ``per_species`` maps each
    staged species to ``(generators, clip_rows, mesh_files)``. Merging with
    staged snagret-family rows happens in :func:`stage_snagret`.
    """
    source = Path(source)
    actors = list(actors)
    by_species: dict[str, list[int]] = {}
    for generator, species in actors:
        if species not in SPECIES_IDS:
            raise StagingError(f"Snagret adapter got non-snagret species: {species!r}")
        if type(generator) is not int or not 0 < generator <= 0xFFFFFFFF:
            raise StagingError(f"Snagret actor generator out of native range: {generator!r}")
        by_species.setdefault(species, []).append(generator)
    if not by_species:
        raise StagingError("Snagret install requires at least one generator")
    for species, generators in by_species.items():
        if len(set(generators)) != len(generators):
            raise StagingError("Snagret actor generators are not unique")
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    per_species = {}
    for species, generators in by_species.items():
        clips = _clip_poses(species, document["species"][species])
        clip_rows = []
        for clip in clips:
            token = _events_token(clip["name"], clip.get("events", []))
            converted_poses = sum(1 for _pos, _pose in _converted_poses(clip))
            clip_rows.append((clip["name"], clip["source_frames"], token,
                              converted_poses, "converted"))
        mesh_files = {}
        for clip in clips:
            for _position, pose in _converted_poses(clip):
                data = _mesh_bytes(source, species, pose)
                if pose["file"] in mesh_files and mesh_files[pose["file"]] != data:
                    raise StagingError(f"Snagret pose mesh name collision: {pose['file']}")
                mesh_files[pose["file"]] = data
        per_species[species] = (generators, clip_rows, mesh_files)
    return digest, per_species


def stage_snagret(source, run, actors):
    """Stage the snagret-pair files from an extracted snagret tree.

    ``source`` is the extracted ``<content>/SnakeCrow/`` (or ``SnakeWhole/``)
    directory (``snagret.json`` plus per-species pose meshes); ``run`` is the
    run directory whose text-bank slots and
    ``assets/dataDir/courses/pikmin2room/`` room receive the staged files;
    ``actors`` is the seed's ``[(generator_id, species), ...]`` bindings.
    Rows merge with other snagret-family staged rows (DangoMushi first or
    second: both orders succeed and stage the same row sets; bank bytes are
    canonical while actor rows keep insertion order like the ground-family
    mergers); idempotent across repeat calls, fail-closed on any conflict,
    all validated before any write.
    """
    source, run = Path(source), Path(run)
    actors = list(actors)
    if not run.is_dir():
        raise StagingError(f"Snagret run directory missing: {run}")
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f"Snagret room directory missing for run staging: {room}")
    digest, per_species = plan(source, actors)
    actors_path, bank_path = run / ACTORS_TXT, run / BANK_TXT
    merged_actors = (actors_path.read_bytes() if actors_path.is_file() else None)
    merged_bank = (bank_path.read_bytes() if bank_path.is_file() else None)
    for species in sorted(per_species, key=lambda s: list(SPECIES_IDS).index(s)):
        generators, clip_rows, _mesh = per_species[species]
        merged_actors = _merge_actors(merged_actors, species, generators)
        merged_bank = _merge_bank(merged_bank, species, SPECIES_IDS[species], clip_rows)
    targets = {ACTORS_TXT: merged_actors, BANK_TXT: merged_bank}
    mesh_files: dict[str, bytes] = {}
    for _species, (_generators, _clips, meshes) in per_species.items():
        for name, payload in meshes.items():
            if name in mesh_files and mesh_files[name] != payload:
                raise StagingError(f"Snagret pose mesh name collision: {name}")
            mesh_files[name] = payload
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    mesh_conflicts = sorted(
        name for name, payload in mesh_files.items()
        if (run / str(ROOM / name)).is_file()
        and (run / str(ROOM / name)).read_bytes() != payload)
    if mesh_conflicts:
        raise StagingError(
            "Refusing conflicting Snagret staging: " + ", ".join(mesh_conflicts))
    if all((run / name).is_file() and (run / name).read_bytes() == payload
           for name, payload in targets.items()):
        staged = "existing_identical"
    else:
        for name, payload in targets.items():
            if not (run / name).is_file() or (run / name).read_bytes() != payload:
                (run / name).write_bytes(payload)
        staged = "written"
    receipt = dict(species=sorted(per_species), staged=staged,
                   manifest_sha256=digest,
                   generators=[int(generator) for generator, _species in actors],
                   files={name: _sha(payload) for name, payload in targets.items()})
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--actor", action="append", required=True,
                        help="generator:species, e.g. 219094:SnakeCrow")
    args = parser.parse_args()
    actors = [(int(value.split(":")[0]), value.split(":")[1]) for value in args.actor]
    print(json.dumps(stage_snagret(args.source, args.run, actors),
                     sort_keys=True, indent=2))
