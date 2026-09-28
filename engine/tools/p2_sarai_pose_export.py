"""Export verified Sarai mouth poses for the private native host (no asset embedding)."""
import argparse, hashlib, json, math, re
from pathlib import Path

def export(source, clip_name, output, models=False):
    raw = source.read_bytes()
    data = json.loads(raw)
    if data.get("species") != "Sarai" or data.get("enemy_id") != 23:
        raise ValueError("not a Sarai pose bank")
    clips = [c for c in data["clips"] if c["file"] == clip_name]
    if len(clips) != 1 or clips[0].get("status") != "converted":
        raise ValueError("missing or ambiguous converted clip")
    poses = clips[0]["poses"]
    # Sarai extraction samples at most 32 poses per clip (frames_for budget).
    if not 1 <= len(poses) <= 32:
        raise ValueError("pose budget")
    rows = ["P2_DEMON_POSES_2" if models else "P2_DEMON_MOUTHS_1", hashlib.sha256(raw).hexdigest(), str(len(poses))]
    previous = -1
    for pose in poses:
        frame = pose["frame"]
        if not isinstance(frame, int) or frame <= previous or frame > 100000:
            raise ValueError("frame order")
        previous = frame
        mouths = pose["mouths"]
        if [m["joint"] for m in mouths] != ["rkamujnt", "lkamujnt"]:
            raise ValueError("mouth order")
        values = []
        for mouth in mouths:
            matrix = mouth["matrix"]
            if mouth["radius"] != 15 or len(matrix) != 3 or any(len(r) != 4 for r in matrix):
                raise ValueError("mouth geometry")
            values += [float(x) for row in matrix for x in row]
        if any(not math.isfinite(x) or abs(x) > 1e6 for x in values):
            raise ValueError("invalid matrix")
        prefix = str(frame)
        if models:
            filename = pose["file"]
            if not re.fullmatch(r"[A-Za-z0-9_]+[.]mod", filename):
                raise ValueError("unsafe model basename")
            if hashlib.sha256((source.parent / filename).read_bytes()).hexdigest() != pose["sha256"]:
                raise ValueError("model hash mismatch")
            prefix += " " + filename
        rows.append(prefix + " " + " ".join(format(x, ".17g") for x in values))
    output.write_text("\n".join(rows) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("clip")
    parser.add_argument("output", type=Path)
    parser.add_argument("--models", action="store_true")
    args = parser.parse_args()
    export(args.source, args.clip, args.output, args.models)
