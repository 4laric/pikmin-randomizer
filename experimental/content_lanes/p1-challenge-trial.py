"""P1 Challenge Trial isolated metadata/import-contract adapter
(lane p1-challenge-trial, #567).

P0 only: source audit support and the import contract a future P1 decoder
must satisfy. No native build, no runtime, no placement fabrication, no
admission claims. Story-destination (#100) and timed-campaign (#52)
contracts stay separate; the level key stays qualified despite the shared
native area ID.

The expected destination identity is read at runtime from the checked-in
canonical baseline (docs/PIKMIN_CONTENT_IMPORT_LANES.json lane details
plus experimental/levels.py native destination table), never hardcoded
here, so this adapter cannot drift from the reviewed baseline. The actual
P1 source (stages/chal4.ini under a P1 dataDir asset root) is located,
structurally decoded, and hashed when present; when absent the exact
missing prerequisite fails closed instead of inventing values.

The decoder is structural only: top-level scalar directives
(navi_start, map_file, day_multiply), the dayMgr timesetting sequence,
and the new_room starting-room record. Values are preserved verbatim;
lighting rigs, fog, and per-setting blocks are counted, never
interpreted. Unknown top-level directives are explicit unsupported
references, never silently dropped or guessed.
"""
import hashlib
import json
from pathlib import Path

LEVEL_KEY = 'challenge:trial'
SOURCE_PATH = 'stages/chal4.ini'
ISSUE = 567
LANE = 'p1-challenge-trial'

# Where the P1 source was observed for prior lanes (read-only lookup;
# absence is a normal outcome, reported as a prerequisite, not an error
# in this module's logic).
DOCUMENTED_ASSETS = 'C:/Users/alari/bbft/dist/cohesion/pikmin/assets'

# Decoded-manifest keys a stage decode may carry; anything resembling
# runtime state (placements, scores, checks, receipts) is refused outright.
FORBIDDEN_MANIFEST_KEYS = ('placements', 'actors', 'spawn_layout',
                           'scores', 'results', 'checks', 'receipts')

# Top-level scalar directives this adapter decodes. Anything else at
# depth 0 is an explicit unsupported reference.
KNOWN_DIRECTIVES = ('navi_start', 'map_file', 'day_multiply')

# Top-level blocks this adapter decodes. Anything else at depth 0 is an
# explicit unsupported reference.
KNOWN_BLOCKS = ('dayMgr', 'new_room')


class MissingPrerequisite(FileNotFoundError):
    """The P1 asset root (or its stages tree) is not available locally."""


class ContractViolation(ValueError):
    """A decoded manifest (or present file) disagrees with the baseline."""


def workspace_root():
    """Repository root derived from this file's reserved location."""
    return Path(__file__).resolve().parents[2]


def _read_json(path):
    with Path(path).open('r', encoding='utf-8') as stream:
        return json.load(stream)


