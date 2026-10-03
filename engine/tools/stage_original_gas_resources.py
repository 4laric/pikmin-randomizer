"""Stage audited private GasHiba converted geometry for the original provider.

No legal bytes enter source control. Source JPA/audio backends remain separately
required by Native::Services; conversion is not ordinary gameplay acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(source: Path, destination: Path):
    receipt_path = source / "assets.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    joints = json.loads((source / "joint-matrices.json").read_text(encoding="utf-8"))
    if receipt["source_id"] != 21 or receipt["species"] != "GasHiba" or receipt["joints"] != ["gasuhiba1"]:
        raise ValueError("literal GasHiba source/rig mismatch")
    if joints["source_manifest_sha256"] != sha(receipt_path) or joints["model_sha256"] != receipt["model_sha256"]:
        raise ValueError("joint bank does not bind source receipt/model")
    root = destination.resolve()
    models = root / "assets/dataDir/courses/pikmin2room"
    models.mkdir(parents=True, exist_ok=True)
    output = ["P2_ORIGINAL_GAS_BANK_1"]
    samples = {(p["clip"], p["source_frame"]): p for p in joints["poses"]}
    for clip, expected, duration, events in zip(receipt["clips"], ["wait", "attack"], [1, 4], [[], [[0, 0], [3, 1]]]):
        if clip["file"] != expected + ".bca" or clip["duration"] != duration or clip["events"] != events:
            raise ValueError("GasHiba exact source motion/event table changed")
        poses = clip["poses"]
        output.append(f"clip {expected} {len(poses)} {duration} original_gas_{expected}")
        output.append("frames " + " ".join(str(p["frame"]) for p in poses))
        for index, pose in enumerate(poses):
            path = source / pose["file"]
            if sha(path) != pose["sha256"] or path.stat().st_size != pose["bytes"]:
                raise ValueError("converted GasHiba pose bytes differ from receipt")
            sample = samples[(clip["file"], pose["frame"])]
            if sample["pose_sha256"] != pose["sha256"]:
                raise ValueError("GasHiba joint sample does not bind converted pose")
            matrix = sample["joint_model_space_3x4"]["gasuhiba1"]
            if len(matrix) != 3 or any(len(row) != 4 for row in matrix):
                raise ValueError("invalid GasHiba 3x4 matrix")
            output.append("joint " + " ".join(str(v) for row in matrix for v in row))
            shutil.copyfile(path, models / f"original_gas_{expected}_{index:02d}.mod")
    general, proper = receipt["parameter_blocks"][1:3]
    # Missing fp90/91 retain source GasHiba::ProperParms constructor values.
    values = [proper["fp02"], proper["fp01"], proper["fp03"], proper["fp04"], proper.get("fp90", .085),
              proper.get("fp91", .05), general["fp00"], general["fp24"], general["fp22"], general["fp20"], general["fp21"]]
    output.append("parameters " + " ".join(map(str, values)))
    colliders = receipt["collision"]
    if len(colliders) != 2:
        raise ValueError("GasHiba retail collider count changed")
    for index, node in enumerate(colliders):
        if node["joint"] != 0 or node["id"] != "none" or node["code"] != "____" or node["attribute"] != 0 or node["parent"] != (None if index == 0 else 0):
            raise ValueError("GasHiba source collider fields changed")
        output.append("collider " + " ".join(map(str, [-1 if node["parent"] is None else node["parent"], *node["offset"], node["radius"]])))
    (root / "p2-original-gas-bank.txt").write_text("\n".join(output) + "\n", encoding="ascii")
    (root / "p2-original-gas-provenance.json").write_text(json.dumps({
        "source_receipt_sha256": sha(receipt_path), "joint_bank_sha256": sha(source / "joint-matrices.json"),
        "bank_sha256": sha(root / "p2-original-gas-bank.txt"), "source_revision": receipt["source_revision"],
        "ordinary_gameplay": "UNTESTED", "source_effect_audio_backend": "required separately",
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    stage(args.source, args.destination)
