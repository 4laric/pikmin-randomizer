"""P0 import contract for P1 Challenge Forest (issue #564).

Isolated metadata adapter for source ``stages/chal1.ini`` (level key
``challenge:forest``, native area id 1, stage_info index 17).

Scope: decode the actual StageInfo definition, validate stage-directory
resource closure by file identity only, and build an import contract that
preserves original coordinates, IDs, schedules and floor coverage.

Explicit non-goals (P0): no native build, no runtime, no ADMIT, no asset
redistribution, and no fabricated runtime placements. ``.gen`` files are
recorded by name/hash/size only; their weighted rows are definitions, never
actor counts, so this module deliberately offers no placement emitter.
"""

from __future__ import annotations

import hashlib
import re

LEVEL_KEY = "challenge:forest"
NATIVE_AREA_ID = 1
STAGE_INFO_INDEX = 17
SOURCE_PATH = "stages/chal1.ini"
TRACKS = ("story-destination #100", "timed AP campaign #52")
RUNTIME_DEPENDENCIES = (100, 52, 6)

# Reference values observed in a staged derived copy of chal1.ini
# (sha256 54b3e0a5f84a7a93e6521e569a2c96b106102227551434e62ba77861ec4fea6d).
# Recorded as documentation only; the decoder below accepts whatever the
# actual source contains and never asserts these.
REFERENCE_MAP_FILE = "courses/stage1/forest.mod"
REFERENCE_DAY_MULTIPLY = 1.4
REFERENCE_GENERATORS = ("default.gen", "plants.gen")


class Chal1DecodeError(ValueError):
    """Raised when chal1.ini text is missing required fields or malformed."""


def _field(pattern: str, text: str, name: str) -> str:
    match = re.search(pattern, text, re.M)
    if not match:
        raise Chal1DecodeError(f"missing required field: {name}")
    return match.group(1)


def decode_chal1_ini(text: str) -> dict:
    """Decode StageInfo text (shift_jis-decoded str) into source facts.

    Returns a dict with ``navi_start`` (x, z floats), ``map_file`` (str),
    ``day_multiply`` (float or None), ``day_settings`` (int or None) and
    ``rooms`` (list of ``{index, radius, centre}`` preserving file order).
    Raises Chal1DecodeError on missing/malformed required content.
    """
    if not isinstance(text, str) or not text.strip():
        raise Chal1DecodeError("empty stage definition")
    try:
        nx, nz = _field(r"^navi_start\s+(\S+\s+\S+)", text, "navi_start").split()[:2]
        navi_start = (float(nx), float(nz))
    except Chal1DecodeError:
        raise
    except (ValueError, TypeError) as exc:
        raise Chal1DecodeError(f"malformed navi_start: {exc}") from exc
    map_file = _field(r"^map_file\s+(\S+)", text, "map_file")
    day_multiply: float | None = None
    day_match = re.search(r"^day_multiply\s+(\S+)", text, re.M)
    if day_match is not None:
        try:
            day_multiply = float(day_match.group(1))
        except ValueError as exc:
            raise Chal1DecodeError(
                f"malformed day_multiply: {day_match.group(1)!r}") from exc
    day_settings: int | None = None
    settings_match = re.search(r"numsettings\s+(\d+)", text)
    if settings_match is not None:
        day_settings = int(settings_match.group(1))
    rooms: list[dict] = []
    for block in re.finditer(r"new_room\s*\{(.*?)\}", text, re.S):
        body = block.group(1)
        try:
            index = int(_field(r"index\s+(\d+)", body, "room index"))
            radius = float(_field(r"radius\s+(\S+)", body, "room radius"))
            cx, cz = _field(
                r"centre\s+(\S+\s+\S+)", body, "room centre").split()[:2]
            rooms.append({"index": index, "radius": radius,
                          "centre": (float(cx), float(cz))})
        except Chal1DecodeError:
            raise
        except (ValueError, TypeError) as exc:
            raise Chal1DecodeError(f"malformed new_room block: {exc}") from exc
    seen = [room["index"] for room in rooms]
    if len(set(seen)) != len(seen):
        raise Chal1DecodeError("duplicate room index")
    return {"navi_start": navi_start, "map_file": map_file,
            "day_multiply": day_multiply, "day_settings": day_settings,
            "rooms": rooms}


