"""Damagumo bind-mod conversion driver (issue #727).

Produces ``longlegs_Damagumo_bind_00.mod`` from the pinned staged artifacts
(#670 family json, #678 Demon/enemy.bmd, #685 slot json) using the shared
conversion pipeline consumed read-only from the pinned long-legs visual
module tree. No source/shared/native edits, no runtime, no ADMIT.

Policy (recorded, fail-closed): the family MAT3 multi-stage policy
(``approximate_materials=True``, documented in the visual module for Houdai)
plus explicit bind matrices computed by the shared ``joint_matrices`` (the
BigFoot explicit-matrices precedent) with ``bake_rigid=True``. Damagumo has
zero EVP1 envelopes (rigid) but carries a direct matrix reference the strict
decoder only accepts via the explicit-matrices path; the matrices are the
model''s own bind pose, so geometry is unchanged versus default decoding.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

FAMILY_JSON_SHA256 = "f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94"
ENEMY_BMD_SHA256 = "8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961"
SLOT_JSON_SHA256 = "61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c"
VISUAL_MODULE_SHA256 = "0a8329cedb35c6b8e24d74de3dec1988b0c616be38d918a1781ce6e0318a1117"
CONVERT_SHA256 = "6297e1bdffd2ff9df64d5f3f0662f22dbfebbd16c2e06c0d541c757dd3df1a63"
RIGID_SHA256 = "b5533f513465fc07fd3f8c75d6376b072b9be2ae0bb950658fbcdf3314c3361d"
SKINNING_SHA256 = "5203f0dae3e880ddf7c3675bb41197609731f94efe391c38b70bb432fcc1f58c"

SPECIES = "Damagumo"
ENEMY_ID = 56
MOD = "longlegs_Damagumo_bind_00.mod"
MESH = "Damagumo_enemy.bmd"
RECEIPT = "damagumo-bind-receipt.json"
SCHEMA = 1
MAX_MOD_BYTES = 4 * 1024 * 1024


class ConversionError(ValueError):
    """Fail-closed conversion refusal."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    path = Path(path)
    if not path.is_file():
        raise ConversionError("Missing file: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_hash(path, want, what):
    got = sha256_file(path)
    if got != want:
        raise ConversionError("%s hash drift: %s != %s" % (what, got, want))
    return got


def check_json_hash(path, want, what):
    # The #685 packet pins LF-normalized content hashes while the staged
    # files are CRLF on disk; normalize exactly like the packet did.
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    got = sha256_bytes(data)
    if got != want:
        raise ConversionError("%s hash drift: %s != %s" % (what, got, want))
    return got


def load_pipeline(visual_tree):
    """Import the shared conversion pipeline read-only from the pinned tree."""
    visual_tree = Path(visual_tree)
    for rel, want in (
            ("experimental/pikmin2_long_legs_visual.py", VISUAL_MODULE_SHA256),
            ("experimental/pikmin2_convert.py", CONVERT_SHA256),
            ("experimental/pikmin2_rigid.py", RIGID_SHA256),
            ("experimental/pikmin2_skinning.py", SKINNING_SHA256)):
        check_hash(visual_tree / rel, want, rel)
    sys.path.insert(0, str(visual_tree))
    import experimental.pikmin2_convert as convert_mod
    import experimental.pikmin2_rigid as rigid_mod
    return convert_mod, rigid_mod


def convert_damagumo(family_json, enemy_bmd, slot_json, visual_tree, out_dir):
    """Run the Damagumo conversion; return the receipt dict."""
    family_json, enemy_bmd, slot_json = Path(family_json), Path(enemy_bmd), Path(slot_json)
    out_dir = Path(out_dir)
    check_json_hash(family_json, FAMILY_JSON_SHA256, "family json")
    check_hash(enemy_bmd, ENEMY_BMD_SHA256, "enemy.bmd")
    slot = json.loads(slot_json.read_text(encoding="utf-8"))
    if slot.get("species") != SPECIES or slot.get("source_id") != ENEMY_ID:
        raise ConversionError("Slot json is not the Damagumo slot: %r" % slot)
    if slot.get("mesh") != "Demon/enemy.bmd":
        raise ConversionError("Slot mesh drift: %r" % slot.get("mesh"))
    convert_mod, rigid_mod = load_pipeline(visual_tree)
    model = enemy_bmd.read_bytes()
    if len(model) < 32 or model[:8] != b"J3D2bmd3":
        raise ConversionError("Expected complete J3D2bmd3 model")
    matrices = rigid_mod.joint_matrices(convert_mod.blocks(model), None)
    decoded = convert_mod.decode(model, True, bake_rigid=True, draw_matrices=matrices)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "bind.mod"
        report = convert_mod.write_model(decoded, target, "enemy.bmd")
        data = target.read_bytes()
    if not data or len(data) > MAX_MOD_BYTES:
        raise ConversionError("Converted bind mesh out of budget: %d bytes" % len(data))
    if int(report.get("vertices", 0)) <= 0 or int(report.get("triangles", 0)) <= 0:
        raise ConversionError("Degenerate converted geometry: %r" % report)
    out_dir.mkdir(parents=True, exist_ok=True)
    target_path = out_dir / MOD
    if target_path.exists() or target_path.is_symlink():
        raise ConversionError("Refusing existing bind mod: " + str(target_path))
    target_path.write_bytes(data)
    receipt = dict(
        schema=SCHEMA, family="Long Legs", species=SPECIES, enemy_id=ENEMY_ID,
        visual="bind_pose_static", model="bind", output=MOD,
        source_mesh=str(enemy_bmd), source_bytes=len(model),
        source_sha256=sha256_bytes(model), bytes=len(data),
        sha256=sha256_bytes(data), vertices=report.get("vertices"),
        triangles=report.get("triangles"), shapes=report.get("shapes"),
        textures=report.get("textures"), slot=slot.get("slot"),
        policy=dict(approximate_materials=True, bake_rigid=True,
                    bind_matrices="joint_matrices(model, None)",
                    matrix_count=len(matrices)))
    (out_dir / RECEIPT).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                                   encoding="utf-8")
    print("P2_DAMAGUMO_BIND_CONVERT bytes=%d sha256=%s vertices=%s triangles=%s" % (
        len(data), receipt["sha256"], receipt["vertices"], receipt["triangles"]))
    print("P2_DAMAGUMO_BIND_DONE species=%s enemy_id=%d" % (SPECIES, ENEMY_ID))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-json", type=Path, required=True)
    parser.add_argument("--enemy-bmd", type=Path, required=True)
    parser.add_argument("--slot-json", type=Path, required=True)
    parser.add_argument("--visual-tree", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = convert_damagumo(args.family_json, args.enemy_bmd, args.slot_json,
                               args.visual_tree, args.out)
    print("P2_DAMAGUMO_BIND_RECEIPT %s" % receipt["sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
