"""Cross-line provider port: cave runtime input builder for the content line.

Lane ``provider-cave-input-builder-content-port`` (issue #642, parent #586).
Implementation owner: Codex through shared account 4laric.

The shared cave runtime input builder
``experimental/pikmin2_cave_runtime_inputs.py`` (with
``tests/test_pikmin2_cave_runtime_inputs.py``) is owned by
``cave-guarded-runtime-fixture`` (#642, done) and exists ONLY on the species
wave line at producer head 74f5a099... It is ABSENT from the content line at
b0d2c08c... (verified) and at 36b86839... (verified), so content P1 lanes
(#154 forest1, #161 yakushima4, #114 tutorial1) cannot stage their guarded
boot input packages without forking shared code.

This module is a self-contained landable packet: it carries the exact
reviewed producer bytes, their git-blob and file hashes, the target content
base, and the downstream consumer refs. It NEVER writes the shared files
itself and never imports the shared module; the integrator applies the bytes
to the shared paths under #642 ownership after review.

Stdlib only. All six runtime gates UNTESTED; no runtime, no build, no ADMIT.
"""

import argparse
import hashlib
import json
import os
import sys

SCHEMA = "p2-cave-input-builder-content-port-1"

PRODUCER = {
    "lane": "cave-guarded-runtime-fixture",
    "issue": 642,
    "line": "species",
    "base": "07e2126ff8c6dacd610958bcba117f3048dbd870",
    "commits": [
        "94770bc7626bac4c8d941908b6873f3e13b5928c",
        "74f5a099038149b36c49ff8cb7d699533b41f997",
    ],
    "head": "74f5a099038149b36c49ff8cb7d699533b41f997",
}

CONTENT_BASE = {
    "ref": "b0d2c08c1ccb8c67f23946241b4b67dcb9ae9f53",
    "also_absent_at": "36b86839",
    "absence_verified": True,
}

DOWNSTREAM = [
    {"lane": "shard-caves-forest-forest1-p1", "issue": 154, "cave": "forest1"},
    {"lane": "shard-caves-yakushima-yakushima4-p1", "issue": 161, "cave": "yakushima4"},
    {"lane": "p2-cave-tutorial_1-p1-runtime", "issue": 114, "cave": "tutorial1"},
]

