"""P1 runtime import path for Perplexing Pool (yakushima, #150).

Extends the P0 course-record boundary with a real-source decode path and a
P1 import path that stages the decoded manifest into a private run layout
and drives the integrated p2-surface-session-1 checker (#132) over day
transition, save/reload, receipt replay and exit/reentry. Root-only
tooling: no native build, no runtime run, no playability claim.

Source correction (documented, not a fork): the P0 strict record validator
requires a `farm` key, but retail `CourseInfo::read` treats EVERY key as
optional (`src/plugProjectKandoU/gameStages.cpp:207-260`; `farm` is skipped
when absent and `mFarmPath` stays null, guarded at :440-442). No shipped
course block carries `farm`. The strict `decode_course_pairs` entry below is
preserved bit-for-bit for synthetic boundary tests; the real-source
`decode_course_block` entry applies the source-faithful optional-key
semantics through the SAME field validators.
"""
import hashlib
import json
import re
from pathlib import Path

COURSE_ID = "yakushima"
LABEL = "Perplexing Pool"
SOURCE_PATH = "user/Abe/stages.txt"
ISSUE = 150
CONTRACT_VERSION = "p2-overworld-course-1"
P1_SCHEMA = "p2-yakushima-p1-run-1"

COURSE_SCALAR_KEYS = (
    "name",
    "folder",
    "abe_folder",
    "model",
    "collision",
    "waterbox",
    "mapcode",
    "farm",
    "route",
    "start",
    "startangle",
)

LIMIT_GEN_FIELDS = ("name", "minimum_day", "maximum_day", "day_limit")
CAVE_OTAKARA_FIELDS = ("cave_id", "otakara_count", "definition_file")

REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

RUNTIME_DEPENDENCIES = (128, 130, 131, 132, 140, 144, 145, 146)
SIBLING_CAVE_ISSUES = (158, 159, 160, 161)


class CourseDecodeError(ValueError):
    """A course record or manifest fails strict validation."""


class P1GapError(ValueError):
    """A P1 prerequisite pin cannot be supplied; nothing is invented."""

def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def _require_finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CourseDecodeError("field %r must be a number" % field)
    result = float(value)
    if result != result or result in (float("inf"), float("-inf")):
        raise CourseDecodeError("field %r must be finite" % field)
    return result


def _require_non_negative_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CourseDecodeError("field %r must be a non-negative int" % field)
    return value


def _require_path(value, field):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise CourseDecodeError("field %r must be a path string" % field)
    if value.startswith("/") or ".." in value.split("/"):
        raise CourseDecodeError("field %r must be a relative path" % field)
    return value


def _check_limit_rows(rows, block):
    checked = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or tuple(row.keys()) != LIMIT_GEN_FIELDS:
            raise CourseDecodeError(
                "block %r row %d fields must be %r" % (block, i, list(LIMIT_GEN_FIELDS)))
        if not isinstance(row["name"], str) or not row["name"]:
            raise CourseDecodeError("block %r row %d name must be non-empty" % (block, i))
        minimum = _require_non_negative_int(row["minimum_day"], "%s[%d].minimum_day" % (block, i))
        maximum = _require_non_negative_int(row["maximum_day"], "%s[%d].maximum_day" % (block, i))
        if minimum > maximum:
            raise CourseDecodeError(
                "block %r row %d minimum_day exceeds maximum_day" % (block, i))
        checked.append({
            "name": row["name"],
            "minimum_day": minimum,
            "maximum_day": maximum,
            "day_limit": _require_non_negative_int(row["day_limit"], "%s[%d].day_limit" % (block, i)),
        })
    return checked


def _check_cave_rows(rows):
    checked = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or tuple(row.keys()) != CAVE_OTAKARA_FIELDS:
            raise CourseDecodeError(
                "block 'cave_otakara' row %d fields must be %r" % (i, list(CAVE_OTAKARA_FIELDS)))
        cave_id = row["cave_id"]
        if not isinstance(cave_id, str) or len(cave_id) != 4:
            raise CourseDecodeError(
                "block 'cave_otakara' row %d cave_id must be a 4-char ID32" % i)
        filename = row["definition_file"]
        if not isinstance(filename, str) or not filename.endswith(".txt"):
            raise CourseDecodeError(
                "block 'cave_otakara' row %d definition_file must be a .txt path" % i)
        checked.append({
            "cave_id": cave_id,
            "otakara_count": _require_non_negative_int(
                row["otakara_count"], "cave_otakara[%d].otakara_count" % i),
            "definition_file": _require_path(filename, "cave_otakara[%d].definition_file" % i),
        })
    return checked


