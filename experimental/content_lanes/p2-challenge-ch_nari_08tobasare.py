"""P0 import-contract adapter for P2 Challenge 25: ch_NARI_08tobasare (#557).

Isolated per-source metadata and boundary checks for exactly one retail
challenge definition. Reuses the shared caveinfo framing parser
(:mod:`experimental.pikmin2_cave`) and the shared semantic decoder
(:mod:`experimental.pikmin2_cave_catalog`); it never forks them.

What this module does NOT do: emit placements, spawn counts, seeded topology,
or any playability claim. Weighted roster rows stay definitions. The actual
retail bytes for this source are only readable from a local legal US GPVE01
(Pikmin 2) revision 0 disc image; when they are absent every decode entry
point fails closed with an exact missing-prerequisite record instead of
invented values.
"""
import hashlib

from experimental.pikmin2_cave import BASE, parameters, safe_name, tree

SOURCE_ID = 'ch_NARI_08tobasare'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_NARI_08tobasare.txt'
SOURCE_SHA256 = '1ba97d8165e7d29257620b08565e7273dd2529328e565cc09ba5fc4d220832db'
SCHEMA = 1

EXPECTED_DETAILS = {
    'table_order': 18,
    'cave_id': SOURCE_ID,
    'cave_path': SOURCE_PATH,
    'floors': 2,
    'legacy_time': 0.0,
    'bitter_sprays': 2,
    'spicy_sprays': 0,
    'treasure_count_field': 0,
    'ui_index': 24,
    'floor_seconds': [150.0, 100.0],
    'issue': 137,
}
EXPECTED_PIKMIN_ROSTER = [[0, 0, 25], [0, 0, 20], [0, 0, 0], [0, 0, 5],
                          [0, 0, 0], [0, 0, 0], [0, 0, 0]]
EXPECTED_FLOORS = 2

UNIT_BASE = BASE + '/units'
ARC_BASE = BASE + '/arc'
ENEMY_INFO_SOURCE = 'src/plugProjectYamashitaU/enemyInfo.cpp'
PELLET_ARCHIVE = 'user/Abe/Pellet/us/pelletlist_us.szs'
STAGES_TABLE = 'user/Matoba/challenge/stages.txt'
DISC_IDENTITY = 'US GPVE01 revision 0 (Pikmin 2)'

UNSUPPORTED_REFERENCES = [
    {'item': 'TheKey/hole/geyser placement and floor exits',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'scoring and ordinary vs deathless completion',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'retry reset semantics',
     'owner': '#136', 'status': 'unresolved', 'needs': 'accepted Challenge framework pin'},
    {'item': 'generator assembly, seams and navigation',
     'owner': '#129', 'status': 'unresolved', 'needs': 'accepted generator pin'},
    {'item': 'actor/species admission for referenced roster entries',
     'owner': '#130/#131', 'status': 'unresolved', 'needs': 'decoded roster plus admission ledger'},
    {'item': 'localized English display title',
     'owner': '#137', 'status': 'unresolved', 'needs': 'message-table extraction, never guessed'},
]


class ImportContractError(ValueError):
    """Malformed definition or contract violation; never a placement."""


class MissingPrerequisite(ImportContractError):
    """Actual retail source bytes are unavailable; exact needs attached."""

    def __init__(self, message, prerequisites):
        super().__init__(message)
        self.prerequisites = list(prerequisites)


def _integer(value, label, maximum=10000):
    if not isinstance(value, str) or not value.isdigit():
        raise ImportContractError('Expected nonnegative integer for ' + label)
    number = int(value)
    if number > maximum:
        raise ImportContractError(label + ' exceeds catalog limit')
    return number