FILE_BYTES = {
    "experimental/pikmin2_cave_runtime_inputs.py": '"""Reproducible cave runtime input package (lane cave-guarded-runtime-fixture, #642).\n\nBuilds and validates the caller-supplied input package consumed by the shared\nreplacement-main cave boot fixture (native/tools/p2_cave_guarded_boot_fixture.cpp):\n\n  p2-cave-entry.txt          P2_CAVE_ENTRY_1 checkpoint consumed by the integrated\n                             pc_p2_cave_setup path (#129 landing).\n  p2-cave-generate.txt       P2_CAVE_GENERATE_1 floor manifest consumed by the\n                             opt-in pc_p2_cave_generate_run() sidecar.\n  p2-cave-runtime-inputs.json  machine-readable provenance: schema version, cave,\n                             sidecar SHA-256 pins, expected squad/markers, source\n                             pins and consumer commands.\n\nSchema rules mirror the native contracts exactly (pc_p2_cave_entry_policy.h,\npc_port/pc_p2_cave_generate.h, pc_p2_cave.cpp entry reader); validation refuses\nwith the same reason codes the engine would hit, before any runtime is spent.\nStdlib only. No generator/save semantics are invented here.\n"""\n\nimport argparse\nimport hashlib\nimport json\nimport os\nimport sys\n\nSCHEMA = "p2-cave-runtime-inputs-1"\nENTRY_VERSION = "P2_CAVE_ENTRY_1"\nGENERATE_VERSION = "P2_CAVE_GENERATE_1"\n\nHEX32 = set("0123456789abcdef")\n\n\ndef _is_hex(s, length):\n    return isinstance(s, str) and len(s) == length and all(c in HEX32 for c in s)\n\n\ndef _name_ok(s, allow_dollar=False):\n    if not isinstance(s, str) or not s or len(s) > 128:\n        return False\n    for i, c in enumerate(s):\n        ok = ("A" <= c <= "Z") or ("a" <= c <= "z") or ("0" <= c <= "9") or c in "_-."\n        if allow_dollar and c == "$" and i == 0:\n            ok = True\n        if not ok:\n            return False\n    return True\n\n\ndef _finite(v):\n    return isinstance(v, (int, float)) and abs(float(v)) <= 100000.0\n\n\nPRESETS = {\n    # forest1 P1 (#154): floor-1 harness preset. Pool/spawn names are\n    # schema-valid placeholders; the consumer substitutes P0-derived manifests.\n    "forest1": {\n        "token": "a" * 32,\n        "floor": 1,\n        "health": 1.0,\n        "squad": [[1, 1]] * 20,\n        "pool": "forest1-p1-floor1",\n        "units": [["forest1-unit-a", 200.0, 200.0, 0]],\n        "rooms": [[0, 0, 0.0, 0.0, 0.0]],\n        "spawns": [["Bulborb", 3]],\n        "anchor": "hole",\n    },\n    # yakushima4 P1 (#161): floor-1 harness preset (same placeholder policy).\n    "yakushima4": {\n        "token": "b" * 32,\n        "floor": 1,\n        "health": 1.0,\n        "squad": [[1, 1]] * 20,\n        "pool": "yakushima4-p1-floor1",\n        "units": [["yakushima4-unit-a", 240.0, 180.0, 1]],\n        "rooms": [[0, 0, 0.0, 0.0, 0.0]],\n        "spawns": [["DwarfBulborb", 5]],\n        "anchor": "hole",\n    },\n}\n\n\ndef render_entry(preset):\n    lines = ["%s %s %d %.9g %d" % (ENTRY_VERSION, preset["token"], preset["floor"],\n                                   preset["health"], len(preset["squad"]))]\n    for species, maturity in preset["squad"]:\n        lines.append("%d %d" % (species, maturity))\n    return "\\n".join(lines) + "\\n"\n\n\ndef render_generate(preset):\n    units = preset["units"]\n    rooms = preset["rooms"]\n    out = [GENERATE_VERSION]\n    out.append("pool %s %d" % (preset["pool"], len(units)))\n    for i, (name, w, d, kind) in enumerate(units):\n        out.append("unit %d %s %.3f %.3f %d" % (i, name, w, d, kind))\n    out.append("rooms %d" % len(rooms))\n    for i, (unit, turn, ox, oy, oz) in enumerate(rooms):\n        out.append("room %d %d %d %.3f %.3f %.3f" % (i, unit, turn, ox, oy, oz))\n    out.append("doors 0")\n    out.append("links 0")\n    out.append("spawns %d" % len(preset["spawns"]))\n    for sid, count in preset["spawns"]:\n        out.append("spawn %s %d" % (sid, count))\n    out.append("anchor %s" % preset["anchor"])\n    return "\\n".join(out) + "\\n"\n\n\ndef sha256_bytes(data):\n    return hashlib.sha256(data).hexdigest()\n\n\ndef build_package(outdir, cave, pins):\n    """Write the three package files. Returns the provenance dict."""\n    if cave not in PRESETS:\n        raise ValueError("unknown cave preset: %r" % cave)\n    preset = PRESETS[cave]\n    os.makedirs(outdir, exist_ok=True)\n    entry = render_entry(preset).encode("utf-8")\n    generate = render_generate(preset).encode("utf-8")\n    with open(os.path.join(outdir, "p2-cave-entry.txt"), "wb") as f:\n        f.write(entry)\n    with open(os.path.join(outdir, "p2-cave-generate.txt"), "wb") as f:\n        f.write(generate)\n    provenance = {\n        "schema": SCHEMA,\n        "cave": cave,\n        "entry": {"file": "p2-cave-entry.txt", "sha256": sha256_bytes(entry),\n                  "version": ENTRY_VERSION, "floor": preset["floor"],\n                  "survivors": len(preset["squad"])},\n        "generate": {"file": "p2-cave-generate.txt", "sha256": sha256_bytes(generate),\n                     "version": GENERATE_VERSION, "pool": preset["pool"],\n                     "anchor": preset["anchor"]},\n        "expected_markers": ["P2_CAVE_READY", "P2_CAVE_GUARDED_ENTRY_READY",\n                             "P2_CAVE_GENERATE_PASS", "P2_CAVE_GUARDED_BOOT_PASS",\n                             "PASS CAVE_GUARDED_BOOT"],\n        "source_pins": pins,\n    }\n    with open(os.path.join(outdir, "p2-cave-runtime-inputs.json"), "w", encoding="utf-8") as f:\n        json.dump(provenance, f, indent=2)\n        f.write("\\n")\n    return provenance\n\n\ndef _read_text(path):\n    with open(path, encoding="utf-8") as f:\n        return f.read()\n\n\ndef validate_package(outdir):\n    """Return a list of refusal reasons (empty means the package is valid)."""\n    problems = []\n    try:\n        entry_text = _read_text(os.path.join(outdir, "p2-cave-entry.txt"))\n    except OSError:\n        return ["missing-entry-file"]\n    try:\n        generate_text = _read_text(os.path.join(outdir, "p2-cave-generate.txt"))\n    except OSError:\n        return ["missing-generate-file"]\n    try:\n        provenance = json.loads(_read_text(os.path.join(outdir, "p2-cave-runtime-inputs.json")))\n    except (OSError, ValueError):\n        return ["missing-or-bad-provenance"]\n    if provenance.get("schema") != SCHEMA:\n        problems.append("bad-provenance-schema")\n    # --- entry checks (mirror pc_p2_cave.cpp reader + entry policy) ---\n    tokens = entry_text.split()\n    if len(tokens) < 5:\n        problems.append("entry-header")\n    else:\n        version, token, floor_s, health_s, count_s = tokens[:5]\n        try:\n            floor, count, health = int(floor_s), int(count_s), float(health_s)\n        except ValueError:\n            problems.append("entry-header")\n            floor, count, health = None, None, None\n        if version != ENTRY_VERSION:\n            problems.append("entry-version")\n        if not _is_hex(token, 32):\n            problems.append("entry-token")\n        if floor not in (1, 2):\n            problems.append("entry-floor")\n        if not (isinstance(health, float) and 0 < health <= 1):\n            problems.append("entry-health")\n        if not (isinstance(count, int) and 1 <= count <= 100):\n            problems.append("entry-count")\n        else:\n            rest = tokens[5:]\n            if len(rest) != count * 2:\n                problems.append("entry-count-mismatch")\n            else:\n                for i in range(count):\n                    try:\n                        species, maturity = int(rest[2 * i]), int(rest[2 * i + 1])\n                    except ValueError:\n                        problems.append("entry-survivor-%d" % i)\n                        break\n                    if not (0 <= species <= 5 and 0 <= maturity <= 2):\n                        problems.append("entry-survivor-%d" % i)\n                        break\n    # --- generate checks (mirror pc_p2_cave_generate.h readManifest) ---\n    words = generate_text.split()\n    pos = [0]\n\n    def want(word):\n        if pos[0] >= len(words) or words[pos[0]] != word:\n            return False\n        pos[0] += 1\n        return True\n\n    def take_int():\n        if pos[0] >= len(words):\n            return None\n        try:\n            value = int(words[pos[0]])\n        except ValueError:\n            return None\n        pos[0] += 1\n        return value\n\n    def take_num():\n        if pos[0] >= len(words):\n            return None\n        try:\n            value = float(words[pos[0]])\n        except ValueError:\n            return None\n        pos[0] += 1\n        return value\n\n    def take_str():\n        if pos[0] >= len(words):\n            return None\n        value = words[pos[0]]\n        pos[0] += 1\n        return value\n\n    ok = want(GENERATE_VERSION) and want("pool")\n    pool = take_str()\n    nunits = take_int()\n    if not (ok and _name_ok(pool) and isinstance(nunits, int) and 1 <= nunits <= 64):\n        problems.append("generate-pool")\n        nunits = 0\n    for i in range(nunits or 0):\n        if not want("unit"):\n            problems.append("generate-unit-%d" % i)\n            break\n        idx, name = take_int(), take_str()\n        w, d, kind = take_num(), take_num(), take_int()\n        if not (idx == i and _name_ok(name)\n                and isinstance(w, float) and isinstance(d, float) and w > 0 and d > 0\n                and _finite(w) and _finite(d)\n                and isinstance(kind, int) and 0 <= kind <= 255):\n            problems.append("generate-unit-%d" % i)\n            break\n    nrooms = take_int() if want("rooms") else None\n    if not (isinstance(nrooms, int) and 1 <= nrooms <= 256):\n        problems.append("generate-rooms")\n        nrooms = 0\n    for i in range(nrooms or 0):\n        if not want("room"):\n            problems.append("generate-room-%d" % i)\n            break\n        ridx, unit, turn = take_int(), take_int(), take_int()\n        ox, oy, oz = take_num(), take_num(), take_num()\n        if not (ridx == i and isinstance(unit, int) and 0 <= unit < (nunits or 0)\n                and isinstance(turn, int) and 0 <= turn <= 3\n                and all(isinstance(v, float) and _finite(v) for v in (ox, oy, oz))):\n            problems.append("generate-room-%d" % i)\n            break\n    ndoors = take_int() if want("doors") else None\n    if not (isinstance(ndoors, int) and 0 <= ndoors <= 4096):\n        problems.append("generate-doors")\n    else:\n        for i in range(ndoors):\n            if not want("door"):\n                problems.append("generate-door-%d" % i)\n                break\n            unit, did, direction = take_int(), take_int(), take_int()\n            if not (isinstance(unit, int) and 0 <= unit < (nunits or 0)\n                    and isinstance(did, int) and 0 <= did <= 1024\n                    and isinstance(direction, int) and 0 <= direction <= 3):\n                problems.append("generate-door-%d" % i)\n                break\n    nlinks = take_int() if want("links") else None\n    if not (isinstance(nlinks, int) and 0 <= nlinks <= 4096):\n        problems.append("generate-links")\n    else:\n        for i in range(nlinks):\n            if not want("link"):\n                problems.append("generate-link-%d" % i)\n                break\n            vals = [take_int(), take_int(), take_int(), take_int()]\n            dist = take_num()\n            if not (all(isinstance(v, int) for v in vals) and vals[0] >= 0 and vals[2] >= 0\n                    and isinstance(dist, float) and dist >= 0 and _finite(dist)):\n                problems.append("generate-link-%d" % i)\n                break\n    nspawns = take_int() if want("spawns") else None\n    if not (isinstance(nspawns, int) and 1 <= nspawns <= 256):\n        problems.append("generate-spawns")\n    else:\n        for i in range(nspawns):\n            if not want("spawn"):\n                problems.append("generate-spawn-%d" % i)\n                break\n            sid, count = take_str(), take_int()\n            if not (_name_ok(sid, allow_dollar=True) and isinstance(count, int)\n                    and 1 <= count <= 10000):\n                problems.append("generate-spawn-%d" % i)\n                break\n    anchor = take_str() if want("anchor") else None\n    if anchor not in ("hole", "geyser"):\n        problems.append("generate-anchor")\n    if pos[0] != len(words):\n        problems.append("generate-trailing-data")\n    # --- provenance hash check ---\n    entry_rec = provenance.get("entry", {})\n    generate_rec = provenance.get("generate", {})\n    if entry_rec.get("sha256") != sha256_bytes(entry_text.encode("utf-8")):\n        problems.append("provenance-entry-hash-mismatch")\n    if generate_rec.get("sha256") != sha256_bytes(generate_text.encode("utf-8")):\n        problems.append("provenance-generate-hash-mismatch")\n    return problems\n\n\ndef main(argv=None):\n    parser = argparse.ArgumentParser(description="Build/validate cave runtime input packages")\n    sub = parser.add_subparsers(dest="command", required=True)\n    build = sub.add_parser("build", help="write a preset package")\n    build.add_argument("--cave", choices=sorted(PRESETS), required=True)\n    build.add_argument("--out", required=True)\n    build.add_argument("--pins", default="{}",\n                       help="JSON object of source pins recorded into provenance")\n    validate = sub.add_parser("validate", help="validate a package directory")\n    validate.add_argument("--dir", required=True)\n    args = parser.parse_args(argv)\n    if args.command == "build":\n        try:\n            pins = json.loads(args.pins)\n        except ValueError as exc:\n            print("bad --pins JSON: %s" % exc)\n            return 2\n        try:\n            provenance = build_package(args.out, args.cave, pins)\n        except ValueError as exc:\n            print("refused: %s" % exc)\n            return 2\n        print("package cave=%s entry=%s generate=%s" % (\n            args.cave, provenance["entry"]["sha256"][:16],\n            provenance["generate"]["sha256"][:16]))\n        return 0\n    problems = validate_package(args.dir)\n    if problems:\n        for problem in problems:\n            print("REFUSED reason=%s" % problem)\n        return 1\n    print("INPUTS_PASS dir=%s" % args.dir)\n    return 0\n\n\nif __name__ == "__main__":\n    sys.exit(main())',
    "tests/test_pikmin2_cave_runtime_inputs.py": '"""Focused tests for experimental/pikmin2_cave_runtime_inputs.py (#642).\n\nValid packages validate clean; every mismatch class is refused with an exact\nreason. No engine, no assets, no display needed.\n"""\n\nimport json\nimport os\nimport shutil\nimport sys\nimport tempfile\nimport unittest\n\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))\n\nfrom pikmin2_cave_runtime_inputs import build_package, validate_package, PRESETS\n\n\nPINS = {"root": "07e2126f", "native": "9688995e", "guard": "d2f678c9"}\n\n\nclass CaveRuntimeInputsTest(unittest.TestCase):\n    def setUp(self):\n        self.tmp = tempfile.mkdtemp(prefix="cave-inputs-")\n        self.addCleanup(shutil.rmtree, self.tmp, True)\n\n    def pkg(self, cave="forest1"):\n        outdir = os.path.join(self.tmp, cave)\n        build_package(outdir, cave, PINS)\n        return outdir\n\n    def rewrite(self, outdir, name, text):\n        with open(os.path.join(outdir, name), "w", encoding="utf-8") as f:\n            f.write(text)\n\n    def test_forest1_valid(self):\n        outdir = self.pkg("forest1")\n        self.assertEqual(validate_package(outdir), [])\n        provenance = json.load(open(os.path.join(outdir, "p2-cave-runtime-inputs.json"),\n                                    encoding="utf-8"))\n        self.assertEqual(provenance["schema"], "p2-cave-runtime-inputs-1")\n        self.assertEqual(provenance["cave"], "forest1")\n        self.assertEqual(provenance["entry"]["survivors"], 20)\n        self.assertEqual(provenance["source_pins"], PINS)\n        self.assertIn("P2_CAVE_GUARDED_BOOT_PASS", provenance["expected_markers"])\n\n    def test_yakushima4_valid(self):\n        outdir = self.pkg("yakushima4")\n        self.assertEqual(validate_package(outdir), [])\n        provenance = json.load(open(os.path.join(outdir, "p2-cave-runtime-inputs.json"),\n                                    encoding="utf-8"))\n        self.assertEqual(provenance["cave"], "yakushima4")\n\n    def test_presets_differ(self):\n        self.assertNotEqual(PRESETS["forest1"]["token"], PRESETS["yakushima4"]["token"])\n        self.assertNotEqual(PRESETS["forest1"]["pool"], PRESETS["yakushima4"]["pool"])\n\n    def test_unknown_cave_refused(self):\n        with self.assertRaises(ValueError):\n            build_package(os.path.join(self.tmp, "nope"), "no-such-cave", PINS)\n\n    def test_missing_files(self):\n        self.assertEqual(validate_package(os.path.join(self.tmp, "absent")),\n                         ["missing-entry-file"])\n        outdir = self.pkg()\n        os.remove(os.path.join(outdir, "p2-cave-generate.txt"))\n        self.assertEqual(validate_package(outdir), ["missing-generate-file"])\n        outdir = self.pkg()\n        os.remove(os.path.join(outdir, "p2-cave-runtime-inputs.json"))\n        self.assertEqual(validate_package(outdir), ["missing-or-bad-provenance"])\n\n    def test_bad_entry_header(self):\n        outdir = self.pkg()\n        self.rewrite(outdir, "p2-cave-entry.txt", "P2_CAVE_ENTRY_9 %s 1 1.0 20\\n" % ("a" * 32))\n        self.assertIn("entry-version", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-entry.txt",\n                     "P2_CAVE_ENTRY_1 NOTHEX 1 1.0 1\\n1 1\\n")\n        self.assertIn("entry-token", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-entry.txt",\n                     "P2_CAVE_ENTRY_1 %s 5 1.0 1\\n1 1\\n" % ("a" * 32))\n        self.assertIn("entry-floor", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-entry.txt",\n                     "P2_CAVE_ENTRY_1 %s 1 1.0 3\\n1 1\\n1 1\\n" % ("a" * 32))\n        self.assertIn("entry-count-mismatch", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-entry.txt",\n                     "P2_CAVE_ENTRY_1 %s 1 1.0 1\\n9 9\\n" % ("a" * 32))\n        self.assertIn("entry-survivor-0", validate_package(outdir))\n\n    def test_bad_generate_manifest(self):\n        outdir = self.pkg()\n        entry = open(os.path.join(outdir, "p2-cave-entry.txt"), encoding="utf-8").read()\n        self.rewrite(outdir, "p2-cave-generate.txt", "P2_CAVE_GENERATE_9\\n")\n        self.assertIn("generate-pool", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-generate.txt",\n                     "P2_CAVE_GENERATE_1\\npool x 1\\nunit 0 x -5 5 0\\nrooms 1\\n"\n                     "room 0 0 0 0 0 0\\ndoors 0\\nlinks 0\\nspawns 1\\nspawn Bulborb 1\\nanchor hole\\n")\n        self.assertIn("generate-unit-0", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-generate.txt",\n                     "P2_CAVE_GENERATE_1\\npool x 1\\nunit 0 x 5 5 0\\nrooms 1\\n"\n                     "room 0 0 0 0 0 0\\ndoors 0\\nlinks 0\\nspawns 1\\nspawn Bulborb 1\\nanchor lake\\n")\n        self.assertIn("generate-anchor", validate_package(outdir))\n        self.rewrite(outdir, "p2-cave-generate.txt",\n                     "P2_CAVE_GENERATE_1\\npool x 1\\nunit 0 x 5 5 0\\nrooms 1\\n"\n                     "room 0 0 0 0 0 0\\ndoors 0\\nlinks 0\\nspawns 1\\nspawn Bulborb 1\\nanchor hole\\nEXTRA\\n")\n        self.assertIn("generate-trailing-data", validate_package(outdir))\n        # entry file untouched throughout\n        self.assertEqual(open(os.path.join(outdir, "p2-cave-entry.txt"),\n                              encoding="utf-8").read(), entry)\n\n    def test_provenance_hash_mismatch(self):\n        outdir = self.pkg()\n        with open(os.path.join(outdir, "p2-cave-generate.txt"), "a", encoding="utf-8") as f:\n            f.write("# tampered\\n")\n        problems = validate_package(outdir)\n        self.assertIn("provenance-generate-hash-mismatch", problems)\n\n    def test_bad_provenance_schema(self):\n        outdir = self.pkg()\n        path = os.path.join(outdir, "p2-cave-runtime-inputs.json")\n        provenance = json.load(open(path, encoding="utf-8"))\n        provenance["schema"] = "something-else-9"\n        json.dump(provenance, open(path, "w", encoding="utf-8"))\n        self.assertIn("bad-provenance-schema", validate_package(outdir))\n\n\nif __name__ == "__main__":\n    unittest.main()',
}

