"""P0 import-contract adapter for P2 Challenge stage `ch_MUKI_king` (issue #542).

Lane p2-challenge-ch_muki_king, parent #531, recovery #568. P0 only: decode
and validate `user/Mukki/mapunits/caveinfo/ch_MUKI_king.txt` floor definitions
with byte-exact source hashing and a metadata-only manifest. No native build,
no runtime, no placements: weighted teki/item rows remain definitions, never
actor counts.

Source-backed schema (read-only decomp `native/pikmin2-research`,
revision `632af9378`):
- `src/plugProjectKandoU/gameCaveInfo.cpp`: `CaveInfo::load` reads the file
  as a TEXT stream; `CaveInfo::read` = cave parms + int floor-block count +
  `FloorInfo` blocks; `FloorInfo::read` = floor parms + teki list
  (token + weight + gen-type per `TekiInfo::read`) + item list
  (name + weight per `ItemInfo::read`) + gate list (name + life + weight per
  `GateInfo::read`) + cap list iff `mVersion >= 1` (`CapInfo::read`: empty
  byte, else an embedded teki row).
- `TekiInfo::read` token grammar: optional `$N` drop-mode prefix (digit
  1-9, else PikminOrLeader) + enemy name + optional `_treasure` suffix split
  at the enemy-name boundary against the enemy registry.
- `include/Game/Cave/Info.h`: `CaveInfo::Parms` = `mFloorMax` (`c000`,
  1..128); `FloorInfo::Parms` = f000 floor-first, f001 floor-last, f002
  teki max, f003 item max, f004 gate max, f014 cap max, f005 rooms 1..15,
  f006 route ratio 0..1, f007 escape fountain 0..1, f008 unit file, f009
  lighting file, f00A vrbox, f010 hole-clogged, f011/f012/f013 alpha/beta/
  hidden enums, f015 version, f016 waterwraith timer, f017 seesaw;
  `CaveGenType` 0..8; `EnemyDropMode` 0..5.
- `src/sysCommonU/parameters.cpp`: `Parameters::read` consumes (id, size,
  value) parms; `Parameters::write` emits tab-`# name` comments, so `#`
  starts a comment to end-of-line in these text files.
- Challenge roster/maturity/sprays/timers are NOT in this file; they are
  carried as catalog baseline from `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  lane p2-challenge-ch_muki_king (itself sourced from
  `user/Matoba/challenge/stages.txt` at plan time).

Text-grammar assumptions (explicit, re-validated on real bytes): whitespace
tokens, `#` comments, `{`/`}` group-framing tokens tolerated and ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MUKI_king.txt"
EXPECTED_SHA256 = "c2d773778e26aad2dc36defbb40540d54a7ddd48d0e1a59c604db58765fd35aa"
COURSE_LABEL = "P2 Challenge 10: ch_MUKI_king"
EXPECTED_FLOORS = 5

# Catalog baseline (lane plan; NOT decoded from the caveinfo file).
CATALOG_BASELINE = {
    "floors": 5,
    "pikmin_by_native_color_and_maturity": [
        [0, 0, 20], [0, 0, 20], [0, 0, 0], [0, 0, 10],
        [0, 0, 0], [0, 0, 0], [0, 0, 0],
    ],
    "bitter_sprays": 2,
    "spicy_sprays": 2,
    "floor_seconds": [100.0, 100.0, 100.0, 100.0, 100.0],
    "ui_index": 9,
    "table_order": 29,
}

RUNTIME_PREREQUISITES = (
    "#136 P2 Challenge runtime framework",
    "#137 P2 Challenge content",
    "#129 cave generation, seams and navigation",
    "#130 actor/assets/species and hazards",
    "#131 actor/assets/species and hazards",
)

# CaveGenType range from include/Game/Cave/Info.h.
GEN_TYPE_MIN, GEN_TYPE_MAX = 0, 8
# Drop modes from EnemyDropMode (Info.h).
DROP_NAMES = ("NoDrop", "PikminOrLeader", "Pikmin", "Leader",
              "CarryPikmin", "Earthquake")


class CaveDecodeError(ValueError):
    """Raised for any malformed caveinfo content; message names the defect."""


class SourceMissingError(FileNotFoundError):
    """Raised when the legal retail source file is unavailable."""


def prerequisite_message(source: str = SOURCE_PATH) -> str:
    return (
        "missing prerequisite: legal retail file '%s' is not staged; "
        "extract it read-only from a legally owned P2 disc "
        "(e.g. C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso) "
        "into the lane output directory and rerun with --source <path>; "
        "no values are invented when the source is absent" % source
    )


@dataclass
class TekiRow:
    token: str
    enemy: str
    treasure: str
    drop_mode: int
    weight: int
    gen_type: int


@dataclass
class ItemRow:
    name: str
    weight: int


@dataclass
class GateRow:
    name: str
    life: float
    weight: int


@dataclass
class Floor:
    first: int
    last: int
    parms: dict = field(default_factory=dict)
    teki: list = field(default_factory=list)
    items: list = field(default_factory=list)
    gates: list = field(default_factory=list)
    caps: list = field(default_factory=list)


def parse_teki_token(token: str, known_enemies: frozenset) -> tuple:
    """Split a teki token per TekiInfo::read grammar.

    Returns (enemy, treasure, drop_mode). The treasure part is the raw held
    suffix (pelletMgr authority to resolve); unknown enemy names are a hard
    error so aliases can never pass as source IDs.
    """
    rest = token
    drop_mode = 0
    if rest.startswith("$"):
        if len(rest) > 1 and rest[1].isdigit():
            digit = int(rest[1])
            if digit < 1 or digit > 9:
                raise CaveDecodeError("bad drop-mode digit in %r" % token)
            drop_mode = digit
            rest = rest[2:]
        else:
            drop_mode = 1  # DROP_PikminOrLeader, mirroring TekiInfo::read
            rest = rest[1:]
    if not rest:
        raise CaveDecodeError("empty enemy in teki token %r" % token)
    # Split at the enemy-name boundary: longest known-enemy prefix, with the
    # remainder (minus one underscore) as the held-treasure suffix.
    enemy, treasure = None, ""
    for cut in range(len(rest), 0, -1):
        candidate = rest[:cut]
        if candidate in known_enemies:
            tail = rest[cut:]
            if tail:
                if not tail.startswith("_"):
                    continue
                treasure = tail[1:]
                if not treasure:
                    raise CaveDecodeError(
                        "empty treasure suffix in %r" % token)
            enemy = candidate
            break
    if enemy is None:
        raise CaveDecodeError(
            "unknown enemy token %r; not in the enemy registry" % token)
    return enemy, treasure, drop_mode

class _Tokens:
    def __init__(self, text: str):
        parts: list = []
        for line in text.splitlines():
            line = line.split("#", 1)[0]
            for tok in line.split():
                if tok in ("{", "}"):
                    continue  # group framing; tolerated, ignored
                parts.append(tok)
        self.tokens = parts
        self.pos = 0

    def take(self, what: str) -> str:
        if self.pos >= len(self.tokens):
            raise CaveDecodeError("truncated file while reading %s" % what)
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def take_int(self, what: str, lo=None, hi=None) -> int:
        token = self.take(what)
        try:
            value = int(token)
        except ValueError:
            raise CaveDecodeError("bad integer for %s: %r" % (what, token))
        if (lo is not None and value < lo) or (hi is not None and value > hi):
            raise CaveDecodeError("out-of-range %s: %s" % (what, value))
        return value

    def take_float(self, what: str) -> float:
        token = self.take(what)
        try:
            value = float(token)
        except ValueError:
            raise CaveDecodeError("bad float for %s: %r" % (what, token))
        if not math.isfinite(value):
            raise CaveDecodeError("non-finite float for %s: %r" % (what, token))
        return value

    def remaining(self) -> int:
        return len(self.tokens) - self.pos


# Parm value shapes: fixed-shape ids decoded strictly; anything else is an
# explicit unsupported reference, never silently skipped.
_INT_PARMS = frozenset(("c000", "f000", "f001", "f002", "f003", "f004",
                        "f014", "f005", "f007", "f010", "f011", "f012",
                        "f013", "f015", "f017"))
_FLOAT_PARMS = frozenset(("f006", "f016"))
_STRING_PARMS = frozenset(("f008", "f009", "f00A"))
_KNOWN_PARMS = _INT_PARMS | _FLOAT_PARMS | _STRING_PARMS


def _read_parm(tokens: _Tokens, what: str):
    parm_id = tokens.take("%s parm id" % what)
    if len(parm_id) != 4:
        raise CaveDecodeError("bad parm id %r in %s" % (parm_id, what))
    size_tok = tokens.take("%s parm size for %r" % (what, parm_id))
    try:
        int(size_tok)
    except ValueError:
        raise CaveDecodeError(
            "bad parm size for %r in %s: %r" % (parm_id, what, size_tok))
    if parm_id in _INT_PARMS:
        return parm_id, tokens.take_int("%s %s" % (what, parm_id))
    if parm_id in _FLOAT_PARMS:
        return parm_id, tokens.take_float("%s %s" % (what, parm_id))
    if parm_id in _STRING_PARMS:
        return parm_id, tokens.take("%s %s" % (what, parm_id))
    raise CaveDecodeError(
        "unsupported parm id %r in %s; needs shared review, "
        "not silent skipping" % (parm_id, what))


def _read_floor(tokens: _Tokens, known_enemies: frozenset) -> Floor:
    parms: dict = {}
    for _ in range(19):  # f000..f017 documented set (f014 included)
        pid, value = _read_parm(tokens, "floor")
        if pid in parms:
            raise CaveDecodeError("duplicate floor parm %r" % pid)
        parms[pid] = value
    missing = _KNOWN_PARMS - {"c000"} - set(parms)
    if missing:
        raise CaveDecodeError("floor missing parms: %s" % sorted(missing))
    floor = Floor(first=int(parms["f000"]), last=int(parms["f001"]), parms=parms)
    if not (1 <= floor.first <= floor.last <= 128):
        raise CaveDecodeError(
            "invalid floor range %s..%s" % (floor.first, floor.last))
    version = int(parms["f015"])

    teki_count = tokens.take_int("teki count", 0, 4096)
    for _ in range(teki_count):
        token = tokens.take("teki token")
        enemy, treasure, drop = parse_teki_token(token, known_enemies)
        weight = tokens.take_int("teki weight", 0, 1 << 30)
        gen = tokens.take_int("teki gen_type", GEN_TYPE_MIN, GEN_TYPE_MAX)
        floor.teki.append(TekiRow(token, enemy, treasure, drop, weight, gen))
    item_count = tokens.take_int("item count", 0, 4096)
    for _ in range(item_count):
        floor.items.append(ItemRow(tokens.take("item name"),
                                   tokens.take_int("item weight", 0, 1 << 30)))
    gate_count = tokens.take_int("gate count", 0, 4096)
    for _ in range(gate_count):
        floor.gates.append(GateRow(tokens.take("gate name"),
                                   tokens.take_float("gate life"),
                                   tokens.take_int("gate weight", 0, 1 << 30)))
    if version >= 1:
        cap_count = tokens.take_int("cap count", 0, 4096)
        for _ in range(cap_count):
            empty = tokens.take_int("cap empty byte", 0, 1)
            if empty == 0:
                token = tokens.take("cap teki token")
                enemy, treasure, drop = parse_teki_token(token, known_enemies)
                weight = tokens.take_int("cap teki weight", 0, 1 << 30)
                gen = tokens.take_int("cap teki gen_type",
                                      GEN_TYPE_MIN, GEN_TYPE_MAX)
                floor.caps.append(TekiRow(token, enemy, treasure, drop,
                                          weight, gen))
            else:
                floor.caps.append(None)
    return floor


def parse_caveinfo(text: str, known_enemies: frozenset):
    """Decode caveinfo text into (floor_max, floors) preserving file order."""
    tokens = _Tokens(text)
    if not tokens.tokens:
        raise CaveDecodeError("empty caveinfo file")
    pid, floor_max = _read_parm(tokens, "cave")
    if pid != "c000":
        raise CaveDecodeError("expected cave parm 'c000', found %r" % pid)
    if not (1 <= int(floor_max) <= 128):
        raise CaveDecodeError("invalid floor max: %s" % (floor_max,))
    count = tokens.take_int("floor block count", 0, 128)
    floors = [_read_floor(tokens, known_enemies) for _ in range(count)]
    if tokens.remaining():
        raise CaveDecodeError(
            "trailing tokens after %s floors: %s" % (count, tokens.remaining()))
    return int(floor_max), floors


def validate_coverage(floor_max: int, floors: list,
                      expected: int = EXPECTED_FLOORS) -> list:
    """Check complete contiguous floor coverage 1..expected; returns defects."""
    defects = []
    if floor_max != expected:
        defects.append("c000 floor_max %s != catalog %s" % (floor_max, expected))
    if len(floors) != expected:
        defects.append("floor block count %s != catalog %s" % (len(floors), expected))
    covered: set = set()
    for floor in floors:
        span = set(range(floor.first, floor.last + 1))
        if covered & span:
            defects.append(
                "overlapping floor range %s..%s" % (floor.first, floor.last))
        covered |= span
    if covered != set(range(1, expected + 1)):
        defects.append(
            "coverage gap: have %s, need 1..%s" % (sorted(covered), expected))
    return defects


def load_source_bytes(path) -> tuple:
    candidate = Path(path)
    if not candidate.is_file():
        raise SourceMissingError(prerequisite_message(str(path)))
    data = candidate.read_bytes()
    if not data:
        raise CaveDecodeError("source file is empty: %s" % path)
    return data, hashlib.sha256(data).hexdigest()


def weight_sum(rows: list) -> int:
    return sum(r.weight for r in rows if r is not None)


def build_manifest(floor_max: int, floors: list, source: str,
                   sha256: str) -> dict:
    """Assemble the P0 metadata manifest. Never emits placements."""
    manifest = {
        "schema": "p2-challenge-p0-1",
        "lane": "p2-challenge-ch_muki_king",
        "issue": 542,
        "label": COURSE_LABEL,
        "source": source,
        "source_sha256": sha256,
        "expected_sha256": EXPECTED_SHA256,
        "floor_max": floor_max,
        "expected_floors": EXPECTED_FLOORS,
        "floors": [
            {
                "first": f.first,
                "last": f.last,
                "parms": f.parms,
                "teki": [r.__dict__ for r in f.teki],
                "items": [r.__dict__ for r in f.items],
                "gates": [r.__dict__ for r in f.gates],
                "caps": [(r.__dict__ if r else None) for r in f.caps],
                "weight_sums": {
                    "teki": weight_sum(f.teki),
                    "items": weight_sum(f.items),
                    "gates": weight_sum(f.gates),
                },
            }
            for f in floors
        ],
        "resource_closure": {
            "unit_files": sorted({str(f.parms["f008"]) for f in floors}),
            "lighting_files": sorted({str(f.parms["f009"]) for f in floors}),
            "vrbox_files": sorted({str(f.parms["f00A"]) for f in floors}),
        },
        # Catalog baseline (Matoba stages.txt decode at plan time), carried
        # through, NOT decoded from the caveinfo file.
        "catalog_baseline": dict(CATALOG_BASELINE),
        "runtime_prerequisites": list(RUNTIME_PREREQUISITES),
        # Explicit negative contract: weighted rows are definitions, not
        # actor counts; this adapter can never emit placements.
        "placements_emitted": False,
    }
    return manifest


def decode_caveinfo_file(path, known_enemies: frozenset):
    """Load, hash, decode and coverage-check the caveinfo file."""
    data, digest = load_source_bytes(path)
    if digest != EXPECTED_SHA256:
        raise CaveDecodeError(
            "source sha256 %s != recorded %s; "
            "refusing to decode mismatched bytes" % (digest, EXPECTED_SHA256))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CaveDecodeError("source is not UTF-8 text: %s" % exc)
    floor_max, floors = parse_caveinfo(text, known_enemies)
    defects = validate_coverage(floor_max, floors)
    if defects:
        raise CaveDecodeError("coverage defects: " + "; ".join(defects))
    return floor_max, floors, digest


_ENEMYINFO_NAME_RE = re.compile(r'\{\s*"([A-Za-z0-9_]+)"\s*,\s*EnemyTypeID::')


def _default_enemyinfo_paths():
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "native" / "pikmin2-research" / "src" / "plugProjectYamashitaU" / "enemyInfo.cpp",
        Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research/src/plugProjectYamashitaU/enemyInfo.cpp"),
    ]
    return [c for c in candidates if c.is_file()]


def load_known_enemies(enemyinfo=None):
    """Enemy-name authority: decomp gEnemyInfo[] mName values, read-only.

    Parses the first-column row names of ``gEnemyInfo[]`` in
    ``src/plugProjectYamashitaU/enemyInfo.cpp`` (the same table
    ``TekiInfo::read`` matches against). Returns an empty frozenset when
    no registry file is found; the CLI refuses to decode in that case.
    """
    if enemyinfo is None:
        found = _default_enemyinfo_paths()
        if not found:
            return frozenset()
        enemyinfo = found[0]
    try:
        text = Path(enemyinfo).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise CaveDecodeError("cannot read enemy registry: %s" % exc)
    names = set(_ENEMYINFO_NAME_RE.findall(text))
    if not names:
        raise CaveDecodeError("enemy registry yielded no names: %s" % enemyinfo)
    return frozenset(names)


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description="P0 decode of ch_MUKI_king.txt")
    parser.add_argument("--source", required=True,
                        help="path to legal retail ch_MUKI_king.txt")
    parser.add_argument("--enemyinfo", default=None,
                        help="optional gEnemyInfo registry file path")
    parser.add_argument("--manifest-out", required=True,
                        help="output path for the manifest JSON")
    args = parser.parse_args(argv)
    try:
        known = load_known_enemies(args.enemyinfo)
        if not known:
            print("ERROR enemy registry unavailable; refusing to decode",
                  file=sys.stderr)
            return 1
        floor_max, floors, digest = decode_caveinfo_file(args.source, known)
    except (SourceMissingError, CaveDecodeError) as exc:
        print("ERROR %s" % exc, file=sys.stderr)
        return 1
    manifest = build_manifest(floor_max, floors, args.source, digest)
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("floors=%s floor_max=%s sha256=%s" % (len(floors), floor_max, digest))
    print("manifest=%s placements_emitted=False" % args.manifest_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
