"""P0 import-contract adapter for Valley of Repose (tutorial overworld), issue #148.

Lane p2-overworld-tutorial, phase P0 only: source audit and additive import
contract. This module consumes the existing stage-table parser
(:func:`experimental.pikmin2_regional_audit.stage_cave_links`, itself framed by
``gameStages.cpp CourseInfo::read``), the brace-stream reader
(:func:`experimental.pikmin2_cave.tree`) and the shared disc reader
(:func:`experimental.pikmin2_assets.disc_files`). It forks no generator and
emits no runtime placements: weighted generator rows remain definitions,
never actor counts or coordinates.

Source identity: ``user/Abe/stages.txt`` on a US GPVE01 revision 0 disc. A
legal local disc is present on this host and the file is extracted read-only
through ``disc_files`` (verified 3275 bytes, sha256
``4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8``).
The canonical inventory records no hash for this path, so the observed hash
is carried as an observed pin, not a recorded one. When the source is
absent, manifests record ``source_sha256: 'unknown'`` plus the exact missing
prerequisite and no value is invented.
"""

import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_cave import tree
from experimental.pikmin2_regional_audit import stage_cave_links

LANE = 'p2-overworld-tutorial'
COURSE_ID = 'tutorial'
LABEL = 'Valley of Repose'
ISSUE = 148
SOURCE_PATH = 'user/Abe/stages.txt'
MAP_SOURCES = ('user/Kando/map/tutorial', 'user/Abe/map/tutorial')
DISC_IDENTITY = 'US GPVE01 revision 0'

# Exact lane-plan contract (docs/PIKMIN_CONTENT_IMPORT_LANES.json).
REQUIRED_INVENTORY = (
    'terrain/collision/water',
    'generator day schedules and regrowth',
    'buried/enemy-held treasure',
    'Onions/ship/bridges/gates',
    'all cave entrances and return anchors',
)
RUNTIME_DEPENDENCIES = (128, 130, 131, 132, 140, 144, 145, 146)

# Story caves this surface owns (canonical inventory story_caves ids). The
# stage table also registers a non-story `test` entry; that is recorded but
# not counted as story coverage.
STORY_CAVES = (
    ('tutorial_1', 'tutorial_1.txt'),
    ('tutorial_2', 'tutorial_2.txt'),
    ('tutorial_3', 'tutorial_3.txt'),
)

# Runtime framework contracts that block P1/P2 (lane-plan issue refs). P0
# resolves none of them; they are reported, never claimed.
BLOCKERS = (
    {'issue': 128, 'contract': 'actor/asset source closure'},
    {'issue': 130, 'contract': 'actor/asset source closure'},
    {'issue': 131, 'contract': 'actor/asset source closure'},
    {'issue': 132, 'contract': 'surface days, saves and progression identity'},
    {'issue': 140, 'contract': 'actor/asset/species source closure'},
    {'issue': 144, 'contract': 'actor/asset/species source closure'},
    {'issue': 145, 'contract': 'actor/asset/species source closure'},
    {'issue': 146, 'contract': 'actor/asset/species source closure'},
)

MISSING_PREREQUISITE = (
    "Legal US Pikmin 2 disc image (GPVE01 rev 0) or an extracted "
    "'user/Abe/stages.txt' file. Provide the bytes to decode_stages() or the "
    "path to decode_source_file(); nothing is staged from weighted "
    "definitions and no hash is invented."
)

# Supported local retail ISO observed on this host; callers may override.
DEFAULT_ISO = Path('C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso')

_DAY_RANGE = re.compile(r'^(\d+)-(\d+)$')
_HEX64 = re.compile(r'^[0-9a-f]{64}$')


