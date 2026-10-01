"""ch_MAT_yellow_purple_white isolated metadata/import-contract adapter
(lane p2-challenge-ch_mat_yellow_purple_white, #552).

P0 only: source audit support and the import contract a future P1 decoder
must satisfy. No native build, no runtime, no placement fabrication, no
admission claims, no English title guesses (source ID and UI index are
authoritative).

The expected stage metadata is read at runtime from the checked-in
canonical baseline (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane details
plus docs/PIKMIN2_CONTENT_INVENTORY.json challenge stages), never
hardcoded here, so this adapter cannot drift from the reviewed baseline.
The actual disc source
(user/Mukki/mapunits/caveinfo/ch_MAT_yellow_purple_white.txt, US GPVE01
rev 0) is located and hash-pinned when present: a present file whose
sha256 differs from the recorded pin fails closed as the wrong revision.
When absent, the exact missing prerequisite fails closed instead of
inventing values.
"""
import hashlib
import json
from pathlib import Path

CAVE_ID = 'ch_MAT_yellow_purple_white'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_MAT_yellow_purple_white.txt'
ISSUE = 552
LANE = 'p2-challenge-ch_mat_yellow_purple_white'

# Recorded source pin (plan + inventory agree; checked at runtime).
RECORDED_SHA256 = 'f6359e35e4fc27c5ef428ad3666cf419d2b93dc5a5877ba52fc8df0dc5ea94ae'

# Where the disc source was documented for prior lanes (read-only lookup;
# absence is the normal P0 outcome, reported as a prerequisite, not an error
# in this module's logic).
DOCUMENTED_ISO = 'output/pikmin2-runtime/pikmin2-source-test.iso'

# Challenge stage metadata keys, in canonical inventory order.
DETAIL_KEYS = ('table_order', 'cave_id', 'cave_path', 'floors',
               'pikmin_by_native_color_and_maturity', 'legacy_time',
               'bitter_sprays', 'spicy_sprays', 'treasure_count_field',
               'ui_index', 'floor_seconds', 'issue')

# Manifest keys a decoded stage may carry; anything resembling runtime
# placement state is refused outright (weighted definitions are never
# emitted as fabricated placements, scores, or results).
FORBIDDEN_MANIFEST_KEYS = ('placements', 'actors', 'spawn_layout',
                           'scores', 'results')


class MissingPrerequisite(FileNotFoundError):
    """The disc source (or its import tree) is not available locally."""


class ContractViolation(ValueError):
    """A decoded manifest (or present file) disagrees with the baseline."""


def workspace_root():
    """Repository root derived from this file's reserved location."""
    return Path(__file__).resolve().parents[2]


def _read_json(path):
    with Path(path).open('r', encoding='utf-8') as stream:
        return json.load(stream)


def plan_details(root=None):
    """This lane's stage details from the canonical lane plan."""
    root = Path(root) if root is not None else workspace_root()
    plan = _read_json(root / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
    for lane in plan['lanes']:
        if lane.get('lane') == LANE:
            details = lane.get('details')
            if not isinstance(details, dict):
                raise ContractViolation('lane has no details mapping')
            return details
    raise ContractViolation('lane missing from canonical plan')


def inventory_stage(root=None):
    """This stage's entry from the canonical content inventory."""
    root = Path(root) if root is not None else workspace_root()
    inventory = _read_json(root / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    for stage in inventory['challenge']['stages']:
        if stage.get('cave_id') == CAVE_ID:
            return stage
    raise ContractViolation('stage missing from canonical inventory')


def baseline_details(root=None):
    """Agreed stage metadata: plan and inventory must describe the same stage.

    Returns the plan's details after cross-checking every challenge field
    against the inventory entry, including the recorded source pin. Any
    drift fails closed instead of picking a side.
    """
    plan = plan_details(root)
    inv = inventory_stage(root)
    for key in DETAIL_KEYS:
        if plan.get(key) != inv.get(key):
            raise ContractViolation(
                'stage key %r drifts between plan and inventory' % (key,))
    root = Path(root) if root is not None else workspace_root()
    inventory = _read_json(root / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    pinned = inventory.get('source_sha256', {}).get(SOURCE_PATH)
    if pinned != RECORDED_SHA256:
        raise ContractViolation(
            'recorded source pin drift for %s: %r' % (SOURCE_PATH, pinned))
    if plan.get('cave_path') != SOURCE_PATH or inv.get('cave_path') != SOURCE_PATH:
        raise ContractViolation('source path drift for challenge 20')
    return plan


def _check_roster_matrix(matrix, where):
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row)
                   for row in matrix)):
        raise ContractViolation(
            '%s must be a 7x3 non-negative int matrix' % (where,))
    return [list(row) for row in matrix]


def _check_seconds(values, floors, where):
    if (not isinstance(values, list) or len(values) != floors
            or any(type(v) is not float
                   or not (v > 0) for v in values)):
        raise ContractViolation(
            '%s must list one positive seconds value per floor' % (where,))
    return [float(v) for v in values]


