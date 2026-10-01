"""World position of the Jellyfloat `suck` part (Proom joint) per baked pose (#960).

The native host holds captured Pikmin and the captain at the source `suck`
collision part, which sits on the Proom joint (enemycoll.txt: joint 4). The port
draws one static baked pose per motion, so the joint is tabulated per pose in
``native/pc_port/pc_p2_kurage_proom.h``. This script recomputes that table from a
staged content root (``<root>/Kurage`` and ``<root>/OniKurage``: enemy.bmd, the
retail .bca clips and the per-clip pose json) using the same skeleton and
animation decoders as the converter.

    py -3.12 scripts/kurage_proom_offsets.py output/p2-content-dense
    py -3.12 scripts/kurage_proom_offsets.py output/p2-content-dense --check path/to/pc_p2_kurage_proom.h
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental.pikmin2_convert import blocks  # noqa: E402
from experimental.pikmin2_purple import bca_pose  # noqa: E402
from experimental.pikmin2_rigid import joint_matrices  # noqa: E402

PROOM_JOINT = "Proom"


def proom_offsets(content_root, enum):
    """{clip stem: (x, y, z)} of the Proom joint at each clip's baked pose frame."""
    species = Path(content_root) / enum
    model = blocks((species / "enemy.bmd").read_bytes())
    meta = json.loads((species / f"{enum.lower()}.json").read_text(encoding="utf-8"))
    joints = meta["joints"]
    index = joints.index(PROOM_JOINT)
    rows = {}
    for clip in meta["clips"]:
        frame = clip["poses"][0]["frame"]
        _, pose = bca_pose((species / clip["file"]).read_bytes(), frame, len(joints), allow_scale=True)
        matrix = joint_matrices(model, pose)[index]
        rows[clip["file"][:-4]] = tuple(round(matrix[r][3], 1) for r in range(3))
    return rows


def header_rows(path):
    """{pose: (lesser xyz, greater xyz)} parsed from pc_p2_kurage_proom.h."""
    num = r"(-?\d+\.\d+)f"
    row = re.compile(r'\{"(\w+)",\s*\{%s,\s*%s,\s*%s\},\s*\{%s,\s*%s,\s*%s\}\}' % ((num,) * 6))
    out = {}
    for m in row.finditer(Path(path).read_text(encoding="utf-8")):
        v = [float(g) for g in m.groups()[1:]]
        out[m.group(1)] = (tuple(v[:3]), tuple(v[3:]))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("content_root", type=Path)
    parser.add_argument("--check", type=Path, help="pc_p2_kurage_proom.h to compare against")
    args = parser.parse_args(argv)
    lesser = proom_offsets(args.content_root, "Kurage")
    greater = proom_offsets(args.content_root, "OniKurage")
    if args.check:
        table = header_rows(args.check)
        bad = []
        for pose, l in lesser.items():
            want = table.get(pose)
            if want is None or any(abs(a - b) > 0.05 for a, b in zip(want[0], l)) \
                    or any(abs(a - b) > 0.05 for a, b in zip(want[1], greater[pose])):
                bad.append(pose)
        if bad or set(table) != set(lesser):
            print("MISMATCH", bad, sorted(set(table) ^ set(lesser)))
            return 1
        print("pc_p2_kurage_proom.h matches the retail skeleton for", len(lesser), "poses")
        return 0
    for pose in sorted(lesser):
        print(f"{pose:8s} lesser {lesser[pose]} greater {greater[pose]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
