"""P0 source audit + import contract for yakushima_3 cave (#160).

Lane p2-cave-yakushima_3 (7 floors). This module is an isolated
metadata/import adapter: it encodes the retail cave-record contract exactly
as the decompilation loads it, strictly validates decoded floor rosters,
classifies roster tokens syntactically, cross-checks the two pinned catalogs
against each other, maps resource closure onto owning lanes, and names the
exact missing prerequisites. It performs no native build, spawns no actors,
and claims no playability.

Source facts (read-only decomp references, never modified by this lane):

- ``include/Game/Cave/Info.h`` (projectPiki/pikmin2): ``CaveInfo`` parms
  ``mFloorMax`` (``c000``, 1..128) with ``FloorInfo`` children;
  ``FloorInfo`` parms ``f000``-``f017`` (floor indices, teki/item/gate/cap
  maxima, room count, route ratio, escape-fountain flag, unit file ``f008``,
  lighting ``f009``, vrbox, hole-clogged flag, alpha/beta/hidden types,
  version, Waterwraith timer ``f016``, seesaw); ``TekiInfo`` (enemy ID,
  weight, spawn type, drop mode, held-treasure code); ``ItemInfo``
  (cave ID, weight); ``GateInfo`` (cave ID, life, weight); ``CapInfo``
  (empty flag + teki); ``BaseGen`` spawn types 0-8 (enemy easy/hard,
  treasure, hole/geyser, door seam, plant, start, enemy special).
- ``$N``-prefixed tokens are generator variants per the canonical roster
  alias rules (docs/PIKMIN2_ENEMY_ROSTER.md ``resolve_alias``); this adapter
  classifies them syntactically and never invents spawn semantics.

Actual ``user/Mukki/mapunits/caveinfo/yakushima_3.txt`` bytes are UNAVAILABLE
in every reachable checkout (absent from the decomp repo, which only carries
the loader; no local P2 disc image staged; no story-cave hash recorded in
docs/PIKMIN2_CONTENT_INVENTORY.json ``source_sha256``). The lane plan
records ``source_sha256: null``. Per the brief, this slice therefore
delivers the tested importer boundary plus the exact missing prerequisite —
no invented coordinates, IDs, schedules, counts or hashes. Every decoded
value below is either pinned catalog metadata (clearly labeled as such, not
as fresh retail bytes) or an explicitly synthetic test fixture.
"""
import re

CAVE_ID = "yakushima_3"
LABEL = "yakushima_3"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/yakushima_3.txt"
ISSUE = 160
CONTRACT_VERSION = "p2-cave-yakushima3-1"
FLOOR_COUNT = 7

# Decoded floor-record keys, mirroring one FloorInfo roster row as catalogued
# (unit pool file + weighted enemy/treasure token lists). Weights, timers and
# gate/cap rows live in the retail bytes and are NOT part of this boundary.
FLOOR_KEYS = ("first", "last", "unit_pool", "enemy_ids", "treasure_ids")

# Runtime dependencies from the lane entry; P1 waits on their validated
# publications, so they are named here, never assumed satisfied.
RUNTIME_DEPENDENCIES = (129, 128, 131, 132, 140, 144, 145, 146)

# Sibling yakushima cave lanes sharing the course and entrance accounting.
SIBLING_CAVE_ISSUES = (158, 159, 161)


class CaveDecodeError(ValueError):
    """Strict structural failure of a decoded cave floor roster."""


def _require_floor_index(value, field):
    if isinstance(value, bool) or not isinstance(value, int):
        raise CaveDecodeError("field %r must be an int, got %r" % (field, value))
    if not 1 <= value <= 128:
        raise CaveDecodeError("field %r must be within CaveInfo floor range 1..128, got %r" % (field, value))
    return value


def _require_unit_path(value, field):
    if not isinstance(value, str) or not value:
        raise CaveDecodeError("field %r must be a non-empty unit file, got %r" % (field, value))
    if not value.endswith(".txt"):
        raise CaveDecodeError("field %r must be a .txt unit file, got %r" % (field, value))
    if value.startswith("/") or value.startswith("\\") or ".." in value.split("/"):
        raise CaveDecodeError("field %r escapes the asset tree: %r" % (field, value))
    return value


def _require_token_list(value, field, floor):
    if not isinstance(value, list):
        raise CaveDecodeError("floor %d field %r must be a list, got %r" % (floor, field, value))
    for i, token in enumerate(value):
        if not isinstance(token, str) or not token:
            raise CaveDecodeError(
                "floor %d field %r token %d must be a non-empty string, got %r" % (floor, field, i, token))
    return list(value)


