"""Dump retail per-species fp27 (life gauge height) and fp00 (health) from a US GPVE01 disc.

Provenance for native pc_port/pc_p2_life_gauge.h (P2 EnemyBase::doGetLifeGaugeParam puts
the life wheel at mPosition.y + general fp27; include/Game/EnemyParmsBase.h default 50).

    py -3.12 scripts/p2_life_meter_heights.py --iso "C:/.../PIKMIN2 for GAMECUBE.iso" --out heights.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental.pikmin2_assets import archive_files, disc_files  # noqa: E402

ROW = re.compile(r"\{([a-z0-9]+)\}\s+4\s+([-+\d.eE]+)")


def general_group(text: str):
    groups, current = [], None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if line == "{":
            current = {}
        elif line == "}":
            groups.append(current)
            current = None
        else:
            m = ROW.fullmatch(line)
            if m and current is not None:
                current[m.group(1)] = float(m.group(2))
    return groups[1] if len(groups) >= 2 else {}


def heights(iso: Path) -> dict:
    index = disc_files(iso)
    at, size = index["enemy/parm/enemyParms.szs"]
    with iso.open("rb") as disc:
        disc.seek(at)
        files = archive_files(disc.read(size))
    out = {}
    for name, data in files.items():
        if name.endswith("/enemyparm.txt"):
            general = general_group(data.decode("shift_jis"))
            out[name.split("/")[0]] = {"fp00": general.get("fp00"), "fp27": general.get("fp27")}
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = heights(args.iso)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(result)} species -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
