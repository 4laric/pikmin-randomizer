"""Demon profile/mesh converter for arena slot 312004 (#670).

Consumes the verified Demon model/anim bytes and the mapped Damagumo folder
(P2 disc, ``enemy/data/Damagumo/{model,anim}.szs``), derives the exact-single-row
``damagumo-family.json`` profile plus the ``Demon/enemy.bmd`` mesh and the
arena slot-312004 descriptor consumable by the #638 arena staging provider.
Deterministic stdlib-only outputs, hash-pinned; malformed/missing inputs fail
closed. No family/shared edits, no runtime, no ADMIT. All six gates UNTESTED.

Derivation (all from real bytes; nothing invented):
* mesh bytes = Yaz0-decoded ``enemy.bmd`` from ``model.szs`` (RARC, single
  member); ``model_sha256`` is its SHA-256.
* joints = BMD JNT1 names via ``pikmin2_sheargrub_assets.joints``;
  ``joint_count`` is their count; textures = TEX1 u16@8.
* special joints use the lane-contract role template (mouth rkamujnt/lkamujnt,
  stickable tama/teama, leg_tube lft1/lht1/rft1/rht1); presence is exact-name
  match against the decoded joints. Damagumo BMD carries none of those names,
  so all report present:false with null index/matrix - the same convention as
  the committed Houdai profile (visual/profile slice; matrices unmeasured).
* animation rows: clip durations parsed from the BCA ANF1 frame-count field
  (J3D1bca1, u16 at ANF1+10, validated 1..10000 and consistent with file
  sizes); frames via the shared deterministic sampler ``frames_for(duration,
  [])`` (no source audit exists for Damagumo events, so only the {0,dur-1} +
  {10,16,17,30<dur} anchors; documented).
* retail/bestiary/folder/enemy_id/name from the committed lane-contract
  ``SPECIES[56]`` row (Damagumo, Beady Long Legs, bestiary 72, folder Demon).
* slot 312004 descriptor binds the arena actor slot to this profile+mesh.

The consumer (#638 ``_damagumo_profile``) requires animation anchors
landing/wait/flick non-empty; the Damagumo ``anim.szs`` ships exactly
dead/flick/landing/wait, so all three resolve from source.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, decompress, disc_files
from experimental.pikmin2_convert import blocks, u16
from experimental.pikmin2_sheargrub_assets import joints

SOURCE_MODEL = "enemy/data/Demon/model.szs"
SOURCE_ANIM = "enemy/data/Demon/anim.szs"
DAMAGUMO_MODEL = "enemy/data/Damagumo/model.szs"
DAMAGUMO_ANIM = "enemy/data/Damagumo/anim.szs"
MODEL_MEMBER = "enemy.bmd"
SLOT_ID = 312004
ENEMY_ID = 56
NAME = "Damagumo"
RETAIL = "Beady Long Legs"
BESTIARY = 72
FOLDER = "Demon"
REQUIRED_CLIPS = ("landing", "wait", "flick")
PROFILE_NAME = "damagumo-family.json"
MESH_NAME = "enemy.bmd"
SLOT_NAME = "damagumo-slot-312004.json"

SPECIAL_JOINT_ROLES = (
    ("mouth", ("rkamujnt", "lkamujnt")),
    ("stickable", ("tama", "teama")),
    ("leg_tube", ("lft1", "lht1", "rft1", "rht1")),
)


class ConvertError(ValueError):
    """Malformed or missing converter input."""


def sha(data):
    return hashlib.sha256(bytes(data)).hexdigest()


def read_member(payload, member):
    """Decode one SZS payload and extract a single RARC member."""
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < 16:
        raise ConvertError("truncated szs payload")
    if bytes(payload[:4]) != b"Yaz0":
        raise ConvertError("expected Yaz0 szs payload")
    try:
        decoded = decompress(bytes(payload))
    except Exception as exc:
        raise ConvertError("szs decode failed: %s" % exc)
    try:
        files = archive_files(decoded)
    except Exception as exc:
        raise ConvertError("rarc member parse failed: %s" % exc)
    if member not in files:
        raise ConvertError("missing archive member: %s" % member)
    return bytes(files[member])


def bca_duration(data, clip):
    """Parse the BCA ANF1 frame-count field (u16 at ANF1+10)."""
    if not isinstance(data, (bytes, bytearray)) or len(data) < 64:
        raise ConvertError("truncated bca clip: %s" % clip)
    data = bytes(data)
    if data[:8] != b"J3D1bca1":
        raise ConvertError("expected J3D1bca1 clip: %s" % clip)
    if data[32:36] != b"ANF1":
        raise ConvertError("missing ANF1 block: %s" % clip)
    duration = struct.unpack(">H", data[42:44])[0]
    if not 1 <= duration <= 10000:
        raise ConvertError("implausible bca duration for %s: %d" % (clip, duration))
    return duration


def frames_for(duration, events=()):
    """Deterministic pose sampler: clip-end anchors plus fixed anchors.

    Mirrors the family deterministic sampler with no audit events: {0, dur-1}
    plus {10, 16, 17, 30} below duration, sorted, capped at 32. Documented as
    duration-derived, not sampled retail events.
    """
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise ConvertError("invalid clip duration")
    frames = {0, duration - 1}
    for frame, event in events:
        if type(frame) is not int or not 0 <= frame <= duration or type(event) is not int:
            raise ConvertError("invalid event frame")
        frames.add(min(frame, duration - 1))
    frames.update(f for f in (10, 16, 17, 30) if f < duration)
    if len(frames) > 32:
        raise ConvertError("pose budget exceeded")
    return sorted(frames)


def mesh_profile(model_bytes):
    """Derive joint/texture evidence from decoded BMD bytes."""
    if len(model_bytes) < 32 or model_bytes[:8] != b"J3D2bmd3":
        raise ConvertError("expected complete J3D2bmd3 model")
    try:
        names = joints(model_bytes)
    except Exception as exc:
        raise ConvertError("joint table parse failed: %s" % exc)
    if not 1 <= len(names) <= 128:
        raise ConvertError("skeleton joint budget exceeded")
    if len(set(names)) != len(names):
        raise ConvertError("ambiguous joint identity")
    try:
        table = blocks(model_bytes)
    except Exception as exc:
        raise ConvertError("bmd block parse failed: %s" % exc)
    texture_count = None
    if "TEX1" in table:
        texture_count = u16(table["TEX1"], 8)
    report = []
    for role, members in SPECIAL_JOINT_ROLES:
        for name in members:
            if name in names:
                report.append(dict(name=name, role=role, present=True,
                                   index=names.index(name), matrix=None))
            else:
                report.append(dict(name=name, role=role, present=False,
                                   index=None, matrix=None))
    return dict(joints=names, joint_count=len(names),
                special_joints=report,
                embedded_texture_count=texture_count)


def convert_profile(model_szs, anim_szs):
    """Convert verified Demon/Damagumo szs bytes to the profile row + mesh."""
    model_bytes = read_member(model_szs, MODEL_MEMBER)
    anim_raw = anim_szs
    if not isinstance(anim_raw, (bytes, bytearray)) or len(anim_raw) < 16:
        raise ConvertError("truncated anim szs payload")
    if bytes(anim_raw[:4]) != b"Yaz0":
        raise ConvertError("expected Yaz0 anim szs payload")
    try:
        anim_decoded = decompress(bytes(anim_raw))
        anim_files = archive_files(anim_decoded)
    except Exception as exc:
        raise ConvertError("anim archive parse failed: %s" % exc)
    clips = {}
    for clip in REQUIRED_CLIPS:
        member = "%s.bca" % clip
        if member not in anim_files:
            raise ConvertError("required source clip unavailable: %s" % clip)
        duration = bca_duration(bytes(anim_files[member]), clip)
        clips[clip] = frames_for(duration)
    profile = mesh_profile(model_bytes)
    row = {
        "schema": 1,
        "family": "Long Legs",
        "enemy_id": ENEMY_ID,
        "name": NAME,
        "retail": RETAIL,
        "bestiary": BESTIARY,
        "folder": FOLDER,
        "mouth_joints": ["rkamujnt", "lkamujnt"],
        "mouth_radius": 40,
        "stickable_joints": ["tama", "teama"],
        "leg_tubes": ["lft1", "lht1", "rft1", "rht1"],
        "press_radius": 15,
        "animation_rows": clips,
        "owned_by": "codex/p2-demon-assets",
        "model_sha256": sha(model_bytes),
        "joints": profile["joints"],
        "joint_count": profile["joint_count"],
        "special_joints": profile["special_joints"],
        "embedded_texture_count": profile["embedded_texture_count"],
    }
    manifest = {"schema": 1, "family": "Long Legs",
                "lane": "damagumo-profile-convert",
                "profiles": {"56": row}}
    slot = {"schema": 1, "slot": SLOT_ID, "species": NAME, "source_id": ENEMY_ID,
            "profile": PROFILE_NAME, "mesh": "%s/%s" % (FOLDER, MESH_NAME),
            "model_sha256": sha(model_bytes),
            "arena_binding": "%d %s" % (SLOT_ID, NAME)}
    return manifest, model_bytes, slot


def convert_paths(model_path, anim_path, output):
    """Convert on-disk szs files into the output dir; return hashes."""
    output = Path(output)
    model_szs = Path(model_path).read_bytes()
    anim_szs = Path(anim_path).read_bytes()
    manifest, mesh, slot = convert_profile(model_szs, anim_szs)
    folder = output / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    (output / PROFILE_NAME).write_text(json.dumps(manifest, indent=1, sort_keys=True),
                                       encoding="utf-8")
    (folder / MESH_NAME).write_bytes(mesh)
    (output / SLOT_NAME).write_text(json.dumps(slot, indent=1, sort_keys=True),
                                    encoding="utf-8")
    return {str(Path(PROFILE_NAME)): sha(json.dumps(manifest, indent=1, sort_keys=True).encode()),
            str(Path(FOLDER) / MESH_NAME): sha(mesh),
            str(Path(SLOT_NAME)): sha(json.dumps(slot, indent=1, sort_keys=True).encode())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="model.szs path")
    parser.add_argument("--anim", required=True, help="anim.szs path")
    parser.add_argument("--output", required=True, help="output dir (created)")
    args = parser.parse_args(argv)
    hashes = convert_paths(args.model, args.anim, args.output)
    print(json.dumps(hashes, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())