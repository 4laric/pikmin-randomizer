"""Lane-04 audit bridge: fold native placement-evidence probe output into a
placement document and report the before/after admission decision (#440).

The native probe (``pc_p2_placement_probe``) emits ``P2_PLACEMENT_SLOT`` facts
for the disposable P2 room encounter arena. This script turns a captured
``p2-placement-probe-v1`` JSON into slot ``evidence``, builds a labelled
encounter-arena document for the Snow/Dwarf Orange host cohort, and prints the
deny -> evidence-stamped decision.

The probe ``uid`` is the generator's 4-byte file id (``Generator::_70``), not a
``p2_placement_catalog`` slot uid (those are crc32 keys). This report is
therefore **arena-only: there is no catalog join** — it does not look the probe
ids up in ``all_slots()`` because the two id spaces are unrelated. See the
``catalog_join``/``catalog_join_note`` fields in the output.

Three results are reported, kept strictly separate:

* ``pre_probe``      -- default-deny: no slot evidence, no profile gates.
* ``stamped``        -- native xyz/terrain/route evidence applied; the pair is
  now denied only on the profile placement gates (`accepted_gates`), which are
  lane-33/QA-owned, NOT lane-04.
* ``injected_legal`` -- clearly-labelled: profile gates filled by hand to show
  the end-to-end interface is wired; this is NOT natural acceptance.

   py -3.12 scripts/audit_p2_placement_evidence.py --probe probe.json [--out report.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from randomizer import p2_placement
from randomizer import p2_placement_native


def arena_document(probe):
    """Build a labelled encounter-arena document from a probe's generator ids."""
    slots = []
    for slot in probe['slots']:
        slots.append(p2_placement.normalize_slot({
            'uid': slot['uid'], 'label': f'p2-room-encounter-generator-{slot["uid"]}', 'stage': 0,
            'terrain': 'ground', 'radius': 100.0,
            'corpse_route': True, 'evidence': {'xyz': False, 'terrain': False, 'route': False},
        }))
    profiles = [
        p2_placement.normalize_profile({
            'identity': 'YellowKochappy', 'terrains': ['ground'], 'family_lane': 13,
            'requires_corpse_route': True, 'accepted_gates': [],
            'notes': 'Snow Bulborb (lane-04 encounter arena audit; profile gates owned by lane 33).',
        }),
        p2_placement.normalize_profile({
            'identity': 'BlueKochappy', 'terrains': ['ground'], 'family_lane': 13,
            'requires_corpse_route': True, 'accepted_gates': [],
            'notes': 'Dwarf Orange Bulborb (lane-04 encounter arena audit; profile gates owned by lane 33).',
        }),
    ]
    return p2_placement.validate_document({'schema': p2_placement.SCHEMA, 'slots': slots, 'profiles': profiles})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)

    probe = p2_placement_native.normalize_probe(json.loads(args.probe.read_text()))
    document = arena_document(probe)

    pre = p2_placement.audit(document)
    stamped = p2_placement_native.stamp_evidence(document, probe)
    post = p2_placement.audit(stamped)

    injected = json.loads(json.dumps(stamped))
    for profile in injected['profiles']:
        profile['accepted_gates'] = ['arena']
    injected = p2_placement.validate_document(injected)
    injected_audit = p2_placement.audit(injected)

    report = {
        'catalog_join': None,
        'catalog_join_note': (
            'arena-only, no catalog join: the probe ids are generator 4-byte file '
            'ids (Generator::_70), not p2_placement_catalog.all_slots() uid keys '
            '(crc32), so they are not looked up in the campaign catalog.'),
        'probe': probe,
        'pre_probe_admitted': pre['admitted'],
        'pre_probe_denied_reasons': pre['denied_reasons'],
        'stamped_admitted': post['admitted'],
        'stamped_denied_reasons': post['denied_reasons'],
        'injected_legal_admitted': injected_audit['admitted'],
        'injected_legal_unplaced': injected_audit['unplaced_identities'],
        'slot_evidence': p2_placement_native.slot_evidence_summary(stamped),
    }
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