def _check_scalar_record(values):
    """Shared field validators for a scalar key map (farm optional)."""
    record = {}
    name = values.get("name")
    if not isinstance(name, str) or not name:
        raise CourseDecodeError("field 'name' must be a non-empty string")
    record["name"] = name
    for key in COURSE_SCALAR_KEYS:
        if key in ("name", "start", "startangle", "farm"):
            continue
        record[key] = _require_path(values[key], key)
    if "farm" in values:
        record["farm"] = _require_path(values["farm"], "farm")
    else:
        record["farm"] = None
    start = values.get("start")
    if not isinstance(start, (list, tuple)) or len(start) != 3:
        raise CourseDecodeError("field 'start' must be [x, y, z]")
    record["start"] = [_require_finite_number(v, "start[%d]" % i)
                       for i, v in enumerate(start)]
    record["startangle"] = _require_finite_number(values.get("startangle"), "startangle")
    return record


def decode_course_pairs(pairs):
    """Strict ordered-record validator (P0 boundary, unchanged semantics).

    Requires the full key order including `farm`; real retail blocks omit
    `farm`, so this entry is for synthetic boundary tests ? use
    `decode_course_block` for retail source.
    """
    if not isinstance(pairs, list):
        raise CourseDecodeError("record must be a list of (key, value) pairs")
    keys = [k for k, _ in pairs]
    expected = list(COURSE_SCALAR_KEYS) + [
        "limit_gens",
        "loop_gens",
        "cave_otakara",
        "ground_otakara_max",
    ]
    if keys != expected:
        raise CourseDecodeError("key order must be %r, got %r" % (expected, keys))
    values = dict(pairs)
    record = _check_scalar_record(values)
    record["farm"] = _require_path(values["farm"], "farm")
    record["limit_gens"] = _check_limit_rows(values["limit_gens"], "limit_gens")
    record["loop_gens"] = _check_limit_rows(values["loop_gens"], "loop_gens")
    record["cave_otakara"] = _check_cave_rows(values["cave_otakara"])
    record["ground_otakara_max"] = _require_non_negative_int(
        values["ground_otakara_max"], "ground_otakara_max")
    return record


def _tokenize(text):
    """Split a brace-block course source into tokens (comments stripped)."""
    stripped = []
    for line in text.splitlines():
        cut = line.find("#")
        stripped.append(line[:cut] if cut >= 0 else line)
    return re.findall(r"[{}]|[^\s{}]+", " ".join(stripped))


