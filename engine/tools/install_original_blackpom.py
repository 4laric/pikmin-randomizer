"""Install the actual source-6 shared Pom bank into a private gameplay stage.

Consumes the existing disc converter's output; writes no actor/proxy sidecar.
Materials and pose sampling remain presentation approximations. Core conversion,
source collision/events, population and SAVE belong to the Purple mechanic.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

SOURCE_HASHES = {
    "enemy/data/Pom/anim.szs": "370b945e2f29461b476ae148f58462f0635c209075fae9a830a6f89f0fcf50b3",
    "enemy/data/Pom/model.szs": "881ddbd4b0809ffdbe17f07b565f1c9ee12df9921a61ae64cbfb70b85fce6088",
    "enemy/parm/enemyParms.szs": "3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84",
}
CLIPS = [("wait", 1), ("dead", 40), ("type1", 30), ("type2", 30), ("type3", 40), ("type4", 20)]


def install(imported: Path, stage: Path, source_root: Path = Path.cwd()):
    sys.path.insert(0, str(source_root.resolve()))
    from experimental.pikmin2_convert import blocks, u16, u32
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_rigid import joint_matrices
    from experimental.pikmin2_breadbug_assets import collision_nodes
    report = json.loads((imported / "flora.json").read_text())
    if report["disc_id"] != "GPVE01" or report["source_sha256"] != SOURCE_HASHES:
        raise ValueError("BlackPom actual disc resource identity mismatch")
    species = report["species"]["BlackPom"]
    if species["enemy_id"] != 6 or species["resource"] != "Pom":
        raise ValueError("BlackPom source family mismatch")
    model = (imported / "BlackPom/enemy.bmd").read_bytes()
    if hashlib.sha256(model).hexdigest() != species["model_sha256"]:
        raise ValueError("BlackPom source model hash mismatch")
    collision = (imported / "BlackPom/enemycoll.txt").read_bytes()
    if hashlib.sha256(collision).hexdigest() != species["metadata_sha256"]["enemycoll.txt"]:
        raise ValueError("BlackPom source collision hash mismatch")
    colliders = collision_nodes(collision, len(species["joints"]))
    if colliders != species["collision"] or len(colliders) != 7:
        raise ValueError("BlackPom source collision topology mismatch")
    joint_lines = ["P2_ORIGINAL_BLACKPOM_JOINTS_1"]
    model_blocks = blocks(model)
    materials = model_blocks["MAT3"]
    table = u32(materials, 20)
    names = []
    for index in range(u16(materials, table)):
        start = table + u16(materials, table + 6 + index * 4)
        names.append(materials[start:materials.index(b"\0", start)].decode("shift_jis"))
    hierarchy = model_blocks["INF1"]
    at = u32(hierarchy, 20)
    material = 0
    petal_shapes = []
    while True:
        kind, index = u16(hierarchy, at), u16(hierarchy, at + 2)
        at += 4
        if kind == 0:
            break
        if kind == 0x11:
            material = index
        if kind == 0x12 and names[material] == "hanabira1_v":
            petal_shapes.append(index)
    if petal_shapes != [0]:
        raise ValueError("BlackPom source petal material mapping changed")
    for i, collider in enumerate(colliders):
        joint_lines.append("collider " + " ".join(map(str, [i, collider["joint"],
            -1 if collider["parent"] is None else collider["parent"], collider["id"],
            collider["code"], *collider["offset"], collider["radius"]])))
    entries = {clip["name"]: clip for clip in species["clips"]}
    pending = []
    lines = ["P2_ORIGINAL_BLACKPOM_BANK_1 6"]
    for name, duration in CLIPS:
        clip = entries[name]
        animation = (imported / "BlackPom" / (name + ".bca")).read_bytes()
        if hashlib.sha256(animation).hexdigest() != clip["source_sha256"]:
            raise ValueError("BlackPom original animation hash mismatch")
        frames = [pose["frame"] for pose in clip["poses"]]
        if (clip["status"] != "converted" or clip["source_frames"] != duration
                or not frames or frames[0] != 0 or frames[-1] != duration - 1
                or any(a >= b for a, b in zip(frames, frames[1:]))):
            raise ValueError("BlackPom source clip incomplete")
        for index, pose in enumerate(clip["poses"]):
            filename = f"flora_BlackPom_{name}_{index:02}.mod"
            if pose["file"] != filename:
                raise ValueError("BlackPom pose filename mismatch")
            src = imported / "BlackPom" / filename
            if hashlib.sha256(src.read_bytes()).hexdigest() != pose["sha256"]:
                raise ValueError("BlackPom converted pose hash mismatch")
            pending.append((src, filename))
        lines += [f"clip {name} {len(frames)} {duration} flora_BlackPom_{name}",
                  "frames " + " ".join(map(str, frames))]
        # Collision uses every original integer BCA frame rather than sparse
        # presentation poses; no source joint is inferred from a P1 flower.
        for frame in range(duration):
            actual_duration, pose = bca_pose(animation, frame, len(species["joints"]), allow_scale=True)
            if actual_duration != duration:
                raise ValueError("BlackPom source animation duration mismatch")
            matrices = joint_matrices(model_blocks, local_overrides=pose)
            for joint in sorted({c["joint"] for c in colliders}):
                joint_lines.append("joint " + " ".join(map(str, [name, frame, joint,
                    *(value for row in matrices[joint] for value in row)])))
    # All identity/hash checks precede stage writes. Never copy legal resources
    # into a tracked source tree or another owner's active stage.
    target = stage / "assets/dataDir/courses/pikmin2room"
    if (stage / "p2-original-blackpom-bank.txt").exists():
        raise ValueError("BlackPom stage already installed")
    target.mkdir(parents=True, exist_ok=True)
    for src, filename in pending:
        if (target / filename).exists():
            raise ValueError("BlackPom pose destination already exists")
    for src, filename in pending:
        shutil.copyfile(src, target / filename)
    # Original setPomColor(Purple) writes TEV RGB(28,0,52) on hanabira1_v.
    # PVW uses an explicitly approximate diffuse multiplier; alpha is retained
    # opaque rather than incorrectly copying retail's unused TEV alpha zero.
    lines.append("petal 0 28 0 52 255")
    (stage / "p2-original-blackpom-bank.txt").write_text("\n".join(lines) + "\n")
    (stage / "p2-original-blackpom-joints.txt").write_text("\n".join(joint_lines) + "\n")
    (stage / "blackpom-source-resource.json").write_text(json.dumps(species, indent=2) + "\n")
    return {"source": 6, "poses": len(pending), "clips": 6,
            "gameplay_qualified": False, "presentation": "sampled poses, approximate materials"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--imported", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True, help="Read-only randomizer converter source root")
    args = p.parse_args()
    print(json.dumps(install(args.imported, args.stage, args.source_root)))