def resource_closure(details=None, root=None):
    """Everything a P1 importer must stage: roster, sprays, timer, floor.

    Native color/maturity rows are preserved verbatim; totals are derived
    sums, never placements. No actors, scores, or results are emitted.
    """
    spec = details if details is not None else baseline_details(root)
    matrix = _check_roster_matrix(spec['pikmin_by_native_color_and_maturity'],
                                  'pikmin_by_native_color_and_maturity')
    seconds = _check_seconds(spec['floor_seconds'], spec['floors'], 'floor_seconds')
    total = sum(sum(row) for row in matrix)
    return {
        'cave_id': CAVE_ID,
        'floors': spec['floors'],
        'floor_seconds': seconds,
        'pikmin_by_native_color_and_maturity': matrix,
        'pikmin_total': total,
        'bitter_sprays': spec['bitter_sprays'],
        'spicy_sprays': spec['spicy_sprays'],
        'legacy_time': float(spec['legacy_time']),
        'treasure_count_field': spec['treasure_count_field'],
        'table_order': spec['table_order'],
        'ui_index': spec['ui_index'],
    }


def locate_source(asset_root):
    """Find and hash-pin the disc source under an asset root.

    Returns {'path', 'sha256', 'bytes'}. A present file whose hash
    differs from the recorded pin raises ContractViolation (wrong
    revision). An absent file raises MissingPrerequisite naming the exact
    expected relative path, the searched root, the recorded pin and the
    documented ISO fallback. Never invents content.
    """
    candidate = Path(asset_root) / Path(*SOURCE_PATH.split('/'))
    if not candidate.is_file():
        raise MissingPrerequisite(
            '%s not present under %s '
            '(recorded sha256 %s); documented ISO fallback '
            '%s is also absent; US GPVE01 rev 0 disc (or an '
            'existing import tree) is required before byte decoding '
            '(issue #%d)' % (SOURCE_PATH, Path(asset_root), RECORDED_SHA256,
                             DOCUMENTED_ISO, ISSUE))
    with candidate.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != RECORDED_SHA256:
        raise ContractViolation(
            '%s hashes to %s, not the recorded pin '
            '%s; refusing wrong-revision source' % (candidate, digest, RECORDED_SHA256))
    return {'path': str(candidate), 'sha256': digest,
            'bytes': candidate.stat().st_size}


def validate_manifest(manifest, details=None, root=None):
    """Check a decoded challenge-20 manifest against the canonical baseline.

    Every stage field (table order, UI index, floor count, roster matrix,
    sprays, legacy time, treasure-count field, per-floor seconds) must
    equal the baseline exactly. Runtime-shaped keys (placements, actors,
    spawn layouts, scores, results) are refused outright. Returns a
    normalized coverage report; raises ContractViolation naming the exact
    field on any deviation.
    """
    if not isinstance(manifest, dict):
        raise ContractViolation('manifest must be a mapping')
    spec = details if details is not None else baseline_details(root)
    if manifest.get('cave_id') != CAVE_ID:
        raise ContractViolation('cave_id must be %r' % (CAVE_ID,))
    for key in ('table_order', 'ui_index', 'floors', 'bitter_sprays',
                'spicy_sprays', 'treasure_count_field'):
        value = manifest.get(key)
        if type(value) is not int or value != spec[key]:
            raise ContractViolation('manifest %s must be %r' % (key, spec[key]))
    if type(manifest.get('legacy_time')) is not float or manifest.get('legacy_time') != spec['legacy_time']:
        raise ContractViolation(
            'manifest legacy_time must be %r' % (spec['legacy_time'],))
    got_seconds = manifest.get('floor_seconds')
    _check_seconds(got_seconds, spec['floors'], 'floor_seconds')
    if got_seconds != [float(v) for v in spec['floor_seconds']]:
        raise ContractViolation(
            'manifest floor_seconds must be %r' % (spec['floor_seconds'],))
    got_matrix = manifest.get('pikmin_by_native_color_and_maturity')
    _check_roster_matrix(got_matrix, 'pikmin_by_native_color_and_maturity')
    if got_matrix != spec['pikmin_by_native_color_and_maturity']:
        raise ContractViolation(
            'manifest pikmin_by_native_color_and_maturity differs from baseline')
    for key in FORBIDDEN_MANIFEST_KEYS:
        if key in manifest:
            raise ContractViolation(
                'manifest %s refused: stage definitions are not runtime state' % (key,))
    return {'cave_id': CAVE_ID,
            'table_order': spec['table_order'],
            'ui_index': spec['ui_index'],
            'floors': spec['floors'],
            'pikmin_total': sum(sum(row) for row in got_matrix),
            'complete': True}


def summarize(root=None, asset_root=None):
    """P0 packet: baseline agreement, closure, and source availability.

    'source' is either the located hash-pinned file record or the exact
    missing prerequisite string. Nothing here claims playability or
    admission.
    """
    spec = baseline_details(root)
    closure = resource_closure(spec, root)
    try:
        source = locate_source(asset_root) if asset_root is not None else None
    except (MissingPrerequisite, ContractViolation) as error:
        source = {'unavailable': str(error)}
    if source is None:
        source = {'unavailable': (
            'no asset root supplied; %s unchecked (issue #%d)' % (SOURCE_PATH, ISSUE))}
    return {
        'lane': LANE,
        'issue': ISSUE,
        'cave_id': CAVE_ID,
        'source_path': SOURCE_PATH,
        'source_sha256': RECORDED_SHA256,
        'closure': closure,
        'source': source,
        'playable': False,
    }
