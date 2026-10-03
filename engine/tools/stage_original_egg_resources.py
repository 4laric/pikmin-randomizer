"""Stage hash-validated private retail Egg geometry and parameters.

Legal bytes remain private. Model materials are the conversion's approximation;
source Egg JPA/audio may be explicitly deferred. Staging proves no gameplay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(source, name, expected, size=None):
    path = (source / name).resolve()
    if path.parent != source or not path.is_file():
        raise ValueError("Egg resource is missing or escapes source directory")
    if sha(path) != expected or (size is not None and path.stat().st_size != size):
        raise ValueError(f"Egg resource bytes differ from receipt: {name}")
    return path


def stage(source: Path, destination: Path):
    source, destination = source.resolve(), destination.resolve()
    if source == destination or source in destination.parents:
        raise ValueError("Egg destination must be separate from original source assets")
    receipt_path = source / "assets.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    joints_path = source / "joint-matrices.json"
    joints = json.loads(joints_path.read_text(encoding="utf-8"))
    if receipt["source_id"] != 37 or receipt["species"] != "Egg" or receipt["joints"] != ["root", "egg"]:
        raise ValueError("literal Egg source/rig mismatch")
    if joints["source_manifest_sha256"] != sha(receipt_path) or joints["model_sha256"] != receipt["model_sha256"]:
        raise ValueError("Egg joint bank does not bind source receipt/model")
    checked(source, "enemy.bmd", receipt["model_sha256"])
    for name, digest in receipt["metadata_sha256"].items():
        checked(source, name, digest)
    if len(receipt["clips"]) != 1:
        raise ValueError("Egg source has exactly one authored clip")
    clip = receipt["clips"][0]
    if clip["file"] != "damage1.bca" or clip["duration"] != 30 or clip["events"] != []:
        raise ValueError("Egg authored animation/event table changed")
    checked(source, clip["file"], clip["source_sha256"])
    poses = clip["poses"]
    if [pose["frame"] for pose in poses] != [0, 6, 12, 17, 23, 29]:
        raise ValueError("Egg authored pose frames changed")
    samples = {(sample["clip"], sample["source_frame"]): sample for sample in joints["poses"]}
    if len(samples) != 6 or len(joints["poses"]) != 6:
        raise ValueError("Egg joint sample set is incomplete or duplicated")
    output = ["P2_ORIGINAL_EGG_BANK_1", "clip damage1 6 30 original_egg_damage1", "frames 0 6 12 17 23 29"]
    copies = []
    for index, pose in enumerate(poses):
        copies.append((checked(source, pose["file"], pose["sha256"], pose["bytes"]), f"original_egg_damage1_{index:02d}.mod"))
        sample = samples[(clip["file"], pose["frame"])]
        if sample["pose_sha256"] != pose["sha256"]:
            raise ValueError("Egg joint sample does not bind converted pose")
        matrices = sample["joint_model_space_3x4"]
        if set(matrices) != {"root", "egg"}:
            raise ValueError("Egg authored joint names changed")
        for name in ["root", "egg"]:
            matrix = matrices[name]
            if len(matrix) != 3 or any(len(row) != 4 for row in matrix):
                raise ValueError("Egg joint matrix is not 3x4")
            values = [v for row in matrix for v in row]
            if not all(isinstance(v, (float, int)) and math.isfinite(v) for v in values):
                raise ValueError("Egg joint matrix is nonfinite")
            output.append("joint " + name + " " + " ".join(map(str, values)))
    general, proper = receipt["parameter_blocks"][1:3]
    parameters = [general["fp00"], *[proper[f"fp{i:02d}"] for i in range(1, 6)]]
    if not all(math.isfinite(v) and v >= 0 for v in parameters) or parameters[0] <= 0 or any(v > 1 for v in parameters[1:]):
        raise ValueError("Egg source health/drop parameters invalid")
    # Egg::Parms source constructor uses forcedDropType=0, doCheckHasSpray=1.
    output.append("parameters " + " ".join(map(str, parameters)) + " 0 1")
    colliders = receipt["collision"]
    if len(colliders) != 2:
        raise ValueError("Egg authored collision count changed")
    for index, node in enumerate(colliders):
        if node["parent"] != (None if index == 0 else 0) or node["joint"] != (1 if index == 0 else 0) or node["id"] != "none" or node["code"] != "____" or node["attribute"] != 0:
            raise ValueError("Egg authored collider fields changed")
        if len(node["offset"]) != 3 or not all(math.isfinite(v) for v in node["offset"]) or not math.isfinite(node["radius"]) or node["radius"] <= 0:
            raise ValueError("Egg source collider geometry invalid")
        output.append("collider " + " ".join(map(str, [-1 if node["parent"] is None else node["parent"], node["joint"], *node["offset"], node["radius"]])))
    # All reads, hashes and source topology validate before any staged write.
    models = destination / "assets/dataDir/courses/pikmin2room"
    models.mkdir(parents=True, exist_ok=True)
    for path, name in copies:
        shutil.copyfile(path, models / name)
    bank = destination / "p2-original-egg-bank.txt"
    bank.write_text("\n".join(output) + "\n", encoding="ascii")
    provenance = {
        "source_receipt_sha256": sha(receipt_path), "joint_bank_sha256": sha(joints_path),
        "bank_sha256": sha(bank), "source_revision": receipt["source_revision"],
        "model_sha256": receipt["model_sha256"],
        "pose_sha256": {name: sha(models / name) for _, name in copies},
        "ordinary_gameplay": "UNTESTED", "source_effect_audio_backend": "explicitly deferred when unavailable",
        "material_fidelity": "source converted sampled geometry; converter material approximation",
    }
    (destination / "p2-original-egg-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    return provenance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    stage(args.source, args.destination)
