"""forest_3 isolated metadata/import-contract adapter (lane p2-cave-forest_3, #156).

P0 only: source audit support and the import contract a future P1 decoder
must satisfy. No native build, no runtime, no placement fabrication, no
admission claims.

The expected floor/roster metadata is read at runtime from the checked-in
canonical baseline (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane entry plus
docs/PIKMIN2_CONTENT_INVENTORY.json story_caves), never hardcoded here, so
this adapter cannot drift from the reviewed baseline. The actual disc
source (user/Mukki/mapunits/caveinfo/forest_3.txt, US GPVE01 rev 0) is
located and hashed when present; when absent the exact missing
prerequisite fails closed instead of inventing values.

Token classification is structural only: ``$``-prefixed tokens are
generator variants, ``_``-suffixed tokens are explicitly unresolved
carrier candidates (roster/family owners resolve them), anything else is
an exact identity. Empty or non-string tokens are malformed. No English
display names are guessed and no token is silently dropped.
"""
import hashlib
import json
from pathlib import Path

CAVE_ID = 'forest_3'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/forest_3.txt'
ISSUE = 156
LANE = 'p2-cave-forest_3'

# Where the disc source was documented for prior lanes (read-only lookup;
# absence is the normal P0 outcome, reported as a prerequisite, not an error
# in this module's logic).
DOCUMENTED_ISO = 'output/pikmin2-runtime/pikmin2-source-test.iso'

FORBIDDEN_MANIFEST_KEYS = ('placements', 'actors', 'spawn_layout')


class MissingPrerequisite(FileNotFoundError):
    """The disc source (or its import tree) is not available locally."""


class ContractViolation(ValueError):
    """A decoded manifest disagrees with the canonical baseline."""


def workspace_root():
    """Repository root derived from this file's reserved location."""
    return Path(__file__).resolve().parents[2]


def _read_json(path):
    with Path(path).open('r', encoding='utf-8') as stream:
        return json.load(stream)


