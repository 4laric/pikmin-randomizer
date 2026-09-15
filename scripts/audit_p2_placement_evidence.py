"""Lane-04 audit bridge: fold a native placement-evidence probe into the real
placement catalog and report the before/after admission decision (#440).

The native probe (``pc_p2_placement_probe``) emits ``P2_PLACEMENT_SLOT`` facts
carrying both the generator 4-byte file id and, when a ``p2-placement-slots.txt``
sidecar is staged, a placement-catalog slot uid. This script turns a captured
``p2-placement-probe`` JSON (``randomizer.p2_placement_probe.build_probe``) into
slot ``evidence`` and runs the deny -> evidence-stamped decision.

When the probe carries a catalog join (``catalog_join=true``), every mapped slot
uid is looked up in ``randomizer.p2_placement_catalog.all_slots()``: an
**unmappable uid is a hard failure**. Only matched slots are stamped, and the
audit runs against the genuine catalog document. When ``catalog_join=false``
(no sidecar) the report is arena-only.

Three results are reported, kept strictly separate:

* ``pre_probe``      -- default-deny: no slot evidence, no profile gates.
* ``stamped``        -- native evidence applied to the matched catalog slot(s);
  the pair is then denied only on the profile gates (`accepted_gates`, owned by
  lane 33/QA, NOT lane-04).
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
from randomizer import p2_placement_catalog
from randomizer import p2_placement_native

IDENTITIES = ('YellowKochappy', 'BlueKochappy')


def catalog_document():
    return p2_placement_catalog.build_document()


def _inject_gates(document):
    doc = json.loads(json.dumps(document))
    for profile in doc['profiles']:
        if profile['identity'] in IDENTITIES:
            profile['accepted_gates'] = ['arena']
    return p2_placement.validate_document(doc)


def arena_document(probe):
    """Fallback for a probe without a catalog join (generator ids only)."""
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


def _admitted_for(report, identities):
    return {k: v for k, v in report['admitted'].items() if k in identities}


def run_audit(probe, catalog_doc=None, identities=IDENTITIES):
    """Return the join + before/after admission report for a probe document."""
    if probe.get('catalog_join'):
        catalog_doc = catalog_doc if catalog_doc is not None else catalog_document()
        catalog_uids = {slot['uid'] for slot in catalog_doc['slots']}
        mapped = [m for m in probe['mapping']]
        mapped_uids = {m['slot'] for m in mapped}
        unmatched = sorted(mapped_uids - catalog_uids)
        if unmatched:
            raise SystemExit(
                f'catalog join hard failure: probe slot uid(s) {unmatched} are not '
                f'present in p2_placement_catalog.all_slots()')
        stamp_probe = {'schema': probe['schema'],
                       'slots': [s for s in probe['slots'] if s['uid'] in mapped_uids]}
        stamped = p2_placement_native.stamp_evidence(catalog_doc, stamp_probe)
        pre = p2_placement.audit(catalog_doc, identities=list(identities))
        post = p2_placement.audit(stamped, identities=list(identities))
        injected = p2_placement.audit(_inject_gates(stamped), identities=list(identities))
        return {
            'catalog_join': True,
            'matched_slot_uids': sorted(mapped_uids),
            'mapping': mapped,
            'pre_probe_admitted': _admitted_for(pre, identities),
            'pre_probe_denied_reasons': pre['denied_reasons'],
            'stamped_admitted': _admitted_for(post, identities),
            'stamped_denied_reasons': post['denied_reasons'],
            'injected_legal_admitted': _admitted_for(injected, identities),
            'slot_evidence': p2_placement_native.slot_evidence_summary(stamped),
        }
    doc = arena_document(probe)
    pre = p2_placement.audit(doc)
    stamped = p2_placement_native.stamp_evidence(doc, probe)
    post = p2_placement.audit(stamped)
    injected = p2_placement.audit(_inject_gates(stamped))
    return {
        'catalog_join': False,
        'catalog_join_note': (
            'arena-only, no catalog join: the probe ids are generator 4-byte file '
            'ids (Generator::_70), not p2_placement_catalog.all_slots() uid keys '
            '(crc32), so they are not looked up in the campaign catalog.'),
        'pre_probe_admitted': _admitted_for(pre, identities),
        'pre_probe_denied_reasons': pre['denied_reasons'],
        'stamped_admitted': _admitted_for(post, identities),
        'stamped_denied_reasons': post['denied_reasons'],
        'injected_legal_admitted': _admitted_for(injected, identities),
        'slot_evidence': p2_placement_native.slot_evidence_summary(stamped),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)

    report = run_audit(json.loads(args.probe.read_text()))
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
