"""Stage private literal Qurione geometry, joints, events and parameters."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def stage(source, destination):
    receipt_path = source / "qurione.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    joints = json.loads((source / "joint-matrices.json").read_text(encoding="utf-8"))
    if receipt["source_id"] != 16 or receipt["catalog_id"] != "Qurione" or receipt["joints"][4] != "body_jnt2":
        raise ValueError("literal Qurione source/rig mismatch")
    if joints["source_manifest_sha256"] != sha(receipt_path) or joints["model_sha256"] != receipt["model_sha256"]:
        raise ValueError("joint bank does not bind source receipt/model")
    if sha(source / "enemy.bmd") != receipt["model_sha256"] or len(receipt["clips"]) != 5:
        raise ValueError("Qurione actual model bytes or source clip count changed")
    root = destination.resolve()
    models = root / "assets/dataDir/courses/pikmin2room"
    samples = {(p["clip"], p["source_frame"]): p for p in joints["poses"]}
    output = ["P2_ORIGINAL_WISP_BANK_1"]
    copies = []
    for clip, name, duration, events in zip(receipt["clips"], ["waitl", "damage", "run", "appear1", "hide1"], [100, 35, 10, 30, 30], [[[0, 0], [99, 1]], [[5, 2]], [[0, 0], [9, 1]], [], []]):
        if clip["file"] != name + ".bca" or clip["duration"] != duration or clip["events"] != events:
            raise ValueError("Qurione exact source motion/event table changed")
        poses = clip["poses"]
        output.append(f"clip {name} {len(poses)} {duration} original_wisp_{name} {len(events)}")
        output.append("events " + " ".join(str(v) for ev in events for v in ev))
        output.append("frames " + " ".join(str(p["frame"]) for p in poses))
        for index, pose in enumerate(poses):
            path = source / pose["file"]
            if sha(path) != pose["sha256"]:
                raise ValueError("converted Qurione pose bytes differ from receipt")
            sample = samples[(clip["file"], pose["frame"])]
            if sample["pose_sha256"] != pose["sha256"]:
                raise ValueError("Qurione joint sample does not bind converted pose")
            for joint in ["water", "body_jnt2"]:
                matrix = sample["joint_model_space_3x4"][joint]
                if len(matrix) != 3 or any(len(row) != 4 for row in matrix):
                    raise ValueError("invalid Qurione 3x4 matrix")
                output.append("joint " + joint + " " + " ".join(str(v) for row in matrix for v in row))
            copies.append((path, models / f"original_wisp_{name}_{index:02d}.mod"))
    general, proper = receipt["parameter_blocks"][1:3]
    output.append("parameters " + " ".join(map(str, [proper["fp01"], proper["fp02"], proper["fp03"], proper["fp04"], proper["fp05"], general["fp06"], general["fp13"], general["fp25"], general["fp00"]])))
    props = receipt["parameter_blocks"][0]
    output.append("physics " + " ".join(map(str, [props["s003"], general["fp01"], general["fp02"], props["s001"]])))
    nodes = receipt["collision"]
    if len(nodes) != 2:
        raise ValueError("Qurione source collider count changed")
    for i, node in enumerate(nodes):
        if node["joint"] != 4 or node["id"] != "none" or node["code"] != ("____" if i == 0 else "_t__") or node["attribute"] != 0 or node["parent"] != (None if i == 0 else 0):
            raise ValueError("Qurione source collider fields changed")
        output.append("collider " + " ".join(map(str, [-1 if node["parent"] is None else node["parent"], *node["offset"], node["radius"]])))
    models.mkdir(parents=True, exist_ok=True)
    for old, new in copies:
        shutil.copyfile(old, new)
    bank = root / "p2-original-wisp-bank.txt"
    bank.write_text("\n".join(output) + "\n", encoding="ascii")
    (root / "p2-original-wisp-provenance.json").write_text(json.dumps({"source_receipt_sha256": sha(receipt_path), "joint_bank_sha256": sha(source / "joint-matrices.json"), "bank_sha256": sha(bank), "source_revision": receipt["source_revision"], "ordinary_gameplay": "UNTESTED", "source_effect_audio_backend": "DEFERRED"}, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    stage(args.source, args.destination)
