"""Reproducible cave runtime input package (lane cave-guarded-runtime-fixture, #642).

Builds and validates the caller-supplied input package consumed by the shared
replacement-main cave boot fixture (native/tools/p2_cave_guarded_boot_fixture.cpp):

  p2-cave-entry.txt          P2_CAVE_ENTRY_1 checkpoint consumed by the integrated
                             pc_p2_cave_setup path (#129 landing).
  p2-cave-generate.txt       P2_CAVE_GENERATE_1 floor manifest consumed by the
                             opt-in pc_p2_cave_generate_run() sidecar.
  p2-cave-runtime-inputs.json  machine-readable provenance: schema version, cave,
                             sidecar SHA-256 pins, expected squad/markers, source
                             pins and consumer commands.

Schema rules mirror the native contracts exactly (pc_p2_cave_entry_policy.h,
pc_port/pc_p2_cave_generate.h, pc_p2_cave.cpp entry reader); validation refuses
with the same reason codes the engine would hit, before any runtime is spent.
Stdlib only. No generator/save semantics are invented here.
"""

import argparse
import hashlib
import json
import os
import sys

SCHEMA = "p2-cave-runtime-inputs-1"
ENTRY_VERSION = "P2_CAVE_ENTRY_1"
GENERATE_VERSION = "P2_CAVE_GENERATE_1"

HEX32 = set("0123456789abcdef")


def _is_hex(s, length):
    return isinstance(s, str) and len(s) == length and all(c in HEX32 for c in s)


def _name_ok(s, allow_dollar=False):
    if not isinstance(s, str) or not s or len(s) > 128:
        return False
    for i, c in enumerate(s):
        ok = ("A" <= c <= "Z") or ("a" <= c <= "z") or ("0" <= c <= "9") or c in "_-."
        if allow_dollar and c == "$" and i == 0:
            ok = True
        if not ok:
            return False
    return True


def _finite(v):
    return isinstance(v, (int, float)) and abs(float(v)) <= 100000.0


PRESETS = {
    # forest1 P1 (#154): floor-1 harness preset. Pool/spawn names are
    # schema-valid placeholders; the consumer substitutes P0-derived manifests.
    "forest1": {
        "token": "a" * 32,
        "floor": 1,
        "health": 1.0,
        "squad": [[1, 1]] * 20,
        "pool": "forest1-p1-floor1",
        "units": [["forest1-unit-a", 200.0, 200.0, 0]],
        "rooms": [[0, 0, 0.0, 0.0, 0.0]],
        "spawns": [["Bulborb", 3]],
        "anchor": "hole",
    },
    # yakushima4 P1 (#161): floor-1 harness preset (same placeholder policy).
    "yakushima4": {
        "token": "b" * 32,
        "floor": 1,
        "health": 1.0,
        "squad": [[1, 1]] * 20,
        "pool": "yakushima4-p1-floor1",
        "units": [["yakushima4-unit-a", 240.0, 180.0, 1]],
        "rooms": [[0, 0, 0.0, 0.0, 0.0]],
        "spawns": [["DwarfBulborb", 5]],
        "anchor": "hole",
    },
}


def render_entry(preset):
    lines = ["%s %s %d %.9g %d" % (ENTRY_VERSION, preset["token"], preset["floor"],
                                   preset["health"], len(preset["squad"]))]
    for species, maturity in preset["squad"]:
        lines.append("%d %d" % (species, maturity))
    return "\n".join(lines) + "\n"