def plan_details(root=None):
    """This lane's destination details from the canonical lane plan."""
    root = Path(root) if root is not None else workspace_root()
    plan = _read_json(root / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
    for lane in plan['lanes']:
        if lane.get('lane') == LANE:
            details = lane.get('details')
            if not isinstance(details, dict):
                raise ContractViolation('lane has no details mapping')
            return details
    raise ContractViolation('lane missing from canonical plan')


def native_level(root=None):
    """The shared native destination row for challenge:trial (read-only)."""
    root = Path(root) if root is not None else workspace_root()
    import sys
    saved = sys.path.insert(0, str(root))
    try:
        from experimental.levels import BY_KEY
        level = BY_KEY.get(LEVEL_KEY)
    finally:
        sys.path.remove(str(root))
    if level is None:
        raise ContractViolation('native destination row missing for trial')
    return level


def baseline_details(root=None):
    """Agreed destination identity: plan and native table must describe it.

    Returns the plan's details after cross-checking the level key, the
    native area ID, the stage-info index rule (16 + area ID), the track
    list, and the stage file path against the shared native destination
    row. Any drift fails closed instead of picking a side.
    """
    details = plan_details(root)
    level = native_level(root)
    if details.get('level_key') != LEVEL_KEY or level.key != LEVEL_KEY:
        raise ContractViolation('level key drift for trial')
    if type(details.get('native_area_id')) is not int:
        raise ContractViolation('native_area_id must be an int')
    if details['native_area_id'] != level.area_id:
        raise ContractViolation('native area ID drift for trial')
    if details.get('stage_info_index') != 16 + level.area_id:
        raise ContractViolation('stage-info index rule drift for trial')
    tracks = details.get('tracks')
    if (not isinstance(tracks, list) or len(tracks) != 2
            or any(not isinstance(t, str) or not t.strip() for t in tracks)
            or len(set(tracks)) != 2):
        raise ContractViolation('trial must carry two distinct track strings')
    if level.stage_file != SOURCE_PATH:
        raise ContractViolation('native stage file drift for trial')
    return details


def _strip_comment(line):
    cut = line.find('//')
    return line[:cut] if cut >= 0 else line


def decode_stage(text):
    """Structurally decode a P1 stage ini (e.g. chal4.ini).

    Returns {'directives': {key: [tokens]}, 'blocks': [names in order],
    'timesettings': [ints in order], 'new_room': {...} or None,
    'unsupported': [depth-0 names not in the known sets]}. Comment text
    never participates. Unknown depth-0 names are listed, never dropped;
    brace imbalance raises ContractViolation.
    """
    directives = {}
    blocks = []
    timesettings = []
    new_room = None
    unsupported = []
    depth = 0
    current = None
    room = None
    for raw in text.splitlines():
        line = _strip_comment(raw).strip()
        if not line:
            continue
        if line == '{':
            depth += 1
            continue
        if line == '}':
            depth -= 1
            if depth < 0:
                raise ContractViolation('unbalanced closing brace')
            if depth == 0 and current == 'new_room':
                new_room = room
                current = None
                room = None
            elif depth == 0:
                current = None
            continue
        parts = line.split()
        if parts[-1] == '{':
            name = parts[0]
            if depth == 0:
                blocks.append(name)
                if name in KNOWN_BLOCKS:
                    current = name
                    if name == 'new_room':
                        room = {}
                else:
                    unsupported.append(name)
                    current = None
            elif depth == 1 and current == 'dayMgr' and name == 'timesetting':
                if len(parts) != 3:
                    raise ContractViolation('malformed timesetting opener')
                try:
                    timesettings.append(int(parts[1]))
                except ValueError:
                    raise ContractViolation('non-integer timesetting index')
            depth += 1
            continue
        if depth == 0:
            key, values = parts[0], parts[1:]
            if key in KNOWN_DIRECTIVES:
                if key in directives:
                    raise ContractViolation('duplicate directive %r' % (key,))
                directives[key] = values
            else:
                unsupported.append(key)
        elif depth == 1 and current == 'new_room':
            room[parts[0]] = parts[1:]
    if depth != 0:
        raise ContractViolation('unbalanced braces in stage file')
    return {'directives': directives, 'blocks': blocks,
            'timesettings': timesettings, 'new_room': new_room,
            'unsupported': unsupported}


def _numbers(values, where, count):
    if len(values) != count:
        raise ContractViolation('%s must carry %d numbers' % (where, count))
    try:
        return [float(v) for v in values]
    except ValueError:
        raise ContractViolation('%s carries non-numeric values' % (where,))


def resource_closure(decoded, asset_root=None):
    """Everything a P1 importer must resolve: spawn, map model, rooms, days.

    The map_file model path is checked against the asset root when one is
    supplied (resolved flag + checked path); otherwise it stays explicitly
    unchecked. day_multiply, timesetting coverage vs numsettings, and the
    new_room starting record are preserved verbatim.
    """
    directives = decoded['directives']
    for key in KNOWN_DIRECTIVES:
        if key not in directives:
            raise ContractViolation('decoded stage missing %r' % (key,))
    navi = _numbers(directives['navi_start'], 'navi_start', 2)
    model = directives['map_file']
    if len(model) != 1:
        raise ContractViolation('map_file must name one model path')
    day = _numbers(directives['day_multiply'], 'day_multiply', 1)[0]
    model_checked = None
    model_resolved = None
    if asset_root is not None:
        model_checked = str(Path(asset_root) / 'dataDir' / Path(*model[0].split('/')))
        model_resolved = Path(model_checked).is_file()
    room = decoded['new_room']
    if room is None:
        raise ContractViolation('decoded stage missing new_room')
    closure = {
        'level_key': LEVEL_KEY,
        'navi_start': navi,
        'map_model': model[0],
        'map_model_checked': model_checked,
        'map_model_resolved': model_resolved,
        'day_multiply': day,
        'timesettings': list(decoded['timesettings']),
        'new_room': {k: list(v) for k, v in room.items()},
        'unsupported': list(decoded['unsupported']),
    }
    return closure


def locate_source(asset_root):
    """Find and hash the P1 stage source under a P1 asset root.

    Looks up dataDir/stages/chal4.ini (the observed P1 layout). Returns
    {'path', 'sha256', 'bytes'}. Absence raises MissingPrerequisite naming
    the exact expected relative path, the searched root, and issue #567.
    Never invents content. (P1 pins are recorded observations, not
    canonical plan pins: the plan keeps P1 source hashes null by design.)
    """
    candidate = Path(asset_root) / 'dataDir' / 'stages' / 'chal4.ini'
    if not candidate.is_file():
        raise MissingPrerequisite(
            'stages/chal4.ini not present under %s/dataDir/stages '
            '(documented P1 assets %s unchecked here); '
            'a legal P1 asset root is required before byte decoding '
            '(issue #%d)' % (Path(asset_root), DOCUMENTED_ASSETS, ISSUE))
    with candidate.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': str(candidate), 'sha256': digest,
            'bytes': candidate.stat().st_size}