def source_prerequisites():
    """Exact inputs required before any byte-level decode of this source."""
    return [
        {'kind': 'disc_image', 'identity': DISC_IDENTITY,
         'path_hint': 'local legal ISO exposing the GPVE01 revision 0 filesystem',
         'provides': [SOURCE_PATH, PELLET_ARCHIVE, STAGES_TABLE]},
        {'kind': 'disc_path', 'path': SOURCE_PATH,
         'expected_sha256': SOURCE_SHA256, 'encoding': 'shift_jis'},
        {'kind': 'enemy_catalog', 'path': ENEMY_INFO_SOURCE,
         'provides': 'native enemy ID set for semantic roster decode'},
        {'kind': 'treasure_catalog', 'path': PELLET_ARCHIVE,
         'provides': 'pellet/treasure ID set for semantic roster decode'},
    ]


def verify_source(data, expected_sha256=SOURCE_SHA256):
    """Hash-gate raw source bytes; raises on mismatch instead of decoding."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ImportContractError('Source bytes required for ' + SOURCE_ID)
    digest = hashlib.sha256(bytes(data)).hexdigest()
    if digest != expected_sha256:
        raise ImportContractError(
            'Source hash mismatch for %s: got %s' % (SOURCE_PATH, digest))
    return dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                sha256=digest, verified=True, size=len(data))


def decode_structure(text):
    """Decode caveinfo framing and floor ranges without enemy catalogs."""
    if not isinstance(text, str) or not text.strip():
        raise ImportContractError('Caveinfo text required for ' + SOURCE_ID)
    try:
        nodes = tree(text)
    except ValueError as exc:
        raise ImportContractError('Unparseable caveinfo framing: %s' % exc) from None
    if len(nodes) < 2 or not isinstance(nodes[0], list):
        raise ImportContractError('Missing cave header')
    try:
        header = parameters(nodes[0])
    except ValueError as exc:
        raise ImportContractError('Malformed cave header: %s' % exc) from None
    if set(header) != {'c000'}:
        raise ImportContractError('Unsupported cave header')
    if not isinstance(nodes[1], str):
        raise ImportContractError('Missing cave definition count')
    count = _integer(nodes[1], 'definition count', 128)
    if count < 1 or _integer(header['c000'], 'header count', 128) != count:
        raise ImportContractError('Cave definition count mismatch')
    floors = []
    cursor = 2
    occupied = set()
    for index in range(count):
        if cursor >= len(nodes) or not isinstance(nodes[cursor], list):
            raise ImportContractError('Missing floor parameter block %d' % index)
        try:
            params = parameters(nodes[cursor])
        except ValueError as exc:
            raise ImportContractError('Malformed floor parameters %d: %s' % (index, exc)) from None
        if not {'f000', 'f001'} <= set(params):
            raise ImportContractError('Incomplete floor range in block %d' % index)
        first = _integer(params['f000'], 'floor first', 127)
        last = _integer(params['f001'], 'floor last', 127)
        if first > last:
            raise ImportContractError('Inverted floor range in block %d' % index)
        if occupied.intersection(range(first, last + 1)):
            raise ImportContractError('Overlapping floor range in block %d' % index)
        occupied.update(range(first, last + 1))
        version = _integer(params.get('f015', '0'), 'floor version')
        pool = params.get('f008')
        if pool is not None:
            try:
                pool = safe_name(pool)
            except ValueError as exc:
                raise ImportContractError('Unsafe unit pool name in block %d' % index) from None
        floors.append(dict(definition_index=index, first_floor=first + 1,
                           last_floor=last + 1, version=version, unit_pool=pool,
                           unit_pool_path=(UNIT_BASE + '/' + pool) if pool else None))
        cursor += 1 + (4 if version >= 1 else 3)
    if cursor != len(nodes):
        raise ImportContractError('Trailing or missing cave roster data')
    return dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                definition_count=count, floors=floors, generated=False)


def check_floor_coverage(floors, expected=EXPECTED_FLOORS):
    """Require gapless 1-based coverage of exactly the catalogued floors."""
    occupied = set()
    for floor in floors:
        first, last = floor.get('first_floor'), floor.get('last_floor')
        if type(first) is not int or type(last) is not int or first < 1 or last < first:
            raise ImportContractError('Invalid floor range record')
        if occupied.intersection(range(first, last + 1)):
            raise ImportContractError('Overlapping floor ranges')
        occupied.update(range(first, last + 1))
    if occupied != set(range(1, expected + 1)):
        raise ImportContractError(
            'Floor coverage %s differs from catalogued %d floors' % (sorted(occupied), expected))
    return dict(source_id=SOURCE_ID, expected_floors=expected,
                covered_floors=sorted(occupied), complete=True)


def decode_full(text, enemy_ids, treasure_ids):
    """Semantic decode via the shared catalog parser (catalogs required)."""
    if not enemy_ids or not treasure_ids:
        raise MissingPrerequisite(
            'Semantic decode of %s needs enemy and treasure catalogs' % SOURCE_ID,
            [p for p in source_prerequisites() if p['kind'] in ('enemy_catalog', 'treasure_catalog')])
    from experimental.pikmin2_cave_catalog import parse
    try:
        result = parse(text, set(enemy_ids), set(treasure_ids))
    except ValueError as exc:
        raise ImportContractError('Semantic decode rejected: %s' % exc) from None
    check_floor_coverage(
        [dict(first_floor=f['first_floor'], last_floor=f['last_floor']) for f in result['floors']],
        expected=EXPECTED_FLOORS)
    if result['floor_count'] != EXPECTED_FLOORS:
        raise ImportContractError('Decoded floor total differs from catalogued stage')
    return result


def starting_population(roster):
    """Validate the native color/maturity roster and total its starting Pikmin."""
    if not isinstance(roster, list) or len(roster) != 7:
        raise ImportContractError('Starting roster must have 7 native color rows')
    rows = []
    for index, row in enumerate(roster):
        if not isinstance(row, list) or len(row) != 3:
            raise ImportContractError('Roster row %d must have 3 maturity columns' % index)
        if any(type(v) is not int or v < 0 for v in row):
            raise ImportContractError('Roster row %d has invalid counts' % index)
        rows.append(dict(color_index=index, leaf=row[0], bud=row[1], flower=row[2], total=sum(row)))
    return dict(source_id=SOURCE_ID, rows=rows, total=sum(r['total'] for r in rows))


def cross_check_catalog(details, roster=None):
    """Compare candidate stage metadata against the catalogued baseline pins."""
    if not isinstance(details, dict):
        raise ImportContractError('Stage details mapping required')
    mismatches = [k for k in EXPECTED_DETAILS if details.get(k) != EXPECTED_DETAILS[k]]
    if roster is not None and roster != EXPECTED_PIKMIN_ROSTER:
        mismatches.append('pikmin_by_native_color_and_maturity')
    if mismatches:
        raise ImportContractError('Catalogue mismatch: ' + ', '.join(sorted(mismatches)))
    return dict(source_id=SOURCE_ID, checked_fields=sorted(EXPECTED_DETAILS) + ['pikmin_roster'],
                mismatches=[], match=True)


def stage_contract(details, roster):
    """Metadata-only contract: spray, timer and starting-roster pins."""
    cross_check_catalog(details, roster)
    population = starting_population(roster)
    return dict(source_id=SOURCE_ID, schema=SCHEMA, metadata_only=True,
                floors=EXPECTED_FLOORS, floor_seconds=list(EXPECTED_DETAILS['floor_seconds']),
                bitter_sprays=EXPECTED_DETAILS['bitter_sprays'],
                spicy_sprays=EXPECTED_DETAILS['spicy_sprays'],
                ui_index=EXPECTED_DETAILS['ui_index'], table_order=EXPECTED_DETAILS['table_order'],
                starting_population=population,
                unsupported_references=list(UNSUPPORTED_REFERENCES),
                limitations=['Roster and sprays are definitions, not runtime actor counts.',
                             'No playability or Challenge-mode completion claim in P0.'])


def resource_closure_requirements(structure):
    """Exact retail inputs still needed for full resource closure."""
    floors = structure.get('floors') if isinstance(structure, dict) else None
    if not floors:
        raise ImportContractError('Decoded structure with floors required')
    pools = []
    for floor in floors:
        pool = floor.get('unit_pool_path')
        if pool and pool not in pools:
            pools.append(pool)
    if not pools:
        raise ImportContractError('No unit pools referenced; nothing to close')
    pending = [{'unit_pool': p,
                'needs': [p, ARC_BASE + '/<unit>/arc.szs', ARC_BASE + '/<unit>/texts.szs'],
                'note': 'unit names resolve only after pool text is read from disc'} for p in pools]
    return dict(source_id=SOURCE_ID, unit_pools=pools, pending_unit_payloads=pending,
                closed=False, missing=source_prerequisites(),
                unsupported_references=list(UNSUPPORTED_REFERENCES),
                limitations=['Weights/counts are definition inputs, not spawn instances or placements.',
                             'No seeded topology, hole selection, radial distribution or restart identity is generated.'])


def audit_packet(details, roster=None, source_bytes=None, expected_sha256=SOURCE_SHA256):
    """Assemble the P0 audit packet; byte decode only when source is present."""
    record = dict(schema=SCHEMA, source_id=SOURCE_ID, source_path=SOURCE_PATH,
                  expected_sha256=SOURCE_SHA256, catalog=cross_check_catalog(details, roster),
                  unsupported_references=list(UNSUPPORTED_REFERENCES),
                  limitations=['Metadata is not runtime acceptance.',
                               'No native build, gameplay, or playability claim in P0.'])
    if source_bytes is None:
        record.update(decoded=False, missing_prerequisites=source_prerequisites(), coverage=None)
        return record
    record.update(source=verify_source(source_bytes, expected_sha256))
    decoded = decode_structure(source_bytes.decode('shift_jis'))
    record.update(decoded=True, structure=decoded,
                  coverage=check_floor_coverage(decoded['floors']),
                  resource_closure=resource_closure_requirements(decoded))
    return record


# ---------------------------------------------------------------------------
# P1 runtime-import path (lane p2-challenge-ch-nari-08tobasare-p1, gen 2).
# Reuses this module's real-source decode helpers above; no forked parser.
# Validates a P0-decoded stage manifest and stages a private run layout.
# No runtime is executed here; all six gates stay UNTESTED unless genuinely
# observed by a later runtime run.
# ---------------------------------------------------------------------------

import argparse
import json
import sys
from pathlib import Path as _Path

P1_SCHEMA = "p2-challenge-ch-nari-08tobasare-p1-v1"
P1_EXPECTED_FLOORS = EXPECTED_FLOORS
P1_EXPECTED_SECONDS = [150.0, 100.0]
P1_EXPECTED_TOTAL = 50
P1_EXPECTED_CELLS = [(0, 2), (1, 2), (3, 2)]
P1_EXPECTED_SPRAYS = {"bitter": 2, "spicy": 0}
P1_EXPECTED_UI = 24


def validate_p1_manifest(manifest):
    """Check a P0 manifest carries everything the P1 import needs."""
    if not isinstance(manifest, dict):
        raise ImportContractError("P1 manifest must be a mapping")
    if manifest.get("cave_id") != SOURCE_ID:
        raise ImportContractError("P1 stage mismatch")
    floors = manifest.get("floors")
    if not isinstance(floors, list) or len(floors) != P1_EXPECTED_FLOORS:
        raise ImportContractError("P1 needs exactly the %d decoded floors" % P1_EXPECTED_FLOORS)
    staged = []
    for n, floor in enumerate(floors, 1):
        if not isinstance(floor, dict):
            raise ImportContractError("P1 floor malformed")
        for key in ("unit_pool", "enemies", "treasures"):
            if key not in floor:
                raise ImportContractError("P1 floor missing field")
        if not isinstance(floor["enemies"], list) or not floor["enemies"]:
            raise ImportContractError("P1 floor has no enemy roster")
        if not isinstance(floor["unit_pool"], str) or not floor["unit_pool"]:
            raise ImportContractError("P1 floor has no unit pool")
        staged.append({
            "number": n,
            "unit_pool": floor["unit_pool"],
            "enemies": [e["source_token"] for e in floor["enemies"]],
            "treasures": [t["treasure_id"] for t in floor["treasures"]],
        })
    population = starting_population(manifest.get("starting_roster"))
    if population["total"] != P1_EXPECTED_TOTAL:
        raise ImportContractError("P1 starting squad total must be %d" % P1_EXPECTED_TOTAL)
    rows = manifest["starting_roster"]
    for color, maturity in P1_EXPECTED_CELLS:
        if rows[color][maturity] <= 0:
            raise ImportContractError("P1 roster missing pinned cell [%d][%d]" % (color, maturity))
    timers = manifest.get("floor_seconds")
    if not isinstance(timers, list) or [float(v) for v in timers] != P1_EXPECTED_SECONDS:
        raise ImportContractError("P1 floor timers must preserve %s" % (P1_EXPECTED_SECONDS,))
    sprays = manifest.get("sprays", {})
    if not isinstance(sprays, dict):
        raise ImportContractError("P1 sprays malformed")
    if int(sprays.get("bitter", -1)) != 2 or int(sprays.get("spicy", -1)) != 0:
        raise ImportContractError("P1 sprays must preserve bitter 2 / spicy 0")
    if manifest.get("ui_index") != P1_EXPECTED_UI:
        raise ImportContractError("P1 ui_index must preserve 24")
    return {
        "cave_id": SOURCE_ID,
        "floors": staged,
        "squad_total": population["total"],
        "floor_seconds": [float(v) for v in timers],
        "sprays": {"bitter": int(sprays.get("bitter", 0)),
                   "spicy": int(sprays.get("spicy", 0))},
        "ui_index": int(manifest.get("ui_index", 0)),
    }


def stage_run_layout(manifest, output):
    """Validate the manifest and write the private P1 run layout."""
    staging = validate_p1_manifest(manifest)
    output = _Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = {}

    def write(name, payload):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        (output / name).write_text(text, encoding="utf-8")
        files[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()

    write("stage-manifest.json", manifest)
    write("p1-input-package.json", {
        "schema": P1_SCHEMA,
        "cave_id": staging["cave_id"],
        "floors": staging["floors"],
        "squad_total": staging["squad_total"],
        "floor_seconds": staging["floor_seconds"],
        "sprays": staging["sprays"],
        "ui_index": staging["ui_index"],
    })
    write("run-plan.json", {
        "schema": P1_SCHEMA,
        "order": [
            "boot private runtime with the input package (fresh arena, starting-Pikmin overlay, centred 960x540)",
            "captain guard FIRST (orimaDead/NaviDead/HP<=1, CAPTAIN_DOWN + BLOCKED, parked captain)",
            "observe live starting squad (no immediate extinction)",
            "observe actual collision/routes/actors per floor with receipt-parseable markers",
            "record honest six-gate evidence; no playability claim beyond observed evidence",
        ],
        "gates": "all six UNTESTED unless genuinely observed",
    })
    return {"files": files, "cave_id": staging["cave_id"],
            "floors": len(staging["floors"])}


def p1_main(manifest_path, output):
    """Stage the run layout from a manifest file on disk."""
    manifest_path = _Path(manifest_path)
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ImportContractError("P1 manifest unreadable: %s" % exc) from None
    result = stage_run_layout(manifest, _Path(output))
    print("P1 staged cave=%s floors=%d files=%s" % (
        result["cave_id"], result["floors"], sorted(result["files"])))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stage the ch_NARI_08tobasare P1 run layout")
    parser.add_argument("manifest", help="P0-decoded stage manifest JSON")
    parser.add_argument("output", help="private run-layout directory")
    args = parser.parse_args(argv)
    p1_main(args.manifest, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
