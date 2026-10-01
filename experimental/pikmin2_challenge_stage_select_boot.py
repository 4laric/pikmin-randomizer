"""Stage-selectable boot path probe + minimal selector candidate for P2
ch_NARI_01kusachi (lane challenge-stage-select-boot, issue #669).

PROBE VERDICT (read-only findings, no invented selection): no existing
fixture selects a P2 caveinfo stage. `--experimental-challenge-level`
(engine/pc_port/pc_bbft.cpp:47-52) accepts exactly one char 0-4 mapped to
P1 area IDs; P2 ui_index 3 would collide with P1 semantics (area 3), so it
cannot address ch_NARI_01kusachi. The host-mode module (#651,
native/pc_port/pc_p2_challenge_mode.{h,cpp} on its lane branch, NOT in
maintained HEAD) carries pure `selectByUiIndex` logic with no maintained
registration and no engine boot hook of its own. The guarded fixture
(#649) constrains inputs to SLOT_RE `^chal[0-4]$` (P1 stages only).

MINIMAL SELECTOR CANDIDATE (this module, root-side only): `select_stage`
validates a P2 stage key against the canonical plan + inventory pins and
returns the boot-selection record a future native hook consumes;
`render_boot_request` serializes it as P2_CHALLENGE_STAGE_SELECT_1 text.
No native consumer exists yet -- the precise missing hook is an engine
boot flag accepting a P2 stage key, registration of a decoded P2 stage
table, and a guarded SLOT_RE extension, all requiring owner review before
landing. Nothing here touches #651/shared/native files.
"""
import json
from pathlib import Path

STAGE_KEY = 'ch_NARI_01kusachi'
SOURCE_PATH = 'user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt'
SOURCE_SHA256 = 'b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85'
BOOT_MAGIC = 'P2_CHALLENGE_STAGE_SELECT_1'

FORBIDDEN_PREFIXES = ('chal',)


class SelectionError(ValueError):
    """Refusal to select: unknown key, wrong namespace, or pin drift."""


def workspace_root():
    return Path(__file__).resolve().parents[2]


def _read_json(path):
    try:
        with Path(path).open('r', encoding='utf-8') as stream:
            return json.load(stream)
    except (OSError, ValueError) as error:
        raise SelectionError('unreadable canonical baseline: ' + str(path)) from error


