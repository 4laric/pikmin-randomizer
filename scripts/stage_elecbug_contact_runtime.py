"""Fresh engineered Impact Site arena for #1164; source assets remain read-only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from experimental.pikmin2_batch2_core import roster, deterministic_births
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_elecbug_content import stage_elecbug_ground
from preview_pikmin2_room import overlay, records, ensure_pikmin_squad


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(assets, content, run, *, white=None, pod=None, safe_squad=False):
    assets, content, run = map(lambda p: Path(p).resolve(), (assets, content, run))
    if run.exists():
        raise ValueError("fresh run directory required")
    cfg = dict(FAMILIES["ground"])
    cfg.update(arena_species=("ElecBug", "ElecBug"), arena_ids=(346002, 346010),
               arena_positions=((-100., 30., 1660.), (120., 30., 1660.)))
    data, actors = roster(cfg, assets)
    starts = [m.start() for m in re.finditer(b"    0.0v", data)]
    entries = [data[s:(starts[i + 1] if i + 1 < len(starts) else len(data))]
               for i, s in enumerate(starts)]
    # Keep original scenery/Onions. Only this fixture's two enemy births and
    # the current overlay's standard20 Reds participate in the encounter.
    entries = [r for r in entries if r[72:76] != b"ikip" and
               (r[72:76] != b"iket" or struct.unpack_from("<I", r, 8)[0] in (346002, 346010))]
    # Opt-in ordinary White acquisition: stage a bound Ivory, never White actors.
    if (white is None) != (pod is None):
        raise ValueError("White bank and Pod inputs must be supplied together")
    if white is not None:
        white, pod = Path(white).resolve(strict=True), Path(pod).resolve(strict=True)
        manifest_lines = [line.split() for line in (white / "p2-white.txt").read_text().splitlines()]
        bindings = [line for line in manifest_lines if line and line[0] == "ivory_generators"]
        if not manifest_lines or manifest_lines[0] != ["P2_WHITE_1"] or bindings != [["ivory_generators", "1", "25"]]:
            raise ValueError("expected exactly one reviewed Ivory generator25 binding")
        if any(struct.unpack_from("<I", r, 8)[0] == 25 for r in entries):
            raise ValueError("Ivory generator25 collides with retained scenery")
        template = next(r for r in records(assets / "dataDir/stages/chal0/default.gen")
                        if r[72:80] == b"ssob\x02\x00\x00\x00")
        flower = bytearray(template)
        struct.pack_into("<I", flower, 8, 25)
        flower[16:48] = b"contact fixture ivory".ljust(32, b"\0")
        struct.pack_into(">6f", flower, 48, 150., 30., 1860., 0., 0., 0.)
        struct.pack_into(">I", flower, 80, 5 | (1 << 6))
        entries.append(bytes(flower))
    data = data[:20] + struct.pack(">I", len(entries)) + b"".join(entries)
    if safe_squad:
        # Engineered initial placement only: prevent falling starting Reds
        # from reversing/killing the receiver before controller observation.
        data = ensure_pikmin_squad(assets, data)
        data = bytearray(data)
        for index, match in enumerate(re.finditer(b"fixture starting squad", data)):
            # The practice floor at X240..312/Z1812..1820 is Y30.
            struct.pack_into(">3f", data, match.start() + 32,
                             240.0 + (index % 10) * 8.0, 30.0,
                             1820.0 - (index // 10) * 8.0)
        data = bytes(data)
    empty = data[:20] + struct.pack(">I", 0)
    overrides = {
        "dataDir/stages/chal0.ini": (assets / "dataDir/stages/practice.ini").read_bytes(),
        "dataDir/stages/chal0/default.gen": data,
        "dataDir/courses/pikmin2room/arena-private.txt": b"P1 original stage arena\n",
    }
    for path in (assets / "dataDir/stages/chal0").glob("*.gen"):
        overrides.setdefault("dataDir/stages/chal0/" + path.name, empty)
    if white is not None:
        for model in white.glob("*.mod"):
            overrides["dataDir/courses/pikmin2room/" + model.name] = model.read_bytes()
        overrides["dataDir/courses/pikmin2room/pod.mod"] = (pod / "pod.mod").read_bytes()
    run.mkdir(parents=True)
    overlay(assets, run / "assets", overrides)
    stage = run / "assets/dataDir/stages/chal0/default.gen"
    birth = deterministic_births(stage, [346002, 346010])
    installed = stage_elecbug_ground(content, run, [(346002, "ElecBug"), (346010, "ElecBug")])
    if white is not None:
        (run / "p2-white.txt").write_bytes((white / "p2-white.txt").read_bytes())
        (run / "p2-pod.txt").write_bytes((pod / "p2-pod.txt").read_bytes())
    (run / "p2-cargo-free.txt").write_text("P2_CARGO_FREE_1\n")
    staged = stage.read_bytes()
    if staged.count(b"fixture starting squad") != 20:
        raise ValueError("current overlay did not supply20 Reds")
    receipt = dict(issue=1164, actors=actors, installed=installed, birth=birth,
                   stage_sha256=sha(stage), overlay_sha256=sha(ROOT / "scripts/preview_pikmin2_room.py"),
                   content_manifest_sha256=sha(content / "elecbug.json"),
                   source_stage_sha256=sha(assets / "dataDir/stages/practice/default.gen"),
                   starting_squad="20 Reds from current ensure_pikmin_squad; live count pending",
                   placement="engineered static pair near the squad, not campaign placement acceptance")
    receipt["safe_squad_initial_grid"] = dict(x=240.0, y=30.0, z=1820.0,
                                             columns=10, spacing=8.0) if safe_squad else None
    if white is not None:
        receipt["white_acquisition"] = dict(
            ivory_generator=25, staged_xyz=[150., 30., 1860.],
            white_manifest_sha256=sha(white / "p2-white.txt"),
            pod_manifest_sha256=sha(pod / "p2-pod.txt"),
            method="ordinary capture/conversion/ejection/pluck required; no initial White actors",
            placement_runtime_validated=False, native_acquisition_accepted=False)
    (run / "elecbug-contact-inputs.json").write_text(json.dumps(receipt, indent=2))
    return run


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("assets", "content", "run"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--white", type=Path)
    p.add_argument("--pod", type=Path)
    a = p.parse_args()
    print(prepare(a.assets, a.content, a.run, white=a.white, pod=a.pod))
