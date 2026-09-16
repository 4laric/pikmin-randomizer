"""P0 import-contract adapter for P2 overworld course `last` (Wistful Wild).

Lane p2-overworld-last, issue #151, parent #531. P0 only: decode and validate
`user/Abe/stages.txt` course metadata for course `last`, with byte-exact
source hashing and a resource-closure manifest. No native build, no runtime,
no placements: weighted generator rows remain definitions, never actor counts.

Source-backed schema (read-only decomp `native/pikmin2-research`,
revision `632af9378`):
- `include/Game/gameStages.h`: `Stages` holds at most `MAX_LEVELS (4)`
  courses; `CourseInfo` carries folder/abe_folder/model/collision/waterbox/
  mapcode/farm/route paths, start position + start angle, limit/loop
  generator tables, cave-otakara table and ground-otakara max.
- `src/plugProjectKandoU/gameStages.cpp`: `Stages::read` reads an int16
  course count then one `CourseInfo::read` per course; `CourseInfo::read`
  consumes keywords in order (name, folder, abe_folder, model, collision,
  waterbox, mapcode, farm, route, start + 3 floats, startangle + 1 float +
  1 discarded trailer token), then `LimitGenInfo` (count + name/min/max/
  limit rows), `LoopGenInfo` (same shape), `CaveOtakaraInfo` (count +
  id/otakara-count/filename rows) and a final `mGroundOtakaraMax` int.
- `Stages::createMapMgr` path-join semantics (mirrored by
  `resource_closure`): folder+model, folder+collision, folder+waterbox,
  folder+mapcode, folder+farm, abe_folder+route.

Course lookup mirrors `Stages::getCourseInfo`: by exact name, or by index
(our course `last` is expected at index 3 of 4).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_PATH = "user/Abe/stages.txt"
COURSE_ID = "last"
EXPECTED_COURSE_COUNT = 4
EXPECTED_COURSE_INDEX = 3

# Keyword order mirrored from CourseInfo::read (order-dependent if-chain).
PATH_KEYWORDS = ("folder", "abe_folder", "model", "collision", "waterbox",
                 "mapcode", "farm", "route")

# Lane-plan required inventory (docs/PIKMIN_CONTENT_IMPORT_LANES.json,
# lane p2-overworld-last) mapped to manifest fields that cover each item.
REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

# Exact native/framework blockers for P1: owner issues from the lane plan.
# These are runtime prerequisites, not P0 findings; P0 completes while they
# remain pending.
RUNTIME_PREREQUISITES = (
    "#128 actor/assets/species and hazards",
    "#130 actor/assets/species and hazards",
    "#131 actor/assets/species and hazards",
    "#132 surface days, saves and progression",
    "#140 actor/assets/species and hazards",
    "#144 actor/assets/species and hazards",
    "#145 actor/assets/species and hazards",
    "#146 actor/assets/species and hazards",
)


class StagesDecodeError(ValueError):
    """Raised for any malformed stages.txt content; message names the defect."""


class SourceMissingError(FileNotFoundError):
    """Raised when the legal retail source file is unavailable."""


def prerequisite_message(source: str = SOURCE_PATH) -> str:
    return (
        f"missing prerequisite: legal retail file '{source}' is not staged; "
        "extract it read-only from a legally owned P2 disc "
        "(e.g. C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso) "
        f"into the lane output directory and rerun with --source <path>; "
        "no values are invented when the source is absent"
    )


@dataclass
class LimitRow:
    name: str
    minimum_day: int
    maximum_day: int
    day_limit: int


@dataclass
class CaveRow:
    cave_id: str
    otakara_count: int
    filename: str


@dataclass
class Course:
    name: str
    index: int
    paths: dict = field(default_factory=dict)
    start: tuple = (0.0, 0.0, 0.0)
    start_angle: float = 0.0
    limit_gen: list = field(default_factory=list)
    loop_gen: list = field(default_factory=list)
    caves: list = field(default_factory=list)
    ground_otakara_max: int = 0


class _Tokens:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.pos = 0

    def take(self, what: str) -> str:
        if self.pos >= len(self.tokens):
            raise StagesDecodeError(f"truncated file while reading {what}")
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def take_int(self, what: str) -> int:
        token = self.take(what)
        try:
            return int(token)
        except ValueError:
            raise StagesDecodeError(f"bad integer for {what}: {token!r}")

    def take_float(self, what: str) -> float:
        token = self.take(what)
        try:
            value = float(token)
        except ValueError:
            raise StagesDecodeError(f"bad float for {what}: {token!r}")
        if not math.isfinite(value):
            raise StagesDecodeError(f"non-finite float for {what}: {token!r}")
        return value

    def remaining(self) -> int:
        return len(self.tokens) - self.pos


def _read_gen_table(tokens: _Tokens, what: str) -> list[LimitRow]:
    count = tokens.take_int(f"{what} count")
    if count < 0 or count > 4096:
        raise StagesDecodeError(f"implausible {what} count: {count}")
    rows = []
    for _ in range(count):
        name = tokens.take(f"{what} name")
        minimum = tokens.take_int(f"{what} minimum_day")
        maximum = tokens.take_int(f"{what} maximum_day")
        limit = tokens.take_int(f"{what} day_limit")
        rows.append(LimitRow(name, minimum, maximum, limit))
    return rows


def _read_cave_table(tokens: _Tokens) -> list[CaveRow]:
    count = tokens.take_int("cave count")
    if count < 0 or count > 4096:
        raise StagesDecodeError(f"implausible cave count: {count}")
    rows = []
    for _ in range(count):
        cave_id = tokens.take("cave id")
        otakara = tokens.take_int("cave otakara_count")
        filename = tokens.take("cave filename")
        rows.append(CaveRow(cave_id, otakara, filename))
    return rows


def _read_course(tokens: _Tokens, index: int) -> Course:
    course = Course(name="", index=index)
    # Keyword-driven header mirroring CourseInfo::read order. Each keyword
    # must appear with its values; unknown keywords are a hard error so a
    # format drift can never be silently absorbed.
    for keyword in ("name",) + PATH_KEYWORDS:
        seen = tokens.take("keyword")
        if seen != keyword:
            raise StagesDecodeError(
                f"course {index}: expected keyword {keyword!r}, found {seen!r}")
        course.paths[keyword] = tokens.take(f"course {index} {keyword}")
    course.name = course.paths.pop("name")
    seen = tokens.take("keyword")
    if seen != "start":
        raise StagesDecodeError(
            f"course {index}: expected keyword 'start', found {seen!r}")
    course.start = (tokens.take_float("start x"), tokens.take_float("start y"),
                    tokens.take_float("start z"))
    seen = tokens.take("keyword")
    if seen != "startangle":
        raise StagesDecodeError(
            f"course {index}: expected keyword 'startangle', found {seen!r}")
    course.start_angle = tokens.take_float("start angle")
    tokens.take("startangle trailer")  # discarded by CourseInfo::read
    course.limit_gen = _read_gen_table(tokens, "limit_gen")
    course.loop_gen = _read_gen_table(tokens, "loop_gen")
    course.caves = _read_cave_table(tokens)
    course.ground_otakara_max = tokens.take_int("ground_otakara_max")
    return course


def parse_stages(text: str) -> list[Course]:
    """Decode stages.txt text into ordered courses, preserving file order."""
    tokens = _Tokens(text.split())
    if not tokens.tokens:
        raise StagesDecodeError("empty stages.txt")
    count = tokens.take_int("course count")
    if count < 0 or count > 64:
        raise StagesDecodeError(f"implausible course count: {count}")
    courses = [_read_course(tokens, i) for i in range(count)]
    if tokens.remaining():
        raise StagesDecodeError(
            f"trailing tokens after {count} courses: {tokens.remaining()}")
    return courses


def select_course(courses: list[Course], course_id: str = COURSE_ID) -> Course:
    """Mirror Stages::getCourseInfo name lookup for our course id."""
    for course in courses:
        if course.name == course_id:
            return course
    raise StagesDecodeError(
        f"course {course_id!r} not present in {[c.name for c in courses]}")


def validate_course(course: Course) -> list[str]:
    """Return exact defect strings; empty means the course contract holds."""
    defects = []
    for keyword in PATH_KEYWORDS:
        value = course.paths.get(keyword, "")
        if not value:
            defects.append(f"course {course.name}: empty path for {keyword!r}")
        elif "\\" in value or value.startswith("/"):
            defects.append(
                f"course {course.name}: non-retail path shape for {keyword!r}: {value!r}")
    for axis in course.start:
        if not math.isfinite(axis):
            defects.append(f"course {course.name}: non-finite start {course.start!r}")
    if not math.isfinite(course.start_angle):
        defects.append(f"course {course.name}: non-finite start angle")
    for table, what in ((course.limit_gen, "limit_gen"), (course.loop_gen, "loop_gen")):
        for row in table:
            if not row.name:
                defects.append(f"course {course.name}: empty {what} row name")
            if row.minimum_day < 0 or row.maximum_day < 0 or row.day_limit < 0:
                defects.append(
                    f"course {course.name}: negative {what} schedule in {row!r}")
            if row.minimum_day > row.maximum_day:
                defects.append(
                    f"course {course.name}: inverted {what} day range in {row!r}")
    seen_ids: set[str] = set()
    for row in course.caves:
        if not row.cave_id:
            defects.append(f"course {course.name}: empty cave id")
        if row.cave_id in seen_ids:
            defects.append(f"course {course.name}: duplicate cave id {row.cave_id!r}")
        seen_ids.add(row.cave_id)
        if not row.filename:
            defects.append(f"course {course.name}: empty cave filename for {row.cave_id!r}")
        if row.otakara_count < 0:
            defects.append(
                f"course {course.name}: negative otakara count for {row.cave_id!r}")
    if course.ground_otakara_max < 0:
        defects.append(f"course {course.name}: negative ground_otakara_max")
    return defects


def resource_closure(course: Course) -> dict[str, str]:
    """Join resource paths exactly as Stages::createMapMgr does."""
    folder = course.paths.get("folder", "")
    abe = course.paths.get("abe_folder", "")
    return {
        "model": f"{folder}/{course.paths.get('model', '')}",
        "collision": f"{folder}/{course.paths.get('collision', '')}",
        "waterbox": f"{folder}/{course.paths.get('waterbox', '')}",
        "mapcode": f"{folder}/{course.paths.get('mapcode', '')}",
        "farm": f"{folder}/{course.paths.get('farm', '')}",
        "route": f"{abe}/{course.paths.get('route', '')}",
    }


def load_source_bytes(path: str | Path) -> tuple[bytes, str]:
    """Read the legal source file; raise SourceMissingError when absent."""
    candidate = Path(path)
    if not candidate.is_file():
        raise SourceMissingError(prerequisite_message(str(path)))
    data = candidate.read_bytes()
    if not data:
        raise StagesDecodeError(f"source file is empty: {path}")
    return data, hashlib.sha256(data).hexdigest()


def build_manifest(course: Course, source: str, sha256: str | None) -> dict:
    """Assemble the P0 metadata manifest. Never emits placements."""
    closure = resource_closure(course)
    coverage = {
        "terrain/collision/water":
            ["collision", "waterbox", "mapcode", "model"],
        "generator day schedules and regrowth":
            ["limit_gen", "loop_gen"],
        "buried/enemy-held treasure":
            ["caves[].otakara_count", "ground_otakara_max"],
        "Onions/ship/bridges/gates":
            ["farm", "route"],
        "all cave entrances and return anchors":
            ["caves[].cave_id", "caves[].filename"],
    }
    manifest = {
        "schema": "p2-overworld-p0-1",
        "lane": "p2-overworld-last",
        "issue": 151,
        "source": source,
        "source_sha256": sha256,
        "course": course.name,
        "course_index": course.index,
        "expected_course_count": EXPECTED_COURSE_COUNT,
        "expected_course_index": EXPECTED_COURSE_INDEX,
        "start": list(course.start),
        "start_angle_deg": course.start_angle,
        "resource_closure": closure,
        "limit_gen": [row.__dict__ for row in course.limit_gen],
        "loop_gen": [row.__dict__ for row in course.loop_gen],
        "caves": [row.__dict__ for row in course.caves],
        "ground_otakara_max": course.ground_otakara_max,
        "required_inventory_coverage": {
            item: {"manifest_fields": fields, "status": "metadata-only"}
            for item, fields in coverage.items()
        },
        "runtime_prerequisites": list(RUNTIME_PREREQUISITES),
        # Explicit negative contract: generator rows are definitions, not
        # actor counts; this adapter can never emit placements.
        "placements_emitted": False,
    }
    for item in REQUIRED_INVENTORY:
        if item not in manifest["required_inventory_coverage"]:
            raise StagesDecodeError(f"coverage gap for required item {item!r}")
    return manifest


def decode_course_file(path: str | Path, course_id: str = COURSE_ID) -> tuple[Course, str]:
    """Load, hash, decode and return the selected course plus its sha256."""
    data, digest = load_source_bytes(path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StagesDecodeError(f"source is not UTF-8 text: {exc}")
    courses = parse_stages(text)
    if len(courses) != EXPECTED_COURSE_COUNT:
        raise StagesDecodeError(
            f"expected {EXPECTED_COURSE_COUNT} courses, found {len(courses)}")
    course = select_course(courses, course_id)
    if course.index != EXPECTED_COURSE_INDEX:
        raise StagesDecodeError(
            f"course {course_id!r} at index {course.index}, "
            f"expected {EXPECTED_COURSE_INDEX}")
    defects = validate_course(course)
    if defects:
        raise StagesDecodeError("course defects: " + "; ".join(defects))
    return course, digest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="P0 decode of user/Abe/stages.txt course 'last'")
    parser.add_argument("--source", required=True,
                        help="path to legal retail user/Abe/stages.txt")
    parser.add_argument("--course", default=COURSE_ID)
    parser.add_argument("--manifest-out", required=True,
                        help="output path for the manifest JSON")
    args = parser.parse_args(argv)
    try:
        course, digest = decode_course_file(args.source, args.course)
    except (SourceMissingError, StagesDecodeError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    manifest = build_manifest(course, args.source, digest)
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"course={course.name} index={course.index} "
          f"caves={len(course.caves)} sha256={digest}")
    print(f"manifest={args.manifest_out} placements_emitted=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