def decode_cave_floors(floors):
    """Validate decoded floor rosters for the 7-floor cave.

    ``floors`` is a list of 7 dicts with exactly the keys ``first``,
    ``last``, ``unit_pool``, ``enemy_ids``, ``treasure_ids``; floor ``n``
    (1-based) must satisfy ``first == last == n`` so coverage is complete
    and contiguous. Returns a normalized copy on success; raises
    :class:`CaveDecodeError` naming the exact failure otherwise. The
    real-bytes reader (JSystem Stream over disc bytes through
    ``CaveInfo::load``/``FloorInfo::read``) is the recorded missing
    prerequisite; this boundary takes already-decoded catalog values so no
    retail bytes are fabricated here.
    """
    if not isinstance(floors, list):
        raise CaveDecodeError("floors must be a list of floor records")
    if len(floors) != FLOOR_COUNT:
        raise CaveDecodeError(
            "yakushima_3 requires exactly %d floors, got %d" % (FLOOR_COUNT, len(floors)))
    record = []
    for n, floor in enumerate(floors, 1):
        if not isinstance(floor, dict) or tuple(floor.keys()) != FLOOR_KEYS:
            raise CaveDecodeError(
                "floor %d keys must be %r" % (n, list(FLOOR_KEYS)))
        first = _require_floor_index(floor["first"], "first")
        last = _require_floor_index(floor["last"], "last")
        if (first, last) != (n, n):
            raise CaveDecodeError(
                "floor %d must satisfy first == last == %d, got %r/%r" % (n, n, first, last))
        record.append({
            "first": first,
            "last": last,
            "unit_pool": _require_unit_path(floor["unit_pool"], "unit_pool"),
            "enemy_ids": _require_token_list(floor["enemy_ids"], "enemy_ids", n),
            "treasure_ids": _require_token_list(floor["treasure_ids"], "treasure_ids", n),
        })
    return record


def classify_token(token):
    """Syntactic roster-token class. No spawn semantics are invented.

    Returns one of ``generator_variant`` (``$N``-prefixed per the roster
    alias rules; ``base`` is the token with the prefix stripped),
    ``exact`` (a plain ``Enum``/name token resolved downstream by the owning
    lanes), or ``compound`` (any other multi-part token, passed through
    opaquely — this adapter never splits it into a species claim).
    """
    if not isinstance(token, str) or not token:
        raise CaveDecodeError("token must be a non-empty string, got %r" % (token,))
    if token.startswith("$"):
        match = re.fullmatch(r"\$(\d+)(.+)", token)
        if not match:
            raise CaveDecodeError("malformed generator-variant token: %r" % (token,))
        return {"class": "generator_variant", "token": token, "base": match.group(2)}
    if "_" in token:
        return {"class": "compound", "token": token, "base": None}
    return {"class": "exact", "token": token, "base": None}


def floor_coverage(floors):
    """Coverage report over decoded floors: contiguity, gaps, duplicates."""
    seen = {}
    for floor in floors:
        seen.setdefault((floor["first"], floor["last"]), []).append(floor)
    expected = [(n, n) for n in range(1, FLOOR_COUNT + 1)]
    missing = [pair for pair in expected if pair not in seen]
    duplicates = sorted(pair for pair, rows in seen.items() if len(rows) > 1)
    extra = sorted(pair for pair in seen if pair not in expected)
    return {
        "floor_count": len(floors),
        "expected_count": FLOOR_COUNT,
        "contiguous": not missing and not extra and not duplicates,
        "missing": missing,
        "duplicates": duplicates,
        "extra": extra,
    }


def lane_vs_inventory(lane_floors, inventory_floors):
    """Exact per-floor consistency between the two pinned catalogs.

    Both inputs are decoded floor lists in catalog form. Returns
    ``{"equal": bool, "mismatches": [...]}`` with one entry per differing
    floor naming the exact key divergence. Catalog agreement is the P0
    baseline; any mismatch is a catalog bug to fix, never silently merged.
    """
    mismatches = []
    if len(lane_floors) != len(inventory_floors):
        return {"equal": False, "mismatches": [
            "floor list lengths differ: lane=%d inventory=%d"
            % (len(lane_floors), len(inventory_floors))]}
    for n, (left, right) in enumerate(zip(lane_floors, inventory_floors), 1):
        for key in FLOOR_KEYS:
            if left.get(key) != right.get(key):
                mismatches.append(
                    "floor %d key %r differs: lane=%r inventory=%r"
                    % (n, key, left.get(key), right.get(key)))
    return {"equal": not mismatches, "mismatches": mismatches}


def token_inventory(floors):
    """Unique enemy/treasure tokens across floors with syntactic classes."""
    enemies, treasures = {}, {}
    for floor in floors:
        for token in floor["enemy_ids"]:
            info = classify_token(token)
            enemies.setdefault(token, {"class": info["class"], "base": info["base"], "floors": []})
            enemies[token]["floors"].append(floor["first"])
        for token in floor["treasure_ids"]:
            treasures.setdefault(token, {"floors": []})
            treasures[token]["floors"].append(floor["first"])
    return {"enemy_ids": enemies, "treasure_ids": treasures}


def load_source_bytes(path):
    """Tested importer boundary for the missing retail file.

    Always raises :class:`CaveDecodeError` naming the exact missing
    prerequisite: the operator's own Pikmin 2 disc must supply
    ``user/Mukki/mapunits/caveinfo/yakushima_3.txt`` (expected on extracted
    media under ``files/``) and its SHA-256 must be recorded in the lane
    entry. No bytes are synthesized and no fallback path is guessed.
    """
    raise CaveDecodeError(
        "missing prerequisite: retail bytes of %s are unavailable in every "
        "reachable checkout (checked decomp repo, staged assets and private "
        "outputs); stage the operator's own disc file %r and record its "
        "SHA-256 in the lane entry, never redistribute assets"
        % (SOURCE_PATH, str(path)))