def plan_lane(root=None):
    """This lane's entry from the canonical lane plan (KeyError if absent)."""
    root = Path(root) if root is not None else workspace_root()
    plan = _read_json(root / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
    for lane in plan['lanes']:
        if lane.get('lane') == LANE:
            return lane
    raise ContractViolation(f'lane {LANE} missing from canonical plan')


def inventory_cave(root=None):
    """This cave's entry from the canonical content inventory."""
    root = Path(root) if root is not None else workspace_root()
    inventory = _read_json(root / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    for cave in inventory['story_caves']:
        if cave.get('id') == CAVE_ID:
            return cave
    raise ContractViolation(f'cave {CAVE_ID} missing from canonical inventory')


def baseline_floors(root=None):
    """Agreed floor rows: plan and inventory must describe the same cave.

    Returns the plan's floor list after cross-checking floor numbers,
    unit pools and token sets against the inventory entry. Any drift
    fails closed instead of picking a side.
    """
    plan_floors = plan_lane(root)['details']['floors']
    inv_floors = inventory_cave(root)['floors']
    if len(plan_floors) != len(inv_floors):
        raise ContractViolation(
            f'floor count drift: plan={len(plan_floors)} inventory={len(inv_floors)}')
    for index, (plan_floor, inv_floor) in enumerate(zip(plan_floors, inv_floors)):
        for key in ('first', 'last', 'unit_pool', 'enemy_ids', 'treasure_ids'):
            if plan_floor.get(key) != inv_floor.get(key):
                raise ContractViolation(
                    f'floor row {index} key {key!r} drifts between plan and inventory')
    numbers = [(row['first'], row['last']) for row in plan_floors]
    if [first for first, _ in numbers] != list(range(1, len(numbers) + 1)):
        raise ContractViolation(f'floors are not contiguous 1..N: {numbers}')
    if any(last != first for first, last in numbers):
        raise ContractViolation(f'non-singleton floor range: {numbers}')
    return plan_floors


def classify_token(token):
    """Structural roster-token class; never resolves or drops a token.

    Returns one of ``exact``, ``generator_variant`` (``$``-prefixed) or
    ``suffixed_unresolved`` (``_``-carrying carrier candidate whose head
    needs a roster/family owner). Empty, blank or non-string tokens raise
    ContractViolation.
    """
    if not isinstance(token, str) or not token.strip():
        raise ContractViolation(f'malformed roster token: {token!r}')
    if token.startswith('$'):
        if len(token) < 2:
            raise ContractViolation(f'malformed variant token: {token!r}')
        return 'generator_variant'
    if '_' in token:
        return 'suffixed_unresolved'
    return 'exact'


def resource_closure(floors=None, root=None):
    """Everything a P1 importer must resolve: sorted token/pool sets.

    No counts are emitted as placements: weighted definitions stay
    definitions, per the lane contract.
    """
    rows = floors if floors is not None else baseline_floors(root)
    enemies, treasures, pools = set(), set(), set()
    for row in rows:
        pools.add(row['unit_pool'])
        enemies.update(row['enemy_ids'])
        treasures.update(row['treasure_ids'])
    classified = {}
    for token in sorted(enemies):
        classified[token] = classify_token(token)
    return {
        'cave_id': CAVE_ID,
        'floor_count': len(rows),
        'unit_pools': sorted(pools),
        'enemy_tokens': sorted(enemies),
        'treasure_tokens': sorted(treasures),
        'token_class': classified,
        'unresolved': sorted(t for t, c in classified.items() if c != 'exact'),
    }


def locate_source(asset_root):
    """Find and hash the disc source under an asset root.

    Returns ``{'path', 'sha256', 'bytes'}``. Raises MissingPrerequisite
    naming the exact expected relative path, the searched root and the
    documented ISO fallback when the file is absent. Never invents content.
    """
    candidate = Path(asset_root) / Path(*SOURCE_PATH.split('/'))
    if not candidate.is_file():
        raise MissingPrerequisite(
            f'{SOURCE_PATH} not present under {Path(asset_root)}; '
            f'documented ISO fallback {DOCUMENTED_ISO} is also absent; '
            f'US GPVE01 rev 0 disc (or an existing import tree) is required '
            f'before byte decoding (issue #{ISSUE})')
    with candidate.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(candidate), 'sha256': digest, 'bytes': candidate.stat().st_size}


def validate_manifest(manifest, floors=None, root=None):
    """Check a decoded forest_3 manifest against the canonical baseline.

    The manifest must carry exactly the 7 singleton floors 1..7 in order,
    each with the baseline unit pool and the exact baseline token sets —
    no missing entries, no extras. ``placements``/``actors``/``spawn_layout``
    keys are refused outright: weighted definitions must never be emitted
    as fabricated runtime placements. Returns a normalized coverage report;
    raises ContractViolation naming the exact field on any deviation.
    """
    if not isinstance(manifest, dict):
        raise ContractViolation('manifest must be a mapping')
    if manifest.get('cave_id') != CAVE_ID:
        raise ContractViolation(f"cave_id must be {CAVE_ID!r}")
    rows = manifest.get('floors')
    if not isinstance(rows, list):
        raise ContractViolation('manifest floors must be a list')
    expected = floors if floors is not None else baseline_floors(root)
    if len(rows) != len(expected):
        raise ContractViolation(
            f'floor coverage {len(rows)} != baseline {len(expected)}')
    coverage = []
    for position, (row, want) in enumerate(zip(rows, expected)):
        where = f'floors[{position}]'
        if not isinstance(row, dict):
            raise ContractViolation(f'{where} must be a mapping')
        if row.get('number') != want['first']:
            raise ContractViolation(
                f"{where}.number must be {want['first']}")
        if row.get('unit_pool') != want['unit_pool']:
            raise ContractViolation(
                f"{where}.unit_pool must be {want['unit_pool']!r}")
        for key in ('enemy_ids', 'treasure_ids'):
            got = row.get(key)
            if not isinstance(got, list) or any(not isinstance(t, str) for t in got):
                raise ContractViolation(f'{where}.{key} must be a string list')
            if sorted(got) != sorted(want[key]):
                raise ContractViolation(
                    f'{where}.{key} differs from baseline: '
                    f'missing={sorted(set(want[key]) - set(got))} '
                    f'extra={sorted(set(got) - set(want[key]))}')
            for token in got:
                classify_token(token)
        for key in FORBIDDEN_MANIFEST_KEYS:
            if key in row:
                raise ContractViolation(
                    f'{where}.{key} refused: weighted definitions are not runtime placements')
        coverage.append({'number': row['number'], 'unit_pool': row['unit_pool'],
                         'enemies': len(row['enemy_ids']),
                         'treasures': len(row['treasure_ids'])})
    return {'cave_id': CAVE_ID, 'floors': coverage,
            'complete': len(coverage) == len(expected)}


def summarize(root=None, asset_root=None):
    """P0 packet: baseline agreement, closure, and source availability.

    ``source`` is either the located file record or the exact missing
    prerequisite string. Nothing here claims playability or admission.
    """
    rows = baseline_floors(root)
    closure = resource_closure(rows, root)
    try:
        source = locate_source(asset_root) if asset_root is not None else None
    except MissingPrerequisite as error:
        source = {'missing_prerequisite': str(error)}
    if source is None:
        source = {'missing_prerequisite': (
            f'no asset root supplied; {SOURCE_PATH} unchecked (issue #{ISSUE})')}
    return {
        'lane': LANE,
        'issue': ISSUE,
        'cave_id': CAVE_ID,
        'source_path': SOURCE_PATH,
        'floor_count': len(rows),
        'unit_pools': closure['unit_pools'],
        'enemy_tokens': closure['enemy_tokens'],
        'treasure_tokens': closure['treasure_tokens'],
        'token_class': closure['token_class'],
        'unresolved_tokens': closure['unresolved'],
        'source': source,
        'playable': False,
    }