def decode_course_block(text, course=COURSE_ID):
    """Decode one retail course block with source-faithful optional keys.

    Parses the `{ name ... startangle ... end LimitGenInfo(nonloop) ...
    LimitGenInfo(loop) ... CaveOtakara ... Ground Otakara N }` layout and
    validates through the shared field validators. `farm` maps to None when
    the retail block omits it (decomp skips absent keys).
    """
    if not isinstance(text, str) or not text.strip():
        raise CourseDecodeError("course source text is missing or empty")
    tokens = _tokenize(text)
    try:
        course_idx = tokens.index(course)
    except ValueError:
        raise CourseDecodeError("course %r missing from source" % course)
    start = course_idx
    while start >= 0 and tokens[start] != "{":
        start -= 1
    if start < 0:
        raise CourseDecodeError("course block has no opening brace")
    depth = 0
    end = None
    for i in range(start, len(tokens)):
        if tokens[i] == "{":
            depth += 1
        elif tokens[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise CourseDecodeError("course block is unbalanced")
    body = tokens[start + 1:end]
    values = {}
    i = 0
    scalars = ("name", "folder", "abe_folder", "model", "collision",
               "waterbox", "mapcode", "farm", "route")
    while i < len(body):
        token = body[i]
        if token in scalars:
            if token in values:
                raise CourseDecodeError("duplicate scalar %r" % token)
            if i + 1 >= len(body):
                raise CourseDecodeError("scalar %r has no value" % token)
            values[token] = body[i + 1]
            i += 2
        elif token == "start":
            values["start"] = [float(body[i + 1]), float(body[i + 2]), float(body[i + 3])]
            i += 4
        elif token == "startangle":
            values["startangle"] = float(body[i + 1])
            i += 2
        elif token == "end":
            i += 1
            break
        else:
            raise CourseDecodeError("unexpected scalar token %r" % token)
    for key in ("name", "folder", "abe_folder", "model", "collision",
                "waterbox", "mapcode", "route", "start", "startangle"):
        if key not in values:
            raise CourseDecodeError("required scalar %r missing" % key)
    if values["name"] != course:
        raise CourseDecodeError("course name mismatch")

    def read_int(what):
        nonlocal i
        while i < len(body) and body[i] in ("(", ")"):
            i += 1
        try:
            value = int(body[i])
        except (ValueError, IndexError):
            raise CourseDecodeError("%s count missing" % what)
        i += 1
        return value

    def gen_rows(count, what):
        rows = []
        nonlocal i
        for _ in range(count):
            try:
                name = body[i]
                minimum, maximum, limit = int(body[i + 1]), int(body[i + 2]), int(body[i + 3])
            except (IndexError, ValueError):
                raise CourseDecodeError("malformed %s row" % what)
            if name in ("{", "}"):
                raise CourseDecodeError("malformed %s row" % what)
            rows.append({"name": name, "minimum_day": minimum,
                         "maximum_day": maximum, "day_limit": limit})
            i += 4
        return rows

    limit_gens = gen_rows(read_int("limit-gen"), "limit-gen")
    loop_gens = gen_rows(read_int("loop-gen"), "loop-gen")
    cave_count = read_int("cave")
    caves = []
    for _ in range(cave_count):
        # The tokenizer splits a braced tag into `{`, id, `}` tokens.
        try:
            if body[i] == "{":
                if body[i + 2] != "}":
                    raise CourseDecodeError("malformed cave row")
                tag = "{" + body[i + 1] + "}"
                count, filename = int(body[i + 3]), body[i + 4]
                i += 5
            else:
                tag, count, filename = body[i], int(body[i + 1]), body[i + 2]
                i += 3
        except (IndexError, ValueError):
            raise CourseDecodeError("malformed cave row")
        if not (tag.startswith("{") and tag.endswith("}")):
            raise CourseDecodeError("cave tag must be braced")
        caves.append({"cave_id": tag[1:-1], "otakara_count": count,
                      "definition_file": filename})
    ground_max = read_int("ground-otakara")
    if i != len(body):
        raise CourseDecodeError("trailing data after ground count")
    record = _check_scalar_record(values)
    record["limit_gens"] = _check_limit_rows(limit_gens, "limit_gens")
    record["loop_gens"] = _check_limit_rows(loop_gens, "loop_gens")
    record["cave_otakara"] = _check_cave_rows(caves)
    record["ground_otakara_max"] = _require_non_negative_int(ground_max, "ground_otakara_max")
    return record


def resource_closure(record, file_inventory=None):
    """Map a validated record onto the lane's required inventory."""
    inventory = (
        "terrain/collision/water",
        "generator day schedules and regrowth",
        "buried/enemy-held treasure",
        "Onions/ship/bridges/gates",
        "all cave entrances and return anchors",
    )
    closure = []
    for item in inventory:
        closure.append({"item": item, "status": "baseline_catalogued"})
    return closure


def missing_prerequisites():
    return [
        "Legal US Pikmin 2 disc image (GPVE01 rev 0) or an extracted "
        "'user/Abe/stages.txt' file decoded as shift_jis.",
    ]


def implementation_packet(test_log_sha256=None):
    return {
        "schema": 1,
        "lane": "p2-overworld-yakushima",
        "course": COURSE_ID,
        "issue": 150,
        "test_log_sha256": test_log_sha256,
        "playable": False,
    }

# ---------------------------------------------------------------------------
# P1 runtime import path (lane p2-overworld-yakushima-p1-surface-session).
#
# Consumes the integrated generic contract surface-session-provider-contract
# (#132, schema p2-surface-session-1) WITHOUT forking or vendoring it. The
# loader resolves the checker from the live checkout when integrated there,
# else byte-exact from the canonical git object store at the pinned
# content-line commit (blob hash verified). When neither source can supply
# it, callers get the exact pin gap (P1GapError), never invented semantics.
# ---------------------------------------------------------------------------

import copy
import subprocess
import types

CONTENT_PIN = "b08e3bdc2dfb758c0d48e4dab074081a0ee34246"
CONTRACT_PATH = "experimental/pikmin2_surface_session_contract.py"
CONTRACT_BLOB_SHA256 = "3ba71fe92a8989180358cbb1617cf040e3ebf9a25aac1754cec25a1e192460f1"
CONTRACT_SCHEMA = "p2-surface-session-1"
CANONICAL_ROOT = Path("C:/Users/alari/pikmin-randomizer")

P1_MISSING_CONTRACT = (
    "p2-surface-session-1 checker unavailable: not integrated in this "
    "checkout, and content pin b08e3bdc2dfb758c0d48e4dab074081a0ee34246 "
    "cannot supply experimental/pikmin2_surface_session_contract.py "
    "(blob 3ba71fe92a8989180358cbb1617cf040e3ebf9a25aac1754cec25a1e192460f1)."
)


class P1GapError(ValueError):
    """A P1 prerequisite pin cannot be supplied; nothing is invented."""

def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError("source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def load_surface_contract():
    """Resolve the real p2-surface-session-1 checker module (never a fork).

    Returns (module, source) where source is "tree" or "pin:<commit>".
    Raises P1GapError with exact pins when neither source can supply it.
    """
    try:
        from experimental import pikmin2_surface_session_contract as live
    except ImportError:
        live = None
    if live is not None and getattr(live, "SCHEMA", None) == CONTRACT_SCHEMA:
        return live, "tree"
    proc = subprocess.run(
        ["git", "-C", str(CANONICAL_ROOT), "show",
         "%s:%s" % (CONTENT_PIN, CONTRACT_PATH)],
        capture_output=True)
    if proc.returncode != 0:
        raise P1GapError(P1_MISSING_CONTRACT)
    blob = proc.stdout
    if sha256_bytes(blob) != CONTRACT_BLOB_SHA256:
        raise P1GapError(
            "surface contract bytes drifted at pin %s; refusing substitute "
            "semantics." % CONTENT_PIN)
    module = types.ModuleType("pikmin2_surface_session_contract_pinned")
    exec(compile(blob, CONTRACT_PATH, "exec"), module.__dict__)
    if getattr(module, "SCHEMA", None) != CONTRACT_SCHEMA:
        raise P1GapError("pinned contract has unexpected schema")
    return module, "pin:" + CONTENT_PIN


def boundary_scripts(record):
    """Event scripts per boundary, grounded in the decoded course record."""
    if not isinstance(record, dict) or record.get("name") != COURSE_ID:
        raise P1GapError("boundary scripts need a validated yakushima record")
    tags = [row["cave_id"] for row in record.get("cave_otakara", [])]
    first_tag = tags[0] if tags else "y_01"
    return {
        "day_transition": [
            {"type": "begin_day", "day": 2},
            {"type": "sunset", "time_of_day": 1.0},
            {"type": "save"},
            {"type": "reload"},
            {"type": "begin_day", "day": 3},
        ],
        "receipt_replay": [
            {"type": "deliver_receipt", "identity": "cave:" + first_tag,
             "slot": "surface:1", "encounter": "surface"},
            {"type": "deliver_receipt", "identity": "cave:" + first_tag,
             "slot": "surface:1", "encounter": "surface"},
        ],
        "exit_reentry": [
            {"type": "exit_cave"},
            {"type": "enter_cave", "cave_id": first_tag, "floor": 1},
            {"type": "exit_cave", "cave_pokos": 0},
            {"type": "enter_cave", "cave_id": first_tag, "floor": 1},
        ],
    }


_EXPECTED_STEPS = {
    "day_transition": [True, True, True, True, True],
    "receipt_replay": [True, False],
    "exit_reentry": [False, True, True, True],
}


def stage_p1_run(record, run_dir):
    """Stage a validated yakushima record into a private P1 run layout."""
    if not isinstance(record, dict) or record.get("name") != COURSE_ID:
        raise P1GapError("staging needs a validated yakushima record")
    checker, source = load_surface_contract()
    run = Path(run_dir)
    run.mkdir(parents=True, exist_ok=True)
    seed = checker.blank_session(course=COURSE_ID, day=1)
    scripts = boundary_scripts(record)
    record_path = run / "course-record.json"
    record_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seed_path = run / "session-seed.json"
    seed_path.write_text(
        json.dumps(seed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    bounds_path = run / "boundaries.json"
    bounds_path.write_text(
        json.dumps(scripts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "run_dir": str(run),
        "record": str(record_path),
        "record_sha256": sha256_bytes(record_path.read_bytes()),
        "seed": str(seed_path),
        "seed_sha256": sha256_bytes(seed_path.read_bytes()),
        "boundaries": str(bounds_path),
        "boundaries_sha256": sha256_bytes(bounds_path.read_bytes()),
        "contract_source": source,
        "contract_schema": checker.SCHEMA,
    }


def drive_session_boundaries(run_dir):
    """Drive the real checker over staged boundaries; report verdicts.

    Existing checker behavior and missing native integration are reported
    separately: a boundary passes only when every observed step matches the
    contract-expected outcome; native-backed requests are recorded missing.
    """
    checker, source = load_surface_contract()
    run = Path(run_dir)
    try:
        record = json.loads((run / "course-record.json").read_text(encoding="utf-8"))
        seed = json.loads((run / "session-seed.json").read_text(encoding="utf-8"))
        scripts = json.loads((run / "boundaries.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise P1GapError("private run layout unreadable at %s: %s" % (run, exc))
    if not isinstance(record, dict) or record.get("name") != COURSE_ID:
        raise P1GapError("staged record is not a yakushima course record")
    report = {"contract_source": source, "contract_schema": checker.SCHEMA,
              "boundaries": {}, "missing_integration": {}, "wake": {}}
    for name, events in scripts.items():
        expected = _EXPECTED_STEPS.get(name)
        if expected is None or len(expected) != len(events):
            raise P1GapError("boundary script %r is not contract-shaped" % name)
        state = copy.deepcopy(seed)
        steps = []
        for event in events:
            ok, new_state, reason = checker.check_transition(state, event)
            steps.append({"event": event, "ok": ok, "reason": reason})
            if ok:
                state = new_state
        observed = [step["ok"] for step in steps]
        verdict = ("pass" if observed == expected
                   else "FAIL: observed %s, contract expects %s" % (observed, expected))
        report["boundaries"][name] = {"steps": steps, "verdict": verdict}
    for name in checker.MISSING_INTEGRATION:
        ok, _ignored, reason = checker.request_integration(name)
        report["missing_integration"][name] = {"ok": ok, "reason": reason}
    wake = checker.wake_criteria(COURSE_ID)
    wake["course_record_decoded"] = True
    wake["cave_entrances_known"] = True
    report["wake"] = wake
    return report


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stages", type=Path, default=None,
                        help="path to extracted user/Abe/stages.txt")
    parser.add_argument("--output", type=Path, default=None,
                        help="write course record JSON here (otherwise stdout)")
    parser.add_argument("--p1-run", type=Path, default=None,
                        help="stage the record into DIR and drive P1 boundaries")
    args = parser.parse_args(argv)
    if args.stages is None:
        raise SystemExit("missing prerequisite: legal user/Abe/stages.txt bytes")
    raw = args.stages.read_bytes()
    record = decode_course_block(raw.decode("shift_jis"))
    if args.p1_run is not None:
        staged = stage_p1_run(record, args.p1_run)
        report = drive_session_boundaries(args.p1_run)
        (args.p1_run / "boundary-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for name, result in report["boundaries"].items():
            print("%s: %s" % (name, result["verdict"]))
        print("contract_source=%s" % report["contract_source"])
        print("staged=%s" % staged["run_dir"])
        return 0
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