def resource_closure(record, file_inventory=None):
    """Map validated floors onto required inventory with owning lanes.

    ``file_inventory`` is an optional set of asset paths known present;
    ``None`` (the current honest state — no disc staged) marks every
    record-derived item ``missing-source`` instead of inventing presence.
    Items with no loader field at all are ``unsupported-reference`` with the
    exact owning system named. Returns the closure covering unit layouts,
    enemy spawns, treasure placements, floor timing/schedules and
    gate/cap/door seams.
    """
    have = set(file_inventory) if file_inventory is not None else None

    def path_status(path):
        if have is None:
            return ("missing-source", "source bytes unavailable; path catalogued only")
        return ("present", "listed in supplied inventory") if path in have else (
            "missing-source", "path not in supplied inventory")

    units = {}
    for floor in record:
        status, detail = path_status(floor["unit_pool"])
        units["floor_%d" % floor["first"]] = {
            "status": status, "path": floor["unit_pool"], "detail": detail,
            "owner": "cave unit geometry resolves through the accepted generator pin (#129); "
                     "this lane never forks generation",
        }
    inventory = token_inventory(record)
    spawns = {
        "token_classes": sorted({info["class"] for info in inventory["enemy_ids"].values()}),
        "enemy_token_count": len(inventory["enemy_ids"]),
        "status": "missing-source" if have is None else "present",
        "detail": "weighted TekiInfo rows (enemy ID/weight/spawn-type/drop-mode/held-treasure) "
                  "decode from retail bytes via FloorInfo::read; catalogued tokens are rosters, "
                  "not spawn counts. Actor behavior owned by #128/#130/#131/#140-146.",
    }
    treasure = {
        "treasure_token_count": len(inventory["treasure_ids"]),
        "status": "missing-source" if have is None else "present",
        "detail": "ItemInfo rows (cave ID/weight) decode from retail bytes; no treasure "
                  "catalog exists in docs/PIKMIN2_CONTENT_INVENTORY.json, so tokens pass "
                  "through unresolved. Placement owned by #132 progression lanes.",
    }
    timing = {
        "status": "unsupported-reference",
        "detail": "Floor timers, Waterwraith timer (f016), escape-fountain flags and day "
                  "schedules are FloorInfo parm fields decoded from bytes only; P0 records "
                  "no values. Challenge framework timing owned by #136; cave runtime by #129.",
    }
    seams = {
        "status": "unsupported-reference",
        "detail": "GateInfo/CapInfo rows, door seams, hole/geyser and start placements are "
                  "generator-seam behavior owned by #129 with actor hooks from #128/#140-146; "
                  "this lane proposes no shared-hook changes.",
    }
    return {
        "unit layout files": units,
        "enemy spawns": spawns,
        "treasure placements": treasure,
        "floor timing and schedules": timing,
        "gate/cap/door seams": seams,
    }


def missing_prerequisites():
    """Exact missing prerequisites for P1. No invented values."""
    return [
        "Retail bytes of user/Mukki/mapunits/caveinfo/yakushima_3.txt from the "
        "operator's own Pikmin 2 disc image (expected on extracted media under "
        "files/user/Mukki/mapunits/caveinfo/yakushima_3.txt); no checkout on "
        "this host carries it, no story-cave hash exists in "
        "docs/PIKMIN2_CONTENT_INVENTORY.json source_sha256, and lane "
        "source_sha256 is null. Record its SHA-256 in the lane entry when "
        "staged; never redistribute assets.",
        "The 7 floor unit files named in the roster "
        "(3_units_a_d_north_tile.txt, 2_units_ud_dry_tile.txt, "
        "4_units_a_d_f_l_tile.txt, 1_unit_16x17r_conc.txt, "
        "3_units_d_f_ujikou_tile.txt, 3_units_a_l_yuko_tile.txt, "
        "1_units_a_tile.txt) from the same media; same hash-recording rule.",
        "Validated P1 publications from runtime dependencies #129, #128, #131, "
        "#132, #140, #144, #145, #146 before any private runtime import.",
        "Sibling cave definitions #158 (yakushima_1), #159 (yakushima_2), #161 "
        "(yakushima_4) before entrance-to-cave cross-checks.",
    ]


def implementation_packet(test_log_sha256=None):
    """Reviewed P0 implementation packet. Metadata only; not playable."""
    return {
        "packet": "p2-cave-yakushima_3 P0",
        "lane": "p2-cave-yakushima_3",
        "cave": CAVE_ID,
        "issue": ISSUE,
        "source": SOURCE_PATH,
        "source_sha256": None,
        "contract": CONTRACT_VERSION,
        "floors": FLOOR_COUNT,
        "missing_prerequisites": missing_prerequisites(),
        "test_log_sha256": test_log_sha256,
        "playability": "no claim of playability; metadata is not runtime acceptance",
    }
