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
from preview_pikmin2_room import overlay


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(assets, content, run):
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
    data = data[:20] + struct.pack(">I", len(entries)) + b"".join(entries)
    empty = data[:20] + struct.pack(">I", 0)
    overrides = {
        "dataDir/stages/chal0.ini": (assets / "dataDir/stages/practice.ini").read_bytes(),
        "dataDir/stages/chal0/default.gen": data,
        "dataDir/courses/pikmin2room/arena-private.txt": b"P1 original stage arena\n",
    }
    for path in (assets / "dataDir/stages/chal0").glob("*.gen"):
        overrides.setdefault("dataDir/stages/chal0/" + path.name, empty)
    run.mkdir(parents=True)
    overlay(assets, run / "assets", overrides)
    stage = run / "assets/dataDir/stages/chal0/default.gen"
    birth = deterministic_births(stage, [346002, 346010])
    installed = stage_elecbug_ground(content, run, [(346002, "ElecBug"), (346010, "ElecBug")])
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
    (run / "elecbug-contact-inputs.json").write_text(json.dumps(receipt, indent=2))
    return run


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("assets", "content", "run"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    print(prepare(a.assets, a.content, a.run))
