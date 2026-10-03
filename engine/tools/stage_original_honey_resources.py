"""Stage verified private ItemHoney source models, clocks and receiver keys."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(root, name, sha, size=None):
    path = (root / name).resolve()
    if path.parent != root.resolve() or not path.is_file() or digest(path) != sha:
        raise ValueError(f"source Honey file/hash mismatch: {name}")
    if size is not None and path.stat().st_size != size:
        raise ValueError(f"source Honey file size mismatch: {name}")
    return path


def stage(source, receivers, destination):
    source, receivers = source.resolve(), receivers.resolve()
    manifest = source / "assets.json"
    if digest(manifest) != "299964b7553dcf53812289e86ef34dc118784e636241e3b6ede7e5f68d6bd3a5":
        raise ValueError("source Honey receipt changed; audit the replacement before staging")
    receipt = json.loads(manifest.read_text(encoding="utf-8"))
    if receipt["model"] != "mitu.bmd" or receipt["joint_names"] != ["all"] or receipt["material_names"] != ["mitu1"]:
        raise ValueError("source Honey model/rig/material identity changed")
    checked(source, "mitu.bmd", receipt["model_sha256"])
    checked(source, "honeyanimmgr.txt", "f8ceb062ad92f1b1187bcebae23a2855a0c2ce9e018124c9f018e698298bb145")
    checked(source, "aiConstants.txt", receipt["source_resources"]["user/Kando/aiConstants.txt"]["sha256"])
    checked(receivers, "animmgr.txt", receipt["receiver_registry_sha256"])
    transfers = []
    for name, key in [("p2-original-honey-events.txt", "event_table_sha256"), ("p2-original-honey-attach.txt", "attachment_sha256")]:
        transfers.append((checked(source, name, receipt[key]), name))
    transfers.append((checked(receivers, "p2-honey-receiver-events.txt", receipt["receiver_event_table_sha256"]), "p2-honey-receiver-events.txt"))
    lines = ["P2_ORIGINAL_HONEY_BANK_1 " + " ".join([digest(manifest), receipt["event_table_sha256"], receipt["attachment_sha256"], receipt["receiver_event_table_sha256"]])]
    expected = [("born", 30), ("airwait", 20), ("fall", 8), ("swing", 40), ("wait", 40), ("touch", 60), ("dead", 50)]
    if len(receipt["clips"]) != 7:
        raise ValueError("source Honey clip topology changed")
    for ordinal, (clip, (name, duration)) in enumerate(zip(receipt["clips"], expected)):
        if clip["anim_id"] != ordinal or clip["name"] != name or clip["duration"] != duration or clip["file"] != name + ".bca":
            raise ValueError("source Honey authored clip mapping changed")
        checked(source, clip["file"], clip["source_sha256"])
        poses = clip["poses"]
        frames = [pose["frame"] for pose in poses]
        if not 1 <= len(poses) <= 64 or frames[0] != 0 or frames[-1] != duration - 1 or any(a >= b for a, b in zip(frames, frames[1:])):
            raise ValueError("source Honey sampled frame indices invalid")
        lines.append(f"clip {name} {len(poses)} {duration} original_honey_{name} " + " ".join(map(str, frames)))
        hashes = []
        for index, pose in enumerate(poses):
            path = checked(source, pose["file"], pose["sha256"], pose["bytes"])
            transfers.append((path, f"assets/dataDir/courses/pikmin2room/original_honey_{name}_{index:02d}.mod"))
            hashes.append(pose["sha256"])
        lines.append(" ".join(hashes))
    for clip in receipt["receiver_clips"]:
        checked(receivers, clip["file"], clip["source_sha256"])
    gravity = receipt["mechanics"]["gravity"]
    if not math.isfinite(gravity) or gravity != 560.0:
        raise ValueError("source Honey gravity changed")
    lines.append(f"gravity {gravity}")
    # Every input hash validates before creating or replacing a staged file.
    destination.mkdir(parents=True, exist_ok=True)
    for old, relative in transfers:
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, target)
    bank = destination / "p2-original-honey-bank.txt"
    bank.write_text("\n".join(lines) + "\n", encoding="ascii")
    (destination / "p2-original-honey-provenance.json").write_text(json.dumps({"source_receipt_sha256": digest(manifest), "bank_sha256": digest(bank), "source_effect_audio_material": "DEFERRED", "ordinary_gameplay": "UNTESTED", "receivers": "actual shared P2 source clocks; P1 character motions presentation only"}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--receivers", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    stage(args.source, args.receivers, args.destination)