def validate_manifest(manifest, decoded, observed_sha256, details=None, root=None):
    """Check a decoded trial manifest against baseline + observed source.

    Identity (level key, area ID, stage-info index, tracks), the observed
    file hash, and every decoded field (spawn, model, days, timesettings,
    starting room) must match exactly. Runtime-shaped keys are refused
    outright. Returns a normalized coverage report; raises
    ContractViolation naming the exact field on any deviation.
    """
    if not isinstance(manifest, dict):
        raise ContractViolation('manifest must be a mapping')
    spec = details if details is not None else baseline_details(root)
    if manifest.get('level_key') != LEVEL_KEY:
        raise ContractViolation('cave level_key must be %r' % (LEVEL_KEY,))
    if manifest.get('native_area_id') != spec['native_area_id']:
        raise ContractViolation('native_area_id must be %r' % (spec['native_area_id'],))
    if manifest.get('stage_info_index') != spec['stage_info_index']:
        raise ContractViolation('stage_info_index must be %r' % (spec['stage_info_index'],))
    if manifest.get('tracks') != spec['tracks']:
        raise ContractViolation('tracks must equal the baseline pair exactly')
    if manifest.get('source_sha256') != observed_sha256:
        raise ContractViolation('manifest source hash must equal the observed file hash')
    for key in FORBIDDEN_MANIFEST_KEYS:
        if key in manifest:
            raise ContractViolation(
                'manifest %s refused: stage definitions are not runtime state' % (key,))
    if not isinstance(decoded, dict):
        raise ContractViolation('decoded stage must be a mapping')
    for key in ('navi_start', 'map_model', 'day_multiply', 'timesettings', 'new_room'):
        if manifest.get(key) != decoded.get(key):
            raise ContractViolation('manifest %s differs from decoded source' % (key,))
    if decoded.get('unsupported'):
        raise ContractViolation(
            'decoded source carries unsupported references: %r' % (decoded['unsupported'],))
    return {'level_key': LEVEL_KEY,
            'stage_info_index': spec['stage_info_index'],
            'source_sha256': observed_sha256,
            'complete': True}


def summarize(root=None, asset_root=None):
    """P0 packet: baseline agreement, decoded closure, source availability.

    When an asset root is supplied the real file is located, hashed,
    decoded, and closed over; otherwise 'source' carries the exact
    missing prerequisite. Nothing here claims playability or admission.
    """
    spec = baseline_details(root)
    if asset_root is None:
        return {
            'lane': LANE, 'issue': ISSUE, 'level_key': LEVEL_KEY,
            'source_path': SOURCE_PATH, 'details': spec,
            'source': {'unavailable': (
                'no asset root supplied; %s unchecked (issue #%d)' % (SOURCE_PATH, ISSUE))},
            'playable': False,
        }
    try:
        record = locate_source(asset_root)
    except MissingPrerequisite as error:
        return {
            'lane': LANE, 'issue': ISSUE, 'level_key': LEVEL_KEY,
            'source_path': SOURCE_PATH, 'details': spec,
            'source': {'unavailable': str(error)},
            'playable': False,
        }
    text = Path(record['path']).read_text(encoding='utf-8', errors='replace')
    decoded = decode_stage(text)
    closure = resource_closure(decoded, asset_root)
    manifest = {'level_key': LEVEL_KEY,
                'native_area_id': spec['native_area_id'],
                'stage_info_index': spec['stage_info_index'],
                'tracks': list(spec['tracks']),
                'source_sha256': record['sha256'],
                'navi_start': closure['navi_start'],
                'map_model': closure['map_model'],
                'day_multiply': closure['day_multiply'],
                'timesettings': closure['timesettings'],
                'new_room': closure['new_room']}
    report = validate_manifest(manifest, closure, record['sha256'], spec, root)
    return {
        'lane': LANE, 'issue': ISSUE, 'level_key': LEVEL_KEY,
        'source_path': SOURCE_PATH, 'details': spec,
        'source': record, 'closure': closure,
        'manifest_report': report, 'playable': False,
    }