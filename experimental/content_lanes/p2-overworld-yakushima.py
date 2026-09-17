"""P0 source audit + import contract for Perplexing Pool (yakushima, #150).

Lane p2-overworld-yakushima. This module is an isolated metadata/import
adapter: it encodes the retail course-record contract exactly as the
decompilation loads it, validates a decoded record strictly, maps it onto
the lane's required inventory, and names the exact missing prerequisites.
It performs no native build, spawns no actors, and claims no playability.

Source facts (read-only decomp references, never modified by this lane):

- ``include/Game/gameStages.h`` (projectPiki/pikmin2): ``CourseInfo`` fields
  (name/folder/abe_folder/model/collision/waterbox/mapcode/farm/route paths,
  start position + start angle, course index, limit/loop ``LimitGenInfo``,
  ``CaveOtakaraInfo``, ground otakara max, demo matrix) and
  ``MAX_LEVELS (4)`` — the overworld course count.
- ``src/plugProjectKandoU/gameStages.cpp``: ``CourseInfo::read`` consumes the
  keys in the fixed order name, folder, abe_folder, model, collision,
  waterbox, mapcode, farm, route, start, startangle, then the limit-gen,
  loop-gen and cave-otakara blocks, then the ground-otakara-max int.
  ``LimitGenInfo::read`` rows are (name, minimum day, maximum day, day
  limit). ``CaveOtakaraInfo::read`` rows are (4-char ID32, otakara count
  byte, definition filename string).

Actual ``user/Abe/stages.txt`` bytes are UNAVAILABLE in every reachable
checkout (absent from the decomp repo, which only carries the loader; no
local P2 disc image staged). The lane plan records ``source_sha256: null``.
Per the brief, this slice therefore delivers the tested importer boundary
plus the exact missing prerequisite — no invented coordinates, IDs,
schedules, counts or hashes. Every decoded value below is either cited
decomp structure or an explicitly synthetic test fixture.
"""

COURSE_ID = "yakushima"
LABEL = "Perplexing Pool"
SOURCE_PATH = "user/Abe/stages.txt"
ISSUE = 150
CONTRACT_VERSION = "p2-overworld-course-1"

# Fixed scalar key order consumed by CourseInfo::read (gameStages.cpp).
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

# Required inventory from the lane entry (docs/PIKMIN_CONTENT_IMPORT_LANES.json).
REQUIRED_INVENTORY = (
    "terrain/collision/water",
    "generator day schedules and regrowth",
    "buried/enemy-held treasure",
    "Onions/ship/bridges/gates",
    "all cave entrances and return anchors",
)

# Runtime dependencies from the lane entry; P1 waits on their validated
# publications, so they are named here, never assumed satisfied.
RUNTIME_DEPENDENCIES = (128, 130, 131, 132, 140, 144, 145, 146)

# Sibling yakushima cave lanes that own the entrance-target definitions
# this overworld record will eventually cross-check against.
SIBLING_CAVE_ISSUES = (158, 159, 160, 161)


class CourseDecodeError(ValueError):
    """Strict structural failure of a decoded course record."""


def _require_finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CourseDecodeError("field %r must be a number, got %r" % (field, value))
    if value != value or value in (float("inf"), float("-inf")):
        raise CourseDecodeError("field %r must be finite, got %r" % (field, value))
    return float(value)


def _require_non_negative_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise CourseDecodeError("field %r must be an int, got %r" % (field, value))
    if value < 0:
        raise CourseDecodeError("field %r must be >= 0, got %r" % (field, value))
    return value


def _require_path(value, field):
    if not isinstance(value, str) or not value:
        raise CourseDecodeError("field %r must be a non-empty path, got %r" % (field, value))
    if value.startswith("/") or value.startswith("\\") or ".." in value.split("/"):
        raise CourseDecodeError("field %r escapes the asset tree: %r" % (field, value))
    return value


