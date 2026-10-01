#!/usr/bin/env python3
"""Compare two P2 dense content caches and draw eye-check contact sheets (#996/#1002).

Pose MODs (`<stem>_NN.mod`) are paired by path relative to the cache root. The
per-pose delta is the largest distance any vertex moved (MOD chunk 0x10
positions, same vertex count) between the old and the new cache. Species whose
vertex count changed are reported as `topology` changes instead.

    py -3.12 scripts/p2_reextract_compare.py delta OLD NEW [--json out.json]
    py -3.12 scripts/p2_reextract_compare.py sheet OLD NEW OUTDIR [--species Hana,Kabuto]

A sheet is a point-cloud plot (front and side orthographic, one fixed scale per
species so a shrunk or exploded part is visible) of the old pose next to the
new pose for an idle, an attack, a dead and the max-delta clip. It is a quick
eye check, not a textured render.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

POSE_RE = re.compile(r"^(?P<stem>.+)_(?P<idx>\d+)$")


def read_positions(path):
    data = Path(path).read_bytes()
    at = 0
    while at + 8 <= len(data):
        tag, size = struct.unpack_from(">II", data, at)
        if tag == 0x10:
            count = struct.unpack_from(">I", data, at + 8)[0]
            start = at + 8 + 24
            if count < 0 or start + count * 12 > len(data):
                return None
            return list(struct.iter_unpack(">fff", data[start:start + count * 12]))
        if tag == 0xFFFF:
            break
        at += 8 + size
    return None


def species_poses(root, species):
    base = Path(root) / species
    return {p.relative_to(base).as_posix(): p for p in base.rglob("*.mod")}


def pose_delta(a, b):
    if a is None or b is None:
        return None
    if len(a) != len(b):
        return "topology"
    worst = 0.0
    for (ax, ay, az), (bx, by, bz) in zip(a, b):
        d = max(abs(ax - bx), abs(ay - by), abs(az - bz))
        if d > worst:
            worst = d
    return worst


def compare_species(old_root, new_root, species):
    old, new = species_poses(old_root, species), species_poses(new_root, species)
    result = {"poses": len(new), "missing_in_new": sorted(set(old) - set(new))[:10],
              "missing_in_old": sorted(set(new) - set(old))[:10],
              "max_delta": 0.0, "max_pose": None, "topology": 0, "changed": 0, "per_clip": {},
              "by_model": {}}
    for rel in sorted(set(old) & set(new)):
        a, b = read_positions(old[rel]), read_positions(new[rel])
        d = pose_delta(a, b)
        if d is None:
            continue
        if d == "topology":
            result["topology"] += 1
            continue
        if d > 1e-4:
            result["changed"] += 1
        model = rel.split("/")[0] if "/" in rel else "."
        if d > result["by_model"].get(model, 0.0):
            result["by_model"][model] = d
        stem = rel[:-4]
        m = POSE_RE.match(stem)
        clip = m.group("stem") if m else stem
        if d > result["per_clip"].get(clip, 0.0):
            result["per_clip"][clip] = d
        if d > result["max_delta"]:
            result["max_delta"], result["max_pose"] = d, rel
    return result


def species_dirs(root):
    return sorted(p.name for p in Path(root).iterdir() if p.is_dir())


def cmd_delta(args):
    names = args.species.split(",") if args.species else sorted(
        set(species_dirs(args.old)) & set(species_dirs(args.new)))
    out = {n: compare_species(args.old, args.new, n) for n in names}
    for n, r in out.items():
        print(f"{n:16} poses {r['poses']:5} changed {r['changed']:5} topology {r['topology']:4} "
              f"max_delta {r['max_delta']:9.3f}  {r['max_pose'] or ''}")
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1), encoding="utf-8")


def pick_clips(rels, worst_rel):
    def clip_of(rel):
        m = POSE_RE.match(rel[:-4])
        return (m.group("stem") if m else rel[:-4]), (int(m.group("idx")) if m else 0)

    clips = {}
    for rel in rels:
        c, i = clip_of(rel)
        clips.setdefault(c, []).append((i, rel))
    for v in clips.values():
        v.sort()

    def find(*words):
        for w in words:
            for c in sorted(clips):
                if w in c.lower() and "hair" not in c.lower():
                    return c
        return None

    chosen = []
    for c in (find("wait", "idle", "move", "walk"), find("attack", "eat", "bite"), find("dead", "die")):
        if c and c not in chosen:
            chosen.append(c)
    if worst_rel:
        c, _ = clip_of(worst_rel)
        if c not in chosen:
            chosen.append(c)
    rows = []
    for c in chosen:
        poses = clips[c]
        if worst_rel and clip_of(worst_rel)[0] == c:
            rows.append((c, worst_rel))
        else:
            rows.append((c, poses[len(poses) // 2][1]))
    if not rows:
        first = sorted(clips)[0]
        rows.append((first, clips[first][0][1]))
    return rows


def cmd_sheet(args):
    from PIL import Image, ImageDraw
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    names = args.species.split(",") if args.species else sorted(
        set(species_dirs(args.old)) & set(species_dirs(args.new)))
    index = {}
    for name in names:
        old, new = species_poses(args.old, name), species_poses(args.new, name)
        common = sorted(set(old) & set(new))
        if not common:
            continue
        summary = compare_species(args.old, args.new, name)
        rows = pick_clips(common, summary["max_pose"])
        panels = []
        allpts = []
        for _, rel in rows:
            a, b = read_positions(old[rel]), read_positions(new[rel])
            panels.append((rel, a or [], b or []))
            allpts += (a or []) + (b or [])
        if not allpts:
            continue
        cell = 240
        label_h = 14
        img = Image.new("RGB", (cell * 4, (cell + label_h) * len(panels) + 16), (24, 24, 28))
        dr = ImageDraw.Draw(img)
        dr.text((4, 2), f"{name}  cols: old front, old side, NEW front, NEW side   max delta {summary['max_delta']:.2f}",
                fill=(255, 255, 255))
        for r, (rel, a, b) in enumerate(panels):
            y0 = 16 + r * (cell + label_h)
            both = a + b
            if not both:
                continue
            xs = [p[0] for p in both]
            ys = [p[1] for p in both]
            zs = [p[2] for p in both]
            span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-3)
            scale = (cell - 20) / span
            cx, cy, cz = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2
            dr.text((4, y0), f"{rel[:60]}  span {span:.0f}", fill=(200, 200, 120))
            for c, (pts, color) in enumerate(((a, (150, 150, 170)), (b, (90, 220, 120)))):
                for v, (h, w) in enumerate(((0, 1), (2, 1))):  # front: x/y, side: z/y
                    ox = (c * 2 + v) * cell
                    dr.rectangle([ox, y0 + label_h, ox + cell - 1, y0 + label_h + cell - 1], outline=(60, 60, 70))
                    mid = (cx, cy, cz)
                    for p in pts:
                        px = ox + cell / 2 + (p[h] - mid[h]) * scale
                        py = y0 + label_h + cell - 10 - (p[w] - min(ys)) * scale
                        dr.point((px, py), fill=color)
        path = outdir / f"{name}.png"
        img.save(path)
        index[name] = {"sheet": str(path), "max_delta": summary["max_delta"], "clips": [r[1] for r in rows]}
    (outdir / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    print(f"wrote {len(index)} sheets to {outdir}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("delta")
    d.add_argument("old")
    d.add_argument("new")
    d.add_argument("--species")
    d.add_argument("--json")
    d.set_defaults(fn=cmd_delta)
    s = sub.add_parser("sheet")
    s.add_argument("old")
    s.add_argument("new")
    s.add_argument("outdir")
    s.add_argument("--species")
    s.set_defaults(fn=cmd_sheet)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
