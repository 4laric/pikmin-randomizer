"""P0 import-contract adapter for Valley of Repose (tutorial overworld), issue #148.

Lane p2-overworld-tutorial, phase P0 only: source audit and additive import
contract. This module consumes the existing stage-table parser
(:func:`experimental.pikmin2_regional_audit.stage_cave_links`, itself framed by
``gameStages.cpp CourseInfo::read``) and the brace-stream reader
(:func:`experimental.pikmin2_cave.tree`). It decodes no new binary format,
forks no generator, and emits no runtime placements: weighted generator rows
remain definitions, never actor counts or coordinates.

Source identity: ``user/Abe/stages.txt`` on a US GPVE01 revision 0 disc. The
canonical inventory records no hash for this path
(``source_sha256`` is null in ``docs/PIKMIN_CONTENT_IMPORT_LANES.json``), and
no legal disc source is present on this host, so manifests built here carry
``source_sha256: 'unknown'`` together with the exact missing prerequisite.
No value is invented to fill that gap: every cave link comes from the parsed
table, and the surface treasure total is read from the same table framing.
"""

from experimental.pikmin2_cave import tree
from experimental.pikmin2_regional_audit import stage_cave_links

LANE = 'p2-overworld-tutorial'
COURSE_ID = 'tutorial'
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


def source_prerequisite():
    """Return the exact missing prerequisite for real source decoding.

    No local legal GPVE01 disc source is available on this host and the
    canonical inventory pins no hash for ``user/Abe/stages.txt``; callers
    must supply the disc (or its extracted bytes) before any hash or
    floor-coverage claim. This is a boundary description, not a download
    instruction: local assets are never redistributed.
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


def build_manifest(text, links, source_sha256=None):
    """Build the tutorial P0 manifest from decoded text and parsed links.

    ``source_sha256`` is the hex digest of the exact bytes decoded, or None
    when the source is unavailable (recorded honestly as ``'unknown'``).
    The manifest carries cave links and the declared surface total only;
    generator schedules, terrain, actors and placements stay explicitly open.
    """
    if source_sha256 is not None and (
            not isinstance(source_sha256, str)
            or len(source_sha256) != 64
            or any(c not in '0123456789abcdef' for c in source_sha256)):
        raise ValueError('source_sha256 must be 64 lowercase hex or None')
    selected = tutorial_links(links)
    total = tutorial_surface_total(text)
    missing = [dict(source_prerequisite())] if source_sha256 is None else []
    return {
        'schema': 1,
        'lane': LANE,
        'course': COURSE_ID,
        'issue': ISSUE,
        'source': SOURCE_PATH,
        'source_sha256': source_sha256 if source_sha256 is not None else 'unknown',
        'cave_links': selected,
        'surface_treasure_total': total,
        'required_inventory': {
            'terrain/collision/water': {
                'status': 'open',
                'detail': 'Needs user/Kando/map/tutorial and '
                          'user/Abe/map/tutorial decode plus '
                          'collision/water conversion; runtime deps '
                          '#128 #130 #131.',
            },
            'generator day schedules and regrowth': {
                'status': 'open',
                'detail': 'Generator filename/window rows in stages.txt are '
                          'not yet extracted by any lane parser; bounded '
                          'table decode is a P0 follow-up, schedules stay '
                          'with runtime deps.',
            },
            'buried/enemy-held treasure': {
                'status': 'open',
                'detail': 'Declared surface total recorded; per-instance '
                          'buried/enemy-held state needs map tables and the '
                          '#140 ledger.',
            },
            'Onions/ship/bridges/gates': {
                'status': 'open',
                'detail': 'Map-table fixtures; runtime deps #132 #144 #145.',
            },
            'all cave entrances and return anchors': {
                'status': 'metadata',
                'detail': 'Cave tags/filenames linked from the stage table; '
                          'entrance positions and return anchors need map '
                          'tables and #132.',
            },
        },
        'runtime_dependencies': list(RUNTIME_DEPENDENCIES),
        'missing_prerequisites': missing,
        'limitations': [
            'Metadata only: cave links plus the declared surface total. '
            'Not runtime acceptance, not playability.',
            'No generator coordinates, actor placements, terrain, water, '
            'routes, saves or receipts are established by this manifest.',
        ],
    }


def validate_manifest(manifest):
    """Fail closed on invented, incomplete or drifted tutorial manifests."""
    if not isinstance(manifest, dict) or manifest.get('schema') != 1:
        raise ValueError('Manifest schema must be 1')
    for key, expected in (('lane', LANE), ('course', COURSE_ID),
                          ('issue', ISSUE), ('source', SOURCE_PATH)):
        if manifest.get(key) != expected:
            raise ValueError('Manifest identity differs: ' + key)
    sha = manifest.get('source_sha256')
    if sha != 'unknown' and not (
            isinstance(sha, str) and len(sha) == 64
            and all(c in '0123456789abcdef' for c in sha)):
        raise ValueError('Manifest source hash must be 64 hex or unknown')
    if sha == 'unknown' and not manifest.get('missing_prerequisites'):
        raise ValueError('Unknown source hash requires a missing prerequisite')
    links = manifest.get('cave_links')
    if not isinstance(links, list) or not links:
        raise ValueError('Manifest needs at least one tutorial cave link')
    seen = set()
    for link in links:
        if not isinstance(link, dict) or link.get('course_id') != COURSE_ID:
            raise ValueError('Manifest link is not a tutorial course link')
        tag, filename, path = (link.get('cave_tag'), link.get('filename'),
                               link.get('source_path'))
        if (not isinstance(tag, str) or len(tag) != 4
                or not isinstance(filename, str)
                or not filename.endswith('.txt')
                or path != 'user/Mukki/mapunits/caveinfo/' + filename):
            raise ValueError('Manifest link has an invalid cave reference')
        if (tag, filename) in seen:
            raise ValueError('Manifest has a duplicate cave link')
        seen.add((tag, filename))
        for banned in ('placements', 'coordinates', 'actors', 'spawns'):
            if banned in link:
                raise ValueError('Manifest link fabricates runtime data: ' + banned)
    total = manifest.get('surface_treasure_total')
    if type(total) is not int or total < 0:
        raise ValueError('Surface treasure total must be a non-negative integer')
    inventory = manifest.get('required_inventory')
    if (not isinstance(inventory, dict)
            or sorted(inventory) != sorted(REQUIRED_INVENTORY)):
        raise ValueError('Manifest required inventory differs from the lane plan')
    if manifest.get('runtime_dependencies') != list(RUNTIME_DEPENDENCIES):
        raise ValueError('Manifest runtime dependencies differ from the lane plan')
    for banned in ('placements', 'coordinates', 'actors', 'spawns', 'playable'):
        if banned in manifest:
            raise ValueError('Manifest fabricates runtime data: ' + banned)
    if not manifest.get('limitations'):
        raise ValueError('Manifest must state its limitations')
    return manifest