def validate_resource_closure(decoded: dict, files: dict,
                              geometry_present: bool) -> dict:
    """Validate stage-directory closure by file identity (no content parse).

    ``files`` maps stage-directory relative names (``chal1.ini``,
    ``chal1/default.gen``, ``chal1/plants.gen``) to ``{sha256, size}``
    records. Requires ``chal1/default.gen`` and ``geometry_present`` for the
    decoded ``map_file`` target. Returns the closure record; P1 Challenge
    Forest is a single layout, so floor coverage is exactly one entry.
    """
    if not isinstance(decoded, dict) or not decoded.get("map_file"):
        raise Chal1DecodeError("decoded definition with map_file required")
    if not isinstance(files, dict):
        raise Chal1DecodeError("file inventory dict required")
    for name, record in files.items():
        if not isinstance(record, dict) or not record.get("sha256"):
            raise Chal1DecodeError(f"inventory record without sha256: {name}")
    if "chal1/default.gen" not in files:
        raise Chal1DecodeError("missing required generator: chal1/default.gen")
    if not geometry_present:
        raise Chal1DecodeError(
            f"missing geometry for map_file: {decoded['map_file']}")
    generators = sorted(name for name in files
                        if name.startswith("chal1/") and name.endswith(".gen"))
    return {"floors": 1, "floor_ids": [LEVEL_KEY],
            "map_file": decoded["map_file"],
            "generators": generators,
            "files": dict(files)}


def source_sha256_of_bytes(data: bytes) -> str:
    """Hash raw stage bytes (disc or staged copy) for the contract record."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise Chal1DecodeError("non-empty source bytes required")
    return hashlib.sha256(bytes(data)).hexdigest()


def build_import_contract(decoded: dict, closure: dict,
                          source_sha256: str | None = None) -> dict:
    """Assemble the P0 import contract from decoded facts and closure.

    Identity constants come from the lane entry; every coordinate, schedule
    and file fact is carried through verbatim from the inputs. Weighted
    generator rows are never expanded into placements here.
    """
    if closure.get("floor_ids") != [LEVEL_KEY] or closure.get("floors") != 1:
        raise Chal1DecodeError("closure must cover exactly challenge:forest")
    if closure.get("map_file") != decoded.get("map_file"):
        raise Chal1DecodeError("closure/map_file drift between inputs")
    return {
        "level_key": LEVEL_KEY,
        "native_area_id": NATIVE_AREA_ID,
        "stage_info_index": STAGE_INFO_INDEX,
        "source": SOURCE_PATH,
        "source_sha256": source_sha256,
        "navi_start": list(decoded["navi_start"]),
        "map_file": decoded["map_file"],
        "day_multiply": decoded.get("day_multiply"),
        "day_settings": decoded.get("day_settings"),
        "rooms": [dict(room) for room in decoded.get("rooms", [])],
        "floor_coverage": {"floors": 1, "floor_ids": [LEVEL_KEY]},
        "resource_closure": {"generators": list(closure["generators"]),
                             "files": dict(closure["files"])},
        "tracks": list(TRACKS),
        "runtime_dependencies": list(RUNTIME_DEPENDENCIES),
        "native_framework_blockers": [
            "Ten-destination navigation: level key must accompany area id 1 "
            "through map select, launch and travel (issue #100 scope).",
            "Independent persistence: cache/card/check routing per level key "
            "with campaign/challenge save isolation (issue #100 scope).",
            "Timed/scored AP campaign checks, routing and retry/reconnect "
            "semantics stay separate from story destinations (issue #52).",
            "No placement, collision, water, route or balance claims until "
            "P1 private runtime on pinned inputs with fresh 960x540 fixture.",
        ],
        "playable": False,
    }
