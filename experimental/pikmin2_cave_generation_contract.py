"""Read-only surface checker for the P2 cave generation seam
(lane cave-generation-contract-review, issue #129).

Stdlib only; never imports engine code. It probes C++ source TEXT for the
P2_CAVE_* log markers and pc_p2_cave_* entry points the provider contract
requires, so a generator owner (or reviewer) can verify the seam surface
without building. Line citations live in the review doc, pinned to the
audited engine export; this checker reports presence per marker, never
gameplay acceptance.

A surface probe cannot distinguish a marker inside a comment from a real
emission; pinned line citations in the review doc are the human-verified
record. Anything this checker reports must be confirmed there.
"""
import re

# Markers the P1 provider contract requires on the generation seam. Each is
# emitted by engine/pc_port/pc_p2_cave.cpp in the audited export; the review
# doc pins the exact lines.
REQUIRED_MARKERS = (
    'P2_CAVE_READY',
    'P2_CAVE_RESTORE',
    'P2_CAVE_TRANSFER',
    'P2_CAVE_ANCHOR',
    'P2_CAVE_NAV',
    'P2_CAVE_VISUAL_READY',
)

# Public provider entry points declared in engine/pc_port/pc_p2_cave.h.
ENTRY_POINTS = (
    'pc_p2_cave_setup',
    'pc_p2_cave_tick',
    'pc_p2_cave_request',
    'pc_p2_cave_checkpoint',
    'pc_p2_cave_exit_after_checkpoint',
    'pc_p2_cave_floor',
    'pc_p2_cave_is_beasts',
    'pc_p2_cave_boundary_token',
    'pc_p2_cave_receipt_prefix',
    'pc_p2_cave_draw_transition',
    'pc_p2_cave_interact',
)

_MARKER_RE = re.compile(r'P2_[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+')
_ENTRY_RE = re.compile(r'\b(pc_p2_cave_[A-Za-z_]+)\s*\(')


def _require_text(text):
    if not isinstance(text, str) or not text:
        raise ValueError('source text required')


def find_markers(text):
    """Every P2_* marker token in source text, mapped to 1-based lines."""
    _require_text(text)
    found = {}
    for number, line in enumerate(text.splitlines(), 1):
        for token in _MARKER_RE.findall(line):
            found.setdefault(token, []).append(number)
    return found


def check_seam(text):
    """Required-marker surface report: present / missing lists."""
    found = find_markers(text)
    present = [m for m in REQUIRED_MARKERS if m in found]
    return {'present': present,
            'missing': [m for m in REQUIRED_MARKERS if m not in found],
            'extra': sorted(set(found) - set(REQUIRED_MARKERS))}


def entry_points(text):
    """Provider entry points referenced in source text, in header order."""
    _require_text(text)
    seen = set(_ENTRY_RE.findall(text))
    return [name for name in ENTRY_POINTS if name in seen]


def gap_table():
    """Retail-vs-port generation gap, one row per P1 requirement.

    Each row names the requirement, the retail source behavior, the port
    status in the audited seam, and the bounded owner work item. Values
    are review facts; the review doc carries the citations.
    """
    return [
        {'requirement': 'floor topology from unit pools',
         'retail': 'caveinfo f008 pool + MAP unit rooms/doors assembled per floor',
         'port': 'absent; static preview room only',
         'work': 'add pool selection + room assembly driven by P0 unit manifests'},
        {'requirement': 'enemy/treasure actor spawn from rosters',
         'retail': 'MapRoom::placeObjects births Cave::EnemyNode via generalEnemyMgr',
         'port': 'absent; no caveinfo roster consumer',
         'work': 'add roster-driven spawner on the assembled rooms'},
        {'requirement': 'door/waypoint route graph',
         'retail': 'unit doors/links form the traversable graph',
         'port': 'absent; only hole/geyser anchor radius + Pod fallback',
         'work': 'add route graph from unit door links; extend nav diagnostics'},
        {'requirement': 'hole/geyser placement from source',
         'retail': 'transition geometry per floor from cave data',
         'port': 'staged sidecar file only (p2-cave-transition.txt)',
         'work': 'derive transition anchors from decoded floor data'},
        {'requirement': 'schedules (day/multiply, exit windows)',
         'retail': 'per-floor schedule parameters gate exits',
         'port': 'absent; world clock pinned, no schedule enforcement',
         'work': 'add schedule parameters to the floor manifest consumer'},
        {'requirement': 'squad/descent persistence',
         'retail': 'cave save filter carries squad across floors',
         'port': 'present: P2_CAVE_TRANSFER file + P2_CAVE_RESTORE per member',
         'work': 'none; consume as-is (Bulbmin transition rules preserved)'},
    ]


def review_draft():
    """#186 shared-semantics review request for the generator owner."""
    lines = [
        '#186 review request: cave generation provider seam (issue #129)',
        '',
        'Scope: add retail cave generation behind the existing pc_p2_cave',
        'transfer boundary. No changes to squad restore, checkpoint format,',
        'Bulbmin transition rules, Beasts paths, or nav marker strings.',
        'Files (audited export, engine/pc_port):',
        '- pc_p2_cave.cpp:87 pc_p2_cave_setup (entry-file squad restore),',
        '  :113 P2_CAVE_RESTORE, :143 P2_CAVE_READY, :155 pc_p2_cave_checkpoint,',
        '  :232 P2_CAVE_TRANSFER, :239 pc_p2_cave_tick, :262 pc_p2_cave_draw_transition',
        '- pc_p2_cave.h:4,5,6,7,9,10,11,12,13,15,17 entry declarations',
        '- pc_p2_cave_anchor.h:7 P2CaveAnchor, :20 p2_cave_read_anchor',
        '- pc_p2_cave_entry_policy.h:4 P2CaveEntryProfile, :5 p2_cave_entry_profile',
        'Validation: P0 unit manifests resolve; assembled rooms match pool',
        'geometry; roster spawns match caveinfo minima; existing transfer',
        'files still parse; ninja -n clean; no ADMIT change.',
    ]
    return '\n'.join(lines) + '\n'