FILE_META = {
    "experimental/pikmin2_cave_runtime_inputs.py": {
        "blob": "b9fa6c994bf5650b4b334f2428259739be90de1e",
        "sha256": "f44fcfd1e59fe7b0c69249eae68cd54ba95eb0d2b9de624b0f97206e60d3fc77",
        "mode": "100644",
    },
    "tests/test_pikmin2_cave_runtime_inputs.py": {
        "blob": "a221b7559ed82e531c5268229c0c699b6be3f1d7",
        "sha256": "81e96100e83e1e56969915b8404c29a8fdb40c6afa92bf36b4bdc644d110bd7f",
        "mode": "100644",
    },
}

HEX40 = set("0123456789abcdef")


def _is_hex(s, length):
    return isinstance(s, str) and len(s) == length and all(c in HEX40 for c in s)


def expected_sha256(path):
    """Recorded file hash for a packet path; KeyError on unknown path."""
    return FILE_META[path]["sha256"]


def expected_blob(path):
    """Recorded git blob hash for a packet path; KeyError on unknown path."""
    return FILE_META[path]["blob"]


def packet_bytes(path):
    """Exact carried bytes for a packet path; KeyError on unknown path."""
    data = FILE_BYTES[path].encode("utf-8")
    if not data:
        raise ValueError("empty packet bytes: %r" % path)
    return data