def sha256_bytes(data):
    """SHA-256 of raw source bytes; rejects non-bytes/empty input."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise ValueError('source bytes required')
    return hashlib.sha256(bytes(data)).hexdigest()


def source_prerequisite():
    """Return the exact prerequisite that real source decoding requires.

    The canonical inventory pins no hash for ``user/Abe/stages.txt``; callers
    must supply the disc (or its extracted bytes) before any hash or coverage
    claim. This is a boundary description, not a download instruction: local
    assets are never redistributed.
    """
    return {
        'source': SOURCE_PATH,
        'disc': DISC_IDENTITY,
        'header': 'First six bytes GPVE01, byte 7 revision 0 '
                  '(enforced by experimental.pikmin2_assets.disc_files)',
        'recorded_sha256': None,
        'status': 'missing-local-source',
        'supply': 'Provide a locally owned US GPVE01 revision 0 disc image; '
                  'read user/Abe/stages.txt through disc_files() and record '
                  'its SHA-256 in the manifest. Keep the image and all '
                  'extracted bytes local and ignored.',
    }


def missing_prerequisite():
    return MISSING_PREREQUISITE


def locate_source(iso_path=None):
    """Locate the legal retail ISO, or report the exact prerequisite."""
    iso = Path(iso_path) if iso_path is not None else DEFAULT_ISO
    if not iso.is_file():
        return {'available': False, 'iso': None,
                'prerequisite': MISSING_PREREQUISITE}
    return {'available': True, 'iso': str(iso), 'prerequisite': None}


def extract_source_from_iso(iso_path=None):
    """Read ``user/Abe/stages.txt`` bytes from the local ISO (read-only).

    Uses the shared ``disc_files`` reader (which enforces the US GPVE01
    revision 0 header). Raises when the ISO or the source member is absent.
    """
    found = locate_source(iso_path)
    if not found['available']:
        raise FileNotFoundError(MISSING_PREREQUISITE)
    from experimental.pikmin2_assets import disc_files
    iso = Path(found['iso'])
    catalog = disc_files(iso)
    if SOURCE_PATH not in catalog:
        raise ValueError('Missing disc source: ' + SOURCE_PATH)
    offset, length = catalog[SOURCE_PATH]
    with iso.open('rb') as disc:
        disc.seek(offset)
        data = disc.read(length)
    if len(data) != length:
        raise ValueError('Truncated disc source: ' + SOURCE_PATH)
    return data


def decode_stages(data):
    """Decode raw ``stages.txt`` bytes to text (Shift-JIS, nonempty)."""
    if not isinstance(data, (bytes, bytearray)):
        raise ValueError('stages.txt input must be bytes')
    if not data:
        raise ValueError('stages.txt input is empty')
    return bytes(data).decode('shift_jis')


def tutorial_links(links):
    """Select the tutorial course's cave links from parsed stage links.

    Raises when the tutorial course has no link: an absent course is a
    source/parse gap, never an empty manifest.
    """
    selected = [dict(link) for link in links
                if link.get('course_id') == COURSE_ID]
    if not selected:
        raise ValueError('No tutorial course links in stage table')
    return selected


def classify_links(links):
    """Annotate tutorial links with story-cave identity and classification.

    A link whose filename is a known story cave is ``story`` with its
    ``story_cave_id``; every other registered entry (the retail ``test``
    placeholder) is ``registered_non_story``. Links keep table order.
    """
    story_by_filename = {filename: cave_id
                         for cave_id, filename in STORY_CAVES}
    result = []
    for link in links:
        row = dict(link)
        cave_id = story_by_filename.get(row.get('filename'))
        row['story_cave_id'] = cave_id
        row['classification'] = 'story' if cave_id else 'registered_non_story'
        result.append(row)
    return result


def _course_block(text, course_id):
    """Return the raw course block for ``course_id`` (exactly one)."""
    nodes = tree(text)
    if not nodes or not isinstance(nodes[0], str) or not nodes[0].isdigit():
        raise ValueError('Stage table course count mismatch')
    blocks = nodes[1:]
    if int(nodes[0]) != len(blocks):
        raise ValueError('Stage table course count mismatch')
    matches = []
    for block in blocks:
        if not isinstance(block, list):
            raise ValueError('Invalid stage course record')
        fields, at = {}, 0
        while at < len(block) and block[at] != 'end':
            key = block[at]
            width = 3 if key == 'start' else 1
            if (not isinstance(key, str) or key in fields
                    or at + width >= len(block)):
                raise ValueError('Invalid stage course header')
            fields[key] = block[at + 1:at + width + 1]
            at += width + 1
        if 'name' not in fields:
            raise ValueError('Missing stage course name')
        if fields['name'][0] == course_id:
            matches.append((block, at))
    if not matches:
        raise ValueError('No tutorial course in stage table')
    if len(matches) > 1:
        raise ValueError('Duplicate tutorial course in stage table')
    return matches[0]


def tutorial_header(text):
    """Decode the tutorial course header fields verbatim.

    Returns the authored folder/model/collision/waterbox/mapcode/route names
    and the declared start position/angle. These are source coordinates from
    the table, not engine-observed placements.
    """
    block, at = _course_block(text, COURSE_ID)
    header = {}
    cursor = 0
    while cursor < at:
        key = block[cursor]
        width = 3 if key == 'start' else 1
        header[key] = list(block[cursor + 1:cursor + width + 1])
        cursor += width + 1
    if 'name' not in header or 'start' not in header:
        raise ValueError('Tutorial course header missing name/start')
    if len(header['start']) != 3:
        raise ValueError('Tutorial start position is not three values')
    return {
        'name': header['name'][0],
        'folder': header.get('folder', [None])[0],
        'abe_folder': header.get('abe_folder', [None])[0],
        'model': header.get('model', [None])[0],
        'collision': header.get('collision', [None])[0],
        'waterbox': header.get('waterbox', [None])[0],
        'mapcode': header.get('mapcode', [None])[0],
        'route': header.get('route', [None])[0],
        'start': [float(v) for v in header['start']],
        'startangle': float(header.get('startangle', ['0'])[0]),
    }


def tutorial_generator_schedules(text):
    """Decode the two authored generator tables for the tutorial course.

    ``CourseInfo::read`` stores a non-loop then a loop ``LimitGenInfo``
    table; each row is a generator filename plus three day values. The
    filename stem ``A-B`` is cross-checked against the observed day window,
    so a misparse fails closed instead of emitting invented schedules.
    Weighted generator definitions are not expanded here.
    """
    block, at = _course_block(text, COURSE_ID)
    at += 1
    schedules = []
    for kind in ('nonloop', 'loop'):
        if at >= len(block) or not block[at].isdigit():
            raise ValueError('Missing stage generator table')
        count = int(block[at])
        end = at + 1 + 4 * count
        if end > len(block):
            raise ValueError('Truncated stage generator table')
        rows = block[at + 1:end]
        for index in range(count):
            filename, *fields = rows[4 * index:4 * (index + 1)]
            if (not isinstance(filename, str) or not filename.endswith('.txt')
                    or len(fields) != 3
                    or any(not re.fullmatch(r'-?\d+', f) for f in fields)):
                raise ValueError('Invalid generator schedule row')
            first_day, last_day = int(fields[0]), int(fields[1])
            stem = filename[:-4]
            match = _DAY_RANGE.match(stem)
            if match and (int(match.group(1)) != first_day
                          or int(match.group(2)) != last_day):
                raise ValueError('Generator filename/day window mismatch')
            schedules.append({
                'kind': kind,
                'table_index': index,
                'filename': filename,
                'first_day': first_day,
                'last_day': last_day,
                'raw_fields': [int(field) for field in fields],
            })
        at = end
    if not schedules:
        raise ValueError('No tutorial generator schedules')
    return schedules


def tutorial_surface_total(text):
    """Read the tutorial course's trailing surface treasure total.

    This is the declared ground-treasure count field the issue tracks
    (retail value 7 for tutorial), read with the same ``CourseInfo::read``
    framing :func:`stage_cave_links` enforces: header terminator, two
    generator tables (count + four fields each), the cave table, then exactly
    one trailing count. It is a declared total, not a set of placements.
    """
    block, at = _course_block(text, COURSE_ID)
    at += 1
    for _ in range(2):  # Nonloop and loop generator tables.
        if at >= len(block) or not block[at].isdigit():
            raise ValueError('Missing stage generator table')
        end = at + 1 + 4 * int(block[at])
        if end > len(block):
            raise ValueError('Truncated stage generator table')
        at = end
    if at >= len(block) or not block[at].isdigit():
        raise ValueError('Missing stage cave table')
    end = at + 1 + 3 * int(block[at])
    if end > len(block):
        raise ValueError('Truncated stage cave table')
    at = end
    if at != len(block) - 1 or not block[at].isdigit():
        raise ValueError('Missing tutorial surface treasure total')
    return int(block[at])


def story_cave_coverage(links):
    """Report which canonical story caves the tutorial stages table links.

    ``complete`` is true only when every ``STORY_CAVES`` filename appears
    exactly once; a missing or duplicated story cave fails coverage.
    """
    by_filename = {}
    for link in links:
        by_filename.setdefault(link.get('filename'), []).append(link)
    rows = []
    for cave_id, filename in STORY_CAVES:
        matches = by_filename.get(filename, [])
        rows.append({
            'story_cave_id': cave_id,
            'filename': filename,
            'source_path': 'user/Mukki/mapunits/caveinfo/' + filename,
            'link_count': len(matches),
            'linked': len(matches) == 1,
        })
    return {
        'rows': rows,
        'complete': all(row['linked'] for row in rows),
    }


def resource_closure(links, stages_sha256=None, cave_hashes=None,
                     header=None):
    """List every source file this entry needs, with hashes where known."""
    cave_hashes = dict(cave_hashes or {})
    closure = [{'path': SOURCE_PATH, 'sha256': stages_sha256,
                'status': 'hashed' if stages_sha256 else 'hash_unvalidated'}]
    seen = set()
    for link in links:
        path = link['source_path']
        if path in seen:
            continue
        seen.add(path)
        digest = cave_hashes.get(path)
        closure.append({'path': path, 'sha256': digest,
                        'status': 'hashed' if digest else 'hash_unvalidated'})
    for path in (MAP_SOURCES if header is None
                 else (header.get('folder'), header.get('abe_folder'))):
        if path and path not in seen:
            seen.add(path)
            closure.append({'path': path, 'sha256': None,
                            'status': 'referenced_unvalidated'})
    return closure


def _valid_hash(value):
    return isinstance(value, str) and bool(_HEX64.match(value))


def build_manifest(text, links, source_sha256=None, cave_hashes=None):
    """Build the tutorial P0 manifest from decoded text and parsed links.

    ``source_sha256`` is the hex digest of the exact bytes decoded, or None
    when the source is unavailable (recorded honestly as ``'unknown'``).
    The manifest carries authored metadata only: course header, generator
    schedules, cave links with story coverage, and the declared surface
    total. It contains no runtime placements.
    """
    if source_sha256 is not None and not _valid_hash(source_sha256):
        raise ValueError('source_sha256 must be 64 lowercase hex or None')
    selected = classify_links(tutorial_links(links))
    header = tutorial_header(text)
    schedules = tutorial_generator_schedules(text)
    total = tutorial_surface_total(text)
    coverage = story_cave_coverage(selected)
    if not coverage['complete']:
        raise ValueError('Tutorial story cave coverage is incomplete')
    missing = [dict(source_prerequisite())] if source_sha256 is None else []
    inventory = {}
    for item in REQUIRED_INVENTORY:
        if item == 'generator day schedules and regrowth':
            inventory[item] = {
                'status': 'metadata_decoded',
                'detail': 'Nonloop and loop schedule tables decoded from '
                          'stages.txt (filename + day window); weighted '
                          'definitions and regrowth behavior stay source data.',
            }
        elif item == 'all cave entrances and return anchors':
            inventory[item] = {
                'status': 'metadata_decoded',
                'detail': 'All canonical tutorial story caves linked from the '
                          'stage table; entrance positions and return anchors '
                          'need map tables and #132.',
            }
        else:
            inventory[item] = {
                'status': 'open',
                'detail': 'Source metadata recorded; runtime conversion/'
                          'admission still blocked (see blockers).',
            }
    manifest = {
        'schema': 1,
        'lane': LANE,
        'course': COURSE_ID,
        'label': LABEL,
        'issue': ISSUE,
        'source': SOURCE_PATH,
        'disc_identity': DISC_IDENTITY,
        'source_sha256': source_sha256 if source_sha256 is not None else 'unknown',
        'stages_sha256': source_sha256,
        'course_header': header,
        'generator_schedules': schedules,
        'cave_count': len(selected),
        'cave_links': selected,
        'story_caves': coverage['rows'],
        'story_coverage_complete': coverage['complete'],
        'surface_treasure_total': total,
        'required_inventory': inventory,
        'resource_closure': resource_closure(selected, source_sha256,
                                             cave_hashes, header),
        'runtime_dependencies': list(RUNTIME_DEPENDENCIES),
        'blockers': [dict(entry) for entry in BLOCKERS],
        'placement_policy': ('no runtime placements emitted; weighted '
                             'generator definitions stay source data, never '
                             'actor counts'),
        'playable': False,
        'missing_prerequisites': missing,
        'limitations': [
            'Metadata only: course header, generator schedules, cave links '
            'and the declared surface total. Not runtime acceptance, not '
            'playability.',
            'No actor placements, terrain, water, routes, saves or receipts '
            'are established by this manifest.',
        ],
    }
    return validate_manifest(manifest)


def validate_manifest(manifest):
    """Fail closed on invented, incomplete or drifted tutorial manifests."""
    if not isinstance(manifest, dict) or manifest.get('schema') != 1:
        raise ValueError('Manifest schema must be 1')
    for key, expected in (('lane', LANE), ('course', COURSE_ID),
                          ('issue', ISSUE), ('source', SOURCE_PATH)):
        if manifest.get(key) != expected:
            raise ValueError('Manifest identity differs: ' + key)
    sha = manifest.get('source_sha256')
    if sha != 'unknown' and not _valid_hash(sha):
        raise ValueError('Manifest source hash must be 64 hex or unknown')
    if sha == 'unknown' and not manifest.get('missing_prerequisites'):
        raise ValueError('Unknown source hash requires a missing prerequisite')
    if manifest.get('stages_sha256') != (None if sha == 'unknown' else sha):
        raise ValueError('Manifest stages_sha256 must mirror source_sha256')
    header = manifest.get('course_header')
    if (not isinstance(header, dict) or header.get('name') != COURSE_ID
            or not isinstance(header.get('start'), list)
            or len(header['start']) != 3):
        raise ValueError('Manifest course header is invalid')
    schedules = manifest.get('generator_schedules')
    if not isinstance(schedules, list) or not schedules:
        raise ValueError('Manifest needs generator schedules')
    for row in schedules:
        if (not isinstance(row, dict) or row.get('kind') not in ('nonloop', 'loop')
                or not isinstance(row.get('filename'), str)
                or not row['filename'].endswith('.txt')
                or type(row.get('first_day')) is not int
                or type(row.get('last_day')) is not int
                or row['first_day'] > row['last_day']):
            raise ValueError('Manifest has an invalid generator schedule row')
    links = manifest.get('cave_links')
    if not isinstance(links, list) or not links:
        raise ValueError('Manifest needs at least one tutorial cave link')
    seen = set()
    for link in links:
        if not isinstance(link, dict) or link.get('course_id') != COURSE_ID:
            raise ValueError('Manifest link is not a tutorial course link')
        tag, filename, path = (link.get('cave_tag'), link.get('filename'),
                               link.get('source_path'))
        if (not isinstance(tag, str) or not (3 <= len(tag) <= 4)
                or not isinstance(filename, str)
                or not filename.endswith('.txt')
                or path != 'user/Mukki/mapunits/caveinfo/' + filename):
            raise ValueError('Manifest link has an invalid cave reference')
        if (tag, filename) in seen:
            raise ValueError('Manifest has a duplicate cave link')
        seen.add((tag, filename))
        if link.get('classification') not in ('story', 'registered_non_story'):
            raise ValueError('Manifest link lacks a classification')
        if link.get('classification') == 'story' and not link.get('story_cave_id'):
            raise ValueError('Story-classified link needs a story_cave_id')
        if link.get('classification') == 'registered_non_story' and link.get('story_cave_id'):
            raise ValueError('Non-story link must not claim a story_cave_id')
        for banned in ('placements', 'coordinates', 'actors', 'spawns'):
            if banned in link:
                raise ValueError('Manifest link fabricates runtime data: ' + banned)
    story = manifest.get('story_caves')
    expected_ids = {cave_id for cave_id, _ in STORY_CAVES}
    if (not isinstance(story, list)
            or {row.get('story_cave_id') for row in story} != expected_ids):
        raise ValueError('Manifest story cave coverage differs from the lane contract')
    if manifest.get('story_coverage_complete') is not all(
            row.get('linked') for row in story):
        raise ValueError('Manifest story coverage flag disagrees with rows')
    if not all(row.get('linked') for row in story):
        raise ValueError('Manifest story cave coverage is incomplete')
    if manifest.get('cave_count') != len(links):
        raise ValueError('Manifest cave_count disagrees with cave_links')
    total = manifest.get('surface_treasure_total')
    if type(total) is not int or total < 0:
        raise ValueError('Surface treasure total must be a non-negative integer')
    inventory = manifest.get('required_inventory')
    if (not isinstance(inventory, dict)
            or sorted(inventory) != sorted(REQUIRED_INVENTORY)):
        raise ValueError('Manifest required inventory differs from the lane plan')
    closure = manifest.get('resource_closure')
    if not isinstance(closure, list) or not closure:
        raise ValueError('Manifest needs a resource closure')
    if closure[0].get('path') != SOURCE_PATH:
        raise ValueError('Resource closure must start with the stages source')
    for row in closure:
        if (not isinstance(row, dict) or not isinstance(row.get('path'), str)
                or row.get('status') not in ('hashed', 'hash_unvalidated',
                                             'referenced_unvalidated')):
            raise ValueError('Invalid resource closure row')
        if row['status'] == 'hashed' and not _valid_hash(row.get('sha256')):
            raise ValueError('Hashed closure row needs a 64-hex digest')
    if manifest.get('runtime_dependencies') != list(RUNTIME_DEPENDENCIES):
        raise ValueError('Manifest runtime dependencies differ from the lane plan')
    blockers = manifest.get('blockers')
    if not isinstance(blockers, list) or {b.get('issue') for b in blockers} != set(RUNTIME_DEPENDENCIES):
        raise ValueError('Manifest blockers differ from the lane plan')
    if manifest.get('playable') is not False:
        raise ValueError('P0 manifest must not claim playability')
    for banned in ('placements', 'coordinates', 'actors', 'spawns'):
        if banned in manifest:
            raise ValueError('Manifest fabricates runtime data: ' + banned)
    if not manifest.get('limitations'):
        raise ValueError('Manifest must state its limitations')
    return manifest


def decode_source_file(path):
    """Decode a real extracted stages.txt file into a hashed manifest."""
    raw = Path(path).read_bytes()
    return build_manifest(raw.decode('shift_jis'), stage_cave_links(
        raw.decode('shift_jis')), source_sha256=sha256_bytes(raw))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stages', type=Path, default=None,
                        help='path to extracted user/Abe/stages.txt')
    parser.add_argument('--iso', type=Path, default=None,
                        help='read user/Abe/stages.txt from this ISO instead')
    parser.add_argument('--output', type=Path, default=None,
                        help='write manifest JSON here (otherwise stdout)')
    args = parser.parse_args(argv)
    if args.stages is not None:
        raw = args.stages.read_bytes()
    elif args.iso is not None:
        raw = extract_source_from_iso(args.iso)
    else:
        raw = extract_source_from_iso()
    text = decode_stages(raw)
    manifest = build_manifest(text, stage_cave_links(text),
                              source_sha256=sha256_bytes(raw))
    payload = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    if args.output is None:
        print(payload, end='')
    else:
        args.output.write_text(payload, encoding='utf-8')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