def decode_course_pairs(pairs):
    """Validate an ordered decoded course record.

    ``pairs`` is the scalar key sequence ``[(key, value), ...]`` in stream
    order, followed by the three blocks under the pseudo-keys
    ``limit_gens``, ``loop_gens``, ``cave_otakara`` and the trailing
    ``ground_otakara_max`` int — mirroring ``CourseInfo::read``. Returns a
    plain dict on success; raises :class:`CourseDecodeError` naming the
    exact failure otherwise. The real-bytes reader (JSystem Stream over
    disc bytes) is the recorded missing prerequisite; this boundary takes
    already-decoded values so no retail bytes are fabricated here.
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
        raise CourseDecodeError(
            "key order must be %r, got %r" % (expected, keys)
        )
    values = dict(pairs)
    record = {}
    for key in COURSE_SCALAR_KEYS:
        value = values[key]
        if key in ("start",):
            if not isinstance(value, (list, tuple)) or len(value) != 3:
                raise CourseDecodeError("field 'start' must be [x, y, z]")
            record[key] = [_require_finite_number(v, "start[%d]" % i) for i, v in enumerate(value)]
        elif key == "startangle":
            record[key] = _require_finite_number(value, key)
        elif key == "name":
            if not isinstance(value, str) or not value:
                raise CourseDecodeError("field 'name' must be a non-empty string")
            record[key] = value
        else:
            record[key] = _require_path(value, key)
    for block in ("limit_gens", "loop_gens"):
        rows = values[block]
        if not isinstance(rows, list):
            raise CourseDecodeError("block %r must be a list" % block)
        checked = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or tuple(row.keys()) != LIMIT_GEN_FIELDS:
                raise CourseDecodeError(
                    "block %r row %d fields must be %r" % (block, i, list(LIMIT_GEN_FIELDS))
                )
            if not isinstance(row["name"], str) or not row["name"]:
                raise CourseDecodeError("block %r row %d name must be non-empty" % (block, i))
            minimum = _require_non_negative_int(row["minimum_day"], "%s[%d].minimum_day" % (block, i))
            maximum = _require_non_negative_int(row["maximum_day"], "%s[%d].maximum_day" % (block, i))
            if minimum > maximum:
                raise CourseDecodeError(
                    "block %r row %d minimum_day %d exceeds maximum_day %d" % (block, i, minimum, maximum)
                )
            checked.append({
                "name": row["name"],
                "minimum_day": minimum,
                "maximum_day": maximum,
                "day_limit": _require_non_negative_int(row["day_limit"], "%s[%d].day_limit" % (block, i)),
            })
        record[block] = checked
    rows = values["cave_otakara"]
    if not isinstance(rows, list):
        raise CourseDecodeError("block 'cave_otakara' must be a list")
    checked = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict) or tuple(row.keys()) != CAVE_OTAKARA_FIELDS:
            raise CourseDecodeError(
                "block 'cave_otakara' row %d fields must be %r" % (i, list(CAVE_OTAKARA_FIELDS))
            )
        cave_id = row["cave_id"]
        if not isinstance(cave_id, str) or len(cave_id) != 4:
            raise CourseDecodeError(
                "block 'cave_otakara' row %d cave_id must be a 4-char ID32" % i
            )
        filename = row["definition_file"]
        if not isinstance(filename, str) or not filename.endswith(".txt"):
            raise CourseDecodeError(
                "block 'cave_otakara' row %d definition_file must be a .txt path" % i
            )
        checked.append({
            "cave_id": cave_id,
            "otakara_count": _require_non_negative_int(
                row["otakara_count"], "cave_otakara[%d].otakara_count" % i
            ),
            "definition_file": _require_path(filename, "cave_otakara[%d].definition_file" % i),
        })
    record["cave_otakara"] = checked
    record["ground_otakara_max"] = _require_non_negative_int(
        values["ground_otakara_max"], "ground_otakara_max"
    )
    return record


def resource_closure(record, file_inventory=None):
    """Map a validated record onto the lane's required inventory.

    ``file_inventory`` is an optional set of asset paths known present;
    ``None`` (the current honest state — no disc staged) marks every
    record-derived item ``missing-source`` instead of inventing presence.
    Items with no loader field at all are ``unsupported-reference`` with
    the exact owning system named. Returns ``{item: {status, detail}}``
    covering exactly ``REQUIRED_INVENTORY``.
    """
    have = set(file_inventory) if file_inventory is not None else None

    def path_status(path):
        if have is None:
            return ("missing-source", "source bytes unavailable; path decoded from contract only")
        return ("present", "listed in supplied inventory") if path in have else (
            "missing-source", "path not in supplied inventory")

    terrain = {}
    for key in ("collision", "waterbox", "mapcode"):
        status, detail = path_status(record[key])
        terrain[key] = {"status": status, "path": record[key], "detail": detail}
    schedules = {
        "limit_gens": len(record["limit_gens"]),
        "loop_gens": len(record["loop_gens"]),
        "rows": record["limit_gens"] + record["loop_gens"],
        "status": "missing-source" if have is None else "present",
        "detail": "day schedules decode from the record; regrowth behavior is owned by #132",
    }
    treasure = {
        "cave_otakara": record["cave_otakara"],
        "ground_otakara_max": record["ground_otakara_max"],
        "status": "missing-source" if have is None else "present",
        "detail": "buried/enemy-held placement values live in per-map generator files, not the course record",
    }
    structures = {
        "status": "unsupported-reference",
        "detail": "CourseInfo carries no Onion/ship/bridge/gate fields (gameStages.h); "
                  "these resolve through per-map generator + collision data owned by #132/#140-146",
    }
    entrances = {
        "cave_ids": [row["cave_id"] for row in record["cave_otakara"]],
        "status": "missing-source" if have is None else "present",
        "return_anchors": {
            "status": "unsupported-reference",
            "detail": "return anchors are not course-record fields; owned by cave lanes #158-161",
        },
    }
    return {
        "terrain/collision/water": terrain,
        "generator day schedules and regrowth": schedules,
        "buried/enemy-held treasure": treasure,
        "Onions/ship/bridges/gates": structures,
        "all cave entrances and return anchors": entrances,
    }


def missing_prerequisites():
    """Exact missing prerequisites for P1. No invented values."""
    return [
        "Retail bytes of user/Abe/stages.txt from the operator's own Pikmin 2 "
        "disc image (expected on extracted media under files/user/Abe/stages.txt); "
        "no checkout on this host carries it and lane source_sha256 is null. "
        "Record its SHA-256 in the lane entry when staged; never redistribute assets.",
        "Validated P1 publications from runtime dependencies #128, #130, #131, "
        "#132, #140, #144, #145, #146 before any private runtime import.",
        "Sibling cave definitions #158 (yakushima_1), #159 (yakushima_2), "
        "#160 (yakushima_3), #161 (yakushima_4) before entrance-to-cave cross-checks.",
    ]


def implementation_packet(test_log_sha256=None):
    """Reviewed P0 implementation packet. Metadata only; not playable."""
    return {
        "packet": "p2-overworld-yakushima P0",
        "lane": "p2-overworld-yakushima",
        "course": COURSE_ID,
        "label": LABEL,
        "issue": ISSUE,
        "source": SOURCE_PATH,
        "source_sha256": None,
        "contract": CONTRACT_VERSION,
        "required_inventory": list(REQUIRED_INVENTORY),
        "floors": 0,
        "floor_note": "overworld course: no cave floors; MAX_LEVELS (4) is the overworld course count (gameStages.h)",
        "missing_prerequisites": missing_prerequisites(),
        "test_log_sha256": test_log_sha256,
        "playability": "no claim of playability; metadata is not runtime acceptance",
    }