def verify_bytes(path, data):
    """Return refusal reasons for candidate bytes (empty means match)."""
    if path not in FILE_META:
        return ["unknown-file"]
    if not isinstance(data, (bytes, bytearray)):
        return ["not-bytes"]
    if not data:
        return ["empty-bytes"]
    if hashlib.sha256(bytes(data)).hexdigest() != FILE_META[path]["sha256"]:
        return ["hash-mismatch"]
    return []


def verify_packet_self():
    """Check the carried bytes against the recorded hashes."""
    problems = []
    for path in FILE_META:
        try:
            data = packet_bytes(path)
        except (KeyError, ValueError) as exc:
            problems.append("self-bytes-%s" % exc)
            continue
        for reason in verify_bytes(path, data):
            problems.append("%s:%s" % (path, reason))
    return problems


def verify_producer_tree(rootdir):
    """Check an on-disk producer checkout carries the recorded bytes."""
    problems = []
    for path in FILE_META:
        full = os.path.join(rootdir, *path.split("/"))
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            problems.append("missing-file:%s" % path)
            continue
        for reason in verify_bytes(path, data):
            problems.append("%s:%s" % (path, reason))
    return problems


def emit_packet(outdir):
    """Write packet.json plus exact file copies into a private directory.

    Never writes repository shared paths; the integrator applies the copies
    under #642 ownership after review.
    """
    if not isinstance(outdir, str) or not outdir:
        raise ValueError("refused: empty output directory")
    files_dir = os.path.join(outdir, "packet-files")
    os.makedirs(files_dir, exist_ok=True)
    for path in FILE_META:
        data = packet_bytes(path)
        dest = os.path.join(files_dir, *path.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
    packet = {
        "schema": SCHEMA,
        "producer": PRODUCER,
        "content_base": CONTENT_BASE,
        "files": {
            path: {
                "mode": FILE_META[path]["mode"],
                "blob": FILE_META[path]["blob"],
                "sha256": FILE_META[path]["sha256"],
                "size": len(packet_bytes(path)),
            }
            for path in FILE_META
        },
        "downstream": DOWNSTREAM,
        "gates": "all six runtime gates UNTESTED; no runtime, no build, no ADMIT",
    }
    with open(os.path.join(outdir, "packet.json"), "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)
        f.write("\n")
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify/emit the cave input builder content port")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="verify carried or on-disk producer bytes")
    verify.add_argument("--self", action="store_true", help="verify embedded bytes")
    verify.add_argument("--producer-root", default=None, help="producer checkout to check")
    emit = sub.add_parser("emit", help="emit the landable packet")
    emit.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "verify":
        if args.self:
            problems = verify_packet_self()
            if problems:
                for problem in problems:
                    print("REFUSED reason=%s" % problem)
                return 1
            print("SELF_PASS files=%d" % len(FILE_META))
            return 0
        if not args.producer_root:
            print("refused: --self or --producer-root required")
            return 2
        problems = verify_producer_tree(args.producer_root)
        if problems:
            for problem in problems:
                print("REFUSED reason=%s" % problem)
            return 1
        print("PRODUCER_PASS root=%s" % args.producer_root)
        return 0
    packet = emit_packet(args.out)
    print("PACKET_EMITTED dir=%s files=%d downstream=%s" % (
        args.out, len(packet["files"]),
        ",".join(str(d["issue"]) for d in packet["downstream"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