def render_generate(preset):
    units = preset["units"]
    rooms = preset["rooms"]
    out = [GENERATE_VERSION]
    out.append("pool %s %d" % (preset["pool"], len(units)))
    for i, (name, w, d, kind) in enumerate(units):
        out.append("unit %d %s %.3f %.3f %d" % (i, name, w, d, kind))
    out.append("rooms %d" % len(rooms))
    for i, (unit, turn, ox, oy, oz) in enumerate(rooms):
        out.append("room %d %d %d %.3f %.3f %.3f" % (i, unit, turn, ox, oy, oz))
    out.append("doors 0")
    out.append("links 0")
    out.append("spawns %d" % len(preset["spawns"]))
    for sid, count in preset["spawns"]:
        out.append("spawn %s %d" % (sid, count))
    out.append("anchor %s" % preset["anchor"])
    return "\n".join(out) + "\n"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def build_package(outdir, cave, pins):
    """Write the three package files. Returns the provenance dict."""
    if cave not in PRESETS:
        raise ValueError("unknown cave preset: %r" % cave)
    preset = PRESETS[cave]
    os.makedirs(outdir, exist_ok=True)
    entry = render_entry(preset).encode("utf-8")
    generate = render_generate(preset).encode("utf-8")
    with open(os.path.join(outdir, "p2-cave-entry.txt"), "wb") as f:
        f.write(entry)
    with open(os.path.join(outdir, "p2-cave-generate.txt"), "wb") as f:
        f.write(generate)
    provenance = {
        "schema": SCHEMA,
        "cave": cave,
        "entry": {"file": "p2-cave-entry.txt", "sha256": sha256_bytes(entry),
                  "version": ENTRY_VERSION, "floor": preset["floor"],
                  "survivors": len(preset["squad"])},
        "generate": {"file": "p2-cave-generate.txt", "sha256": sha256_bytes(generate),
                     "version": GENERATE_VERSION, "pool": preset["pool"],
                     "anchor": preset["anchor"]},
        "expected_markers": ["P2_CAVE_READY", "P2_CAVE_GUARDED_ENTRY_READY",
                             "P2_CAVE_GENERATE_PASS", "P2_CAVE_GUARDED_BOOT_PASS",
                             "PASS CAVE_GUARDED_BOOT"],
        "source_pins": pins,
    }
    with open(os.path.join(outdir, "p2-cave-runtime-inputs.json"), "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
        f.write("\n")
    return provenance


def _read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def validate_package(outdir):
    """Return a list of refusal reasons (empty means the package is valid)."""
    problems = []
    try:
        entry_text = _read_text(os.path.join(outdir, "p2-cave-entry.txt"))
    except OSError:
        return ["missing-entry-file"]
    try:
        generate_text = _read_text(os.path.join(outdir, "p2-cave-generate.txt"))
    except OSError:
        return ["missing-generate-file"]
    try:
        provenance = json.loads(_read_text(os.path.join(outdir, "p2-cave-runtime-inputs.json")))
    except (OSError, ValueError):
        return ["missing-or-bad-provenance"]
    if provenance.get("schema") != SCHEMA:
        problems.append("bad-provenance-schema")
    # --- entry checks (mirror pc_p2_cave.cpp reader + entry policy) ---
    tokens = entry_text.split()
    if len(tokens) < 5:
        problems.append("entry-header")
    else:
        version, token, floor_s, health_s, count_s = tokens[:5]
        try:
            floor, count, health = int(floor_s), int(count_s), float(health_s)
        except ValueError:
            problems.append("entry-header")
            floor, count, health = None, None, None
        if version != ENTRY_VERSION:
            problems.append("entry-version")
        if not _is_hex(token, 32):
            problems.append("entry-token")
        if floor not in (1, 2):
            problems.append("entry-floor")
        if not (isinstance(health, float) and 0 < health <= 1):
            problems.append("entry-health")
        if not (isinstance(count, int) and 1 <= count <= 100):
            problems.append("entry-count")
        else:
            rest = tokens[5:]
            if len(rest) != count * 2:
                problems.append("entry-count-mismatch")
            else:
                for i in range(count):
                    try:
                        species, maturity = int(rest[2 * i]), int(rest[2 * i + 1])
                    except ValueError:
                        problems.append("entry-survivor-%d" % i)
                        break
                    if not (0 <= species <= 5 and 0 <= maturity <= 2):
                        problems.append("entry-survivor-%d" % i)
                        break
    # --- generate checks (mirror pc_p2_cave_generate.h readManifest) ---
    words = generate_text.split()
    pos = [0]

    def want(word):
        if pos[0] >= len(words) or words[pos[0]] != word:
            return False
        pos[0] += 1
        return True

    def take_int():
        if pos[0] >= len(words):
            return None
        try:
            value = int(words[pos[0]])
        except ValueError:
            return None
        pos[0] += 1
        return value

    def take_num():
        if pos[0] >= len(words):
            return None
        try:
            value = float(words[pos[0]])
        except ValueError:
            return None
        pos[0] += 1
        return value

    def take_str():
        if pos[0] >= len(words):
            return None
        value = words[pos[0]]
        pos[0] += 1
        return value

    ok = want(GENERATE_VERSION) and want("pool")
    pool = take_str()
    nunits = take_int()
    if not (ok and _name_ok(pool) and isinstance(nunits, int) and 1 <= nunits <= 64):
        problems.append("generate-pool")
        nunits = 0
    for i in range(nunits or 0):
        if not want("unit"):
            problems.append("generate-unit-%d" % i)
            break
        idx, name = take_int(), take_str()
        w, d, kind = take_num(), take_num(), take_int()
        if not (idx == i and _name_ok(name)
                and isinstance(w, float) and isinstance(d, float) and w > 0 and d > 0
                and _finite(w) and _finite(d)
                and isinstance(kind, int) and 0 <= kind <= 255):
            problems.append("generate-unit-%d" % i)
            break
    nrooms = take_int() if want("rooms") else None
    if not (isinstance(nrooms, int) and 1 <= nrooms <= 256):
        problems.append("generate-rooms")
        nrooms = 0
    for i in range(nrooms or 0):
        if not want("room"):
            problems.append("generate-room-%d" % i)
            break
        ridx, unit, turn = take_int(), take_int(), take_int()
        ox, oy, oz = take_num(), take_num(), take_num()
        if not (ridx == i and isinstance(unit, int) and 0 <= unit < (nunits or 0)
                and isinstance(turn, int) and 0 <= turn <= 3
                and all(isinstance(v, float) and _finite(v) for v in (ox, oy, oz))):
            problems.append("generate-room-%d" % i)
            break
    ndoors = take_int() if want("doors") else None
    if not (isinstance(ndoors, int) and 0 <= ndoors <= 4096):
        problems.append("generate-doors")
    else:
        for i in range(ndoors):
            if not want("door"):
                problems.append("generate-door-%d" % i)
                break
            unit, did, direction = take_int(), take_int(), take_int()
            if not (isinstance(unit, int) and 0 <= unit < (nunits or 0)
                    and isinstance(did, int) and 0 <= did <= 1024
                    and isinstance(direction, int) and 0 <= direction <= 3):
                problems.append("generate-door-%d" % i)
                break
    nlinks = take_int() if want("links") else None
    if not (isinstance(nlinks, int) and 0 <= nlinks <= 4096):
        problems.append("generate-links")
    else:
        for i in range(nlinks):
            if not want("link"):
                problems.append("generate-link-%d" % i)
                break
            vals = [take_int(), take_int(), take_int(), take_int()]
            dist = take_num()
            if not (all(isinstance(v, int) for v in vals) and vals[0] >= 0 and vals[2] >= 0
                    and isinstance(dist, float) and dist >= 0 and _finite(dist)):
                problems.append("generate-link-%d" % i)
                break
    nspawns = take_int() if want("spawns") else None
    if not (isinstance(nspawns, int) and 1 <= nspawns <= 256):
        problems.append("generate-spawns")
    else:
        for i in range(nspawns):
            if not want("spawn"):
                problems.append("generate-spawn-%d" % i)
                break
            sid, count = take_str(), take_int()
            if not (_name_ok(sid, allow_dollar=True) and isinstance(count, int)
                    and 1 <= count <= 10000):
                problems.append("generate-spawn-%d" % i)
                break
    anchor = take_str() if want("anchor") else None
    if anchor not in ("hole", "geyser"):
        problems.append("generate-anchor")
    if pos[0] != len(words):
        problems.append("generate-trailing-data")
    # --- provenance hash check ---
    entry_rec = provenance.get("entry", {})
    generate_rec = provenance.get("generate", {})
    if entry_rec.get("sha256") != sha256_bytes(entry_text.encode("utf-8")):
        problems.append("provenance-entry-hash-mismatch")
    if generate_rec.get("sha256") != sha256_bytes(generate_text.encode("utf-8")):
        problems.append("provenance-generate-hash-mismatch")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build/validate cave runtime input packages")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="write a preset package")
    build.add_argument("--cave", choices=sorted(PRESETS), required=True)
    build.add_argument("--out", required=True)
    build.add_argument("--pins", default="{}",
                       help="JSON object of source pins recorded into provenance")
    validate = sub.add_parser("validate", help="validate a package directory")
    validate.add_argument("--dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        try:
            pins = json.loads(args.pins)
        except ValueError as exc:
            print("bad --pins JSON: %s" % exc)
            return 2
        try:
            provenance = build_package(args.out, args.cave, pins)
        except ValueError as exc:
            print("refused: %s" % exc)
            return 2
        print("package cave=%s entry=%s generate=%s" % (
            args.cave, provenance["entry"]["sha256"][:16],
            provenance["generate"]["sha256"][:16]))
        return 0
    problems = validate_package(args.dir)
    if problems:
        for problem in problems:
            print("REFUSED reason=%s" % problem)
        return 1
    print("INPUTS_PASS dir=%s" % args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())