def plan_stage(root=None):
    """This stage's entry from the canonical lane plan."""
    root = Path(root) if root is not None else workspace_root()
    plan = _read_json(root / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
    for lane in plan['lanes']:
        if lane.get('source_id') == STAGE_KEY and lane.get('category') == 'p2-challenge':
            return lane
    raise SelectionError('stage %s missing from canonical plan' % STAGE_KEY)


def inventory_stage(root=None):
    """This stage's entry from the canonical content inventory."""
    root = Path(root) if root is not None else workspace_root()
    inventory = _read_json(root / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    for stage in inventory['challenge']['stages']:
        if stage.get('cave_id') == STAGE_KEY:
            return stage
    raise SelectionError('stage %s missing from canonical inventory' % STAGE_KEY)


def baseline_selection(root=None):
    """Agreed boot-selection fields: plan and inventory must describe one stage.

    Cross-checks cave_id/path, floors, roster, timers, sprays, ui/table
    indices and the recorded source pin. Any drift fails closed.
    """
    lane = plan_stage(root)
    details = lane.get('details') or {}
    inv = inventory_stage(root)
    for key in ('cave_id', 'cave_path', 'floors', 'pikmin_by_native_color_and_maturity',
                'legacy_time', 'bitter_sprays', 'spicy_sprays', 'treasure_count_field',
                'ui_index', 'floor_seconds', 'table_order'):
        if details.get(key) != inv.get(key):
            raise SelectionError('stage key %r drifts between plan and inventory' % (key,))
    if lane.get('source') != SOURCE_PATH or inv.get('cave_path') != SOURCE_PATH:
        raise SelectionError('source path drift for challenge stage')
    root = Path(root) if root is not None else workspace_root()
    inventory = _read_json(root / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    if inventory.get('source_sha256', {}).get(SOURCE_PATH) != SOURCE_SHA256:
        raise SelectionError('recorded source pin drift for %s' % SOURCE_PATH)
    return details


def select_stage(stage_key, root=None):
    """Validate a P2 stage key and return its boot-selection record.

    Only exact p2-challenge cave_ids from the canonical baseline resolve.
    P1 `chal<N>` slots are refused (different namespace, different owner);
    anything else is unknown. Never invents a stage.
    """
    if not isinstance(stage_key, str) or not stage_key:
        raise SelectionError('stage key must be a nonempty string')
    if stage_key != STAGE_KEY:
        if isinstance(stage_key, str) and stage_key.startswith(FORBIDDEN_PREFIXES):
            raise SelectionError('P1 challenge slots are a different namespace (owner: p1-challenge lanes)')
        raise SelectionError('unknown P2 challenge stage: %r' % (stage_key,))
    details = baseline_selection(root)
    matrix = details['pikmin_by_native_color_and_maturity']
    if (not isinstance(matrix, list) or len(matrix) != 7
            or any(not isinstance(row, list) or len(row) != 3
                   or any(type(v) is not int or v < 0 for v in row) for row in matrix)):
        raise SelectionError('baseline roster matrix malformed')
    seconds = details['floor_seconds']
    if (not isinstance(seconds, list) or len(seconds) != details['floors']
            or any(not isinstance(v, (int, float)) or not v > 0 for v in seconds)):
        raise SelectionError('baseline floor timers malformed')
    return {
        'cave_id': STAGE_KEY,
        'cave_path': SOURCE_PATH,
        'source_sha256': SOURCE_SHA256,
        'ui_index': details['ui_index'],
        'table_order': details['table_order'],
        'floors': details['floors'],
        'floor_seconds': [float(v) for v in seconds],
        'pikmin_by_native_color_and_maturity': [list(row) for row in matrix],
        'bitter_sprays': details['bitter_sprays'],
        'spicy_sprays': details['spicy_sprays'],
        'legacy_time': float(details['legacy_time']),
        'treasure_count_field': details['treasure_count_field'],
    }


def render_boot_request(record):
    """Canonical boot-request text for a validated selection record."""
    required = ('cave_id', 'cave_path', 'source_sha256', 'ui_index', 'table_order',
                'floors', 'floor_seconds', 'pikmin_by_native_color_and_maturity',
                'bitter_sprays', 'spicy_sprays', 'legacy_time', 'treasure_count_field')
    missing = [k for k in required if k not in record]
    if missing:
        raise SelectionError('boot record missing fields: %s' % sorted(missing))
    if record['cave_id'] != STAGE_KEY or record['cave_path'] != SOURCE_PATH:
        raise SelectionError('boot record identity mismatch')
    lines = [BOOT_MAGIC,
             'cave %s ui_index %d table_order %d floors %d' % (
                 record['cave_id'], record['ui_index'], record['table_order'], record['floors']),
             'source %s %s' % (record['cave_path'], record['source_sha256']),
             'timers %s legacy %s' % (
                 ' '.join(str(v) for v in record['floor_seconds']), record['legacy_time']),
             'sprays bitter %d spicy %d treasure_field %d' % (
                 record['bitter_sprays'], record['spicy_sprays'], record['treasure_count_field'])]
    for row in record['pikmin_by_native_color_and_maturity']:
        lines.append('roster %d %d %d' % tuple(row))
    return '\n'.join(lines) + '\n'


def missing_hook():
    """The precise missing native hook, for the packet and owner review."""
    return {
        'flag': '--experimental-challenge-stage <cave_id>',
        'table': 'decoded P2 stage table keyed by cave_id (host-mode selectByUiIndex is the pure-logic precedent)',
        'registration': 'maintained CMake/CTest wiring for the selector consumer (cf. #651 owned files, #186 review required)',
        'guarded_slot': 'SLOT_RE extension beyond ^chal[0-4]$ in the #649 input package (owner review required)',
        'note': 'P2 ui_index values live in a different namespace than --experimental-challenge-level 0-4 (P1 area IDs); reusing that flag would misboot P1 spring for ui_index 3',
    }