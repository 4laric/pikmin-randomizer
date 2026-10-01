"""Lane 04 native placement evidence ingestion (#440, assignment 3).

Turns one observed generated-session run into `p2-placement-v1` slot evidence
and placement gates. The observed run is produced by
``scripts/p2_ordinary_receipt_runtime.py`` and records the real actor spawn XYZ,
the corpse carry route and the Onion position for a naturally killed and
naturally carried host Dwarf Bulborb.

Admission stays default-deny. Only the single campaign slot matching the observed
run is raised, and only the identities the caller explicitly lists get an
accepted placement gate. Everything else keeps ``evidence.* == False`` and
``accepted_gates == []``.

Trust rules (assignment-3 recovery): a document is only accepted when it is
*trustworthy*, which means all values are finite, the Onion is a real non-null
XYZ, the route length is positive, the run carried the corpse to a natural
terminal delivery through the real Onion endpoint (``delivered == True``), the
run was not injected (``injected == False``) and it carries control evidence
(``control_others``, a finite non-negative count of other live enemies in the
scene). A stale or hand-asserted document (null Onion, ``route_length == 0``, or
``delivered`` asserted without control evidence) is rejected.

The observed slot must also match exactly: the observed stage must equal the
slot's stage and the observed XYZ must be within ``MAX_SLOT_MATCH_DISTANCE`` of
the slot position. A nearest-XYZ match without a distance ceiling or with a
stage mismatch is not trusted, so a run can never spuriously raise a slot in a
different stage or on the far side of the map.

The P2 Snow (``YellowKochappy``) and Dwarf Orange (``BlueKochappy``) candidates
reuse the P1 Dwarf Bulborb body, collision and carrying, so the observed host
slot/route is the shared placement evidence for that cohort. The evidence proves
the slot, terrain and carry route only; it does not prove P2 source behavior,
combat or reward semantics (that is assignment 2 / lane 13).
"""
import argparse
import json
import math
from pathlib import Path

from .campaign_data import CAMPAIGN_SLOTS

SCHEMA = 'p2-placement-evidence-v1'
EVIDENCE_KEYS = ('xyz', 'terrain', 'route')
DEFAULT_GATES = ('placement.xyz', 'placement.terrain', 'placement.route', 'reward.onion')
# A run whose observed XYZ is farther than this from the nearest slot position is
# not a match for that slot (it would spuriously raise a far-side slot). The
# observed host Dwarf Bulborb slot sits ~160 units from its generator anchor, so
# the ceiling is well above the in-slot offset and far below the ~500+ unit
# spacing between different stages/slots.
MAX_SLOT_MATCH_DISTANCE = 250.0


def _distance(a, b):
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def _is_finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_triple(value):
    return (isinstance(value, list) and len(value) == 3
            and all(_is_finite(v) for v in value))


def is_trustworthy(data):
    """Return True only when an observed evidence document meets every trust rule.

    This is the single gate used by :func:`load` and :func:`apply_evidence`.
    Trust requires finite XYZ triples for actor_spawn/generator_position/onion, a
    positive finite route_length, a finite non-negative control_others, a natural
    terminal delivery (``delivered`` is True), a non-injected run
    (``injected`` is False) and an ordinary Onion/AP ledger (not the Pod path).
    """
    if not isinstance(data, dict) or data.get('schema') != SCHEMA:
        return False
    if not all(_valid_triple(data.get(key)) for key in ('actor_spawn', 'generator_position', 'onion')):
        return False
    route = data.get('route_length')
    if not _is_finite(route) or route <= 0:
        return False
    control = data.get('control_others')
    if not _is_finite(control) or control < 0:
        return False
    if data.get('delivered') is not True:
        return False
    if data.get('injected') is not False:
        return False
    if data.get('ordinary_ledger') is not True or data.get('pod_ledger') is not False:
        return False
    stage = data.get('stage')
    if not isinstance(stage, int) or isinstance(stage, bool) or stage < 0:
        return False
    return True


def load(path):
    """Load and validate one observed placement evidence document."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != SCHEMA:
        raise ValueError('unsupported placement evidence schema')
    for key in ('actor_spawn', 'generator_position', 'onion'):
        if not _valid_triple(data.get(key)):
            raise ValueError(f'placement evidence {key} must be a finite XYZ triple')
    route = data.get('route_length')
    if not _is_finite(route) or route <= 0:
        raise ValueError('placement evidence route_length must be a finite positive number')
    control = data.get('control_others')
    if not _is_finite(control) or control < 0:
        raise ValueError('placement evidence control_others must be a finite non-negative count')
    if data.get('delivered') is not True:
        raise ValueError('placement evidence must record a natural terminal delivery (delivered=True)')
    if data.get('injected') is not False:
        raise ValueError('placement evidence must not be an injected run (injected=False)')
    if data.get('ordinary_ledger') is not True or data.get('pod_ledger') is not False:
        raise ValueError('placement evidence must be ordinary Onion/AP, not the experimental Pod ledger')
    if not isinstance(data.get('stage'), int) or isinstance(data.get('stage'), bool) or data.get('stage') < 0:
        raise ValueError('placement evidence stage must be a non-negative integer')
    return data


def nearest_campaign_slot(position, campaign_slots=CAMPAIGN_SLOTS):
    """Return the campaign slot row nearest an observed XYZ and its distance."""
    rows = [row for row in campaign_slots if row.get('position')]
    if not rows:
        raise ValueError('no campaign slots carry an extracted XYZ position')
    row = min(rows, key=lambda r: _distance(r['position'], position))
    return row, _distance(row['position'], position)


def match_slot(position, stage, campaign_slots=CAMPAIGN_SLOTS,
               max_distance=MAX_SLOT_MATCH_DISTANCE):
    """Return the unique trustworthy ``(row, distance)`` match for an observed run.

    A run matches a slot only when the observed stage equals the slot stage and
    the observed XYZ is within ``max_distance`` of the slot position. No match
    raises ``ValueError`` so admission is never inferred from a loose nearest-XYZ
    lookup.
    """
    rows = [row for row in campaign_slots
            if row.get('position') and row.get('stage') == stage]
    if not rows:
        raise ValueError(f'no campaign slots on stage {stage}')
    row = min(rows, key=lambda r: _distance(r['position'], position))
    distance = _distance(row['position'], position)
    if distance > max_distance:
        raise ValueError(
            f'observed XYZ {position} is {distance:.1f} units from slot {row["uid"]} '
            f'({row.get("label")}), exceeding max match distance {max_distance}')
    return row, distance


def apply_evidence(document, evidence, identities, gates=DEFAULT_GATES, campaign_slots=CAMPAIGN_SLOTS,
                   max_distance=MAX_SLOT_MATCH_DISTANCE):
    """Raise the observed slot's evidence and the listed identities' gates.

    The document is only accepted when :func:`is_trustworthy` passes and the
    observed run matches exactly one campaign slot by stage and distance. Returns
    a machine-readable summary of exactly what changed. The document is mutated in
    place; callers that need the default-deny baseline can rebuild it with
    :func:`randomizer.p2_placement_catalog.build_document`.
    """
    if not identities:
        raise ValueError('at least one identity must be listed')
    if not is_trustworthy(evidence):
        raise ValueError('placement evidence is not trustworthy (see is_trustworthy)')
    position = evidence['actor_spawn'] or evidence['generator_position']
    row, match = match_slot(position, evidence['stage'], campaign_slots, max_distance)
    slot = next((s for s in document['slots'] if s['uid'] == row['uid']), None)
    if slot is None:
        raise ValueError('observed campaign slot is not in the placement document')
    profiles = []
    for identity in identities:
        profile = next((p for p in document['profiles'] if p['identity'] == identity), None)
        if profile is None:
            raise ValueError(f'unknown placement identity: {identity}')
        profiles.append(profile)
    # Validate the entire request before changing any approval state.
    for key in EVIDENCE_KEYS:
        slot['evidence'][key] = True
    approved = []
    for profile in profiles:
        profile['accepted_gates'] = list(gates)
        approved.append(profile['identity'])
    return {
        'slot_uid': row['uid'],
        'slot_label': row.get('label', str(row['uid'])),
        'slot_stage': row.get('stage'),
        'slot_cohort': row.get('cohort'),
        'observed_position': list(position),
        'slot_position': list(row['position']),
        'match_distance': match,
        'route_length': float(evidence['route_length']),
        'control_others': int(evidence['control_others']),
        'delivered': bool(evidence['delivered']),
        'identities': approved,
        'gates': list(gates),
    }


def publish_evidence(path, evidence):
    """Publish only validated delivery evidence; remove stale prior approvals."""
    path = Path(path)
    if not is_trustworthy(evidence):
        path.unlink(missing_ok=True)
        return False
    path.write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--identities', default='YellowKochappy,BlueKochappy')
    args = parser.parse_args(argv)

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from randomizer import p2_placement as placement
    from randomizer import p2_placement_catalog as catalog

    data = load(args.evidence)
    document = catalog.build_document()
    identities = [name for name in args.identities.split(',') if name]
    summary = apply_evidence(document, data, identities)
    result = placement.audit(document)
    admitted = {identity: uids for identity, uids in result['admitted'].items() if uids}
    args.output.write_text(json.dumps({'summary': summary, 'admitted': admitted}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'summary': summary, 'admitted': admitted}, indent=2))
    return 0 if admitted else 1


if __name__ == '__main__':
    raise SystemExit(main())
