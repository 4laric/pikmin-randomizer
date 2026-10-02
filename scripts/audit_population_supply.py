"""Decode supplier metadata from legal local P1 inputs; copy no asset payloads."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zlib

from scripts.audit_enemy_slots import Reader, audit, param_int


def pellet_configs(data):
    r = Reader(data)
    count = r.integer()
    if not 0 < count < 1024:
        raise ValueError("invalid pellet config count")
    rows = []
    for _ in range(count):
        values = {}
        while True:
            header = r.take(4)
            if header == b"\xff" * 4:
                break
            key, size = header[:3].decode("ascii"), header[3]
            if key in values:
                raise ValueError("duplicate pellet config parameter")
            if key == "x99" and size == 8:
                length = r.integer()
                if not 0 < length < 1024:
                    raise ValueError("invalid pellet name length")
                values[key] = r.take(length).rstrip(b"\x00").decode("shift_jis")
            elif size == 4:
                values[key] = int.from_bytes(r.take(size), "big", signed=True)
            else:
                raise ValueError("unsupported pellet config parameter")
        model, pellet, unused, repair = r.ident(), r.ident(), r.ident(), r.integer()
        rows.append(dict(model_id=model, pellet_id=pellet, name=values["x99"],
                         kind=values["p00"], color=values["p09"], carry_min=values["p01"],
                         carrier_slots=values["p02"], matching_yield=values["p06"],
                         other_yield=values["p07"]))
    if r.offset != len(data):
        raise ValueError("trailing pellet config bytes")
    return rows


def loose_pellets(data, stage, filename):
    """Read framed GenObjectPellet records separately from Teki/decoration."""
    rows = []
    for match in re.finditer(b"tlep", data):
        start = match.start() - 72
        if start < 20 or data[start + 4:start + 8] != b"0.0v":
            raise ValueError("invalid loose pellet framing")
        r = Reader(data, start)
        r.take(12)
        flags = r.integer()
        r.take(32)
        position, offset = r.floats(3), r.floats(3)
        if r.ident() != "pelt" or r.ident() != "v0.0":
            raise ValueError("unsupported loose pellet version")
        pellet_id = r.ident()
        r.parameters()
        area, area_version = r.ident(), r.ident()
        r.floats(3)
        r.parameters()
        spawn, spawn_version = r.ident(), r.ident()
        params = r.parameters()
        if area_version != "v0.0" or spawn_version != "v0.0" or spawn not in ("1one", "aton", "irnd"):
            raise ValueError("unsupported loose pellet area/spawn version")
        maximum = 1 if spawn == "1one" else param_int(params, "p01" if spawn == "irnd" else "p00", 1)
        minimum = param_int(params, "p00", 1) if spawn == "irnd" else maximum
        rows.append(dict(id=f"{stage}/{filename}@{start}", stage=stage, file=filename,
                         kind="pellet", pellet_id=pellet_id, carry_flags=flags,
                         position=position, count_min=minimum, count_max=maximum,
                         respawn_days=param_int(params, "b00")))
    return rows


def collect(assets):
    facts = audit(assets)
    configs_path = assets / "dataDir/parms/pelMgr.bin"
    config_bytes = configs_path.read_bytes()
    configs = pellet_configs(config_bytes)
    files = {(row["stage"], row["file"]): row for row in facts["files"]}
    records = list(facts["slots"])
    from scripts.audit_enemy_slots import STAGES
    for (stage, filename), file in files.items():
        path = assets / "dataDir/stages" / STAGES[stage] / filename
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != file["sha256"]:
            raise ValueError("generator source changed during audit")
        for row in loose_pellets(data, stage, filename):
            records.append(dict(row, schedule=file["schedule"]))
    result = []
    for row in records:
        result.append(dict(uid=zlib.crc32(("pikrando-spawn/" + row["id"]).encode()),
                           source_record=row["id"], file_sha256=files[row["stage"], row["file"]]["sha256"],
                           stage=row["stage"], kind=row["kind"], species=row.get("species"),
                           pellet_id=row.get("pellet_id"), count_min=row["count_min"],
                           count_max=row["count_max"], respawn_days=row["respawn_days"],
                           carry_flags=row["carry_flags"], schedule=row["schedule"],
                           personality=row.get("personality"), position=row["position"]))
    if len({row["uid"] for row in result}) != len(result):
        raise ValueError("supplier UID collision")
    return dict(version="native-population-inputs-v1", generators=result, configs=configs,
                files=facts["files"], config_sha256=hashlib.sha256(config_bytes).hexdigest(),
                qualification="source/config metadata only; physical hauling and native renewal acceptance pending")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assets", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("preserve old evidence; use a fresh output")
    value = collect(args.assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")
    print(len(value["generators"]), "generators;", len(value["configs"]), "pellet configs")


if __name__ == "__main__":
    main()
