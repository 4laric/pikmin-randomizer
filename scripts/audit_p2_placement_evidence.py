"""Lane-04 audit bridge: fold a native placement-evidence probe into the real
placement catalog and report the before/after admission decision (#440).

The native probe (``pc_p2_placement_probe``) emits ``P2_PLACEMENT_SLOT`` facts
carrying both the generator 4-byte file id and, when a ``p2-placement-slots.txt``
sidecar is staged, a placement-catalog slot uid. This script turns a captured
``p2-placement-probe`` JSON (``randomizer.p2_placement_probe.build_probe``) into
slot ``evidence`` and runs the deny -> evidence-stamped decision.

Guardrails (all hard failures via ``SystemExit``):

* unmapped generators (no sidecar row) fail unless ``--allow-unmapped``;
* a mapped slot uid absent from ``p2_placement_catalog.all_slots()`` fails;
* a mapped slot whose catalog ``stage`` differs from the arena stage
  (``--stage``) fails, so terrain/route evidence is never stamped onto a
  different map.

Three admission columns are reported, kept separate: ``pre_probe`` (default
deny), ``stamped`` (native slot evidence applied; denied only on lane-33/QA
profile gates), and ``injected_legal`` (clearly-labelled profile-gate injection
to show the interface is wired, not natural acceptance).

   py -3.12 scripts/audit_p2_placement_evidence.py --probe probe.json [--stage 0] [--allow-unmapped] [--out report.json]

The arena stage is read from the probe document's ``arena_stage`` field when
``--stage`` is not given (the runner records it beside the probe); a catalog-join
probe with no stage anywhere is rejected instead of silently skipping the guard.
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


def _admitted_for(report, identities):
    return {k: v for k, v in report['admitted'].items() if k in identities}


def run_audit(probe, catalog_doc=None, identities=IDENTITIES, arena_stage=None, allow_unmapped=False):
    """Return the join + before/after admission report for a probe document.

    When ``arena_stage`` is not passed explicitly it is read from the probe's own
    ``arena_stage`` field (the runner records the staged map stage beside the
    probe), so the stage guard fires without a manual ``--stage`` on the standalone
    CLI. If neither is present the stage guard is skipped, as before.
    """
    if arena_stage is None:
        arena_stage = probe.get('arena_stage')
    unmapped = probe.get('unmapped_generators', [])
    if unmapped and not allow_unmapped:
        raise SystemExit(
            f'catalog join: actor(s) {sorted(set(unmapped))} have no sidecar slot '
            f'mapping; pass --allow-unmapped to proceed')

    if probe.get('catalog_join'):
        catalog_doc = catalog_doc if catalog_doc is not None else catalog_document()
        catalog_slots = {slot['uid']: slot for slot in catalog_doc['slots']}
        mapping = probe['mapping']
        for m in mapping:
            record = catalog_slots.get(m['slot'])
            if record is None:
                raise SystemExit(
                    f'catalog join hard failure: probe slot uid {m["slot"]} is not '
                    f'present in p2_placement_catalog.all_slots()')
            if arena_stage is not None and record['stage'] != arena_stage:
                raise SystemExit(
                    f'catalog join hard failure: slot uid {m["slot"]} is stage '
                    f'{record["stage"]} but the arena is stage {arena_stage}')
        mapped_uids = [m['slot'] for m in mapping]
        stamp_probe = {'schema': probe['schema'], 'slots': probe['slots']}
        stamped = p2_placement_native.stamp_evidence(catalog_doc, stamp_probe)
        pre = p2_placement.audit(catalog_doc, identities=list(identities))
        post = p2_placement.audit(stamped, identities=list(identities))
        injected = p2_placement.audit(_inject_gates(stamped), identities=list(identities))
        return {
            'catalog_join': True,
            'arena_stage': arena_stage,
            'matched_slot_uids': sorted(mapped_uids),
            'mapping': mapping,
            'unmapped_generators': unmapped,
            'pre_probe_admitted': _admitted_for(pre, identities),
            'pre_probe_denied_reasons': pre['denied_reasons'],
            'stamped_admitted': _admitted_for(post, identities),
            'stamped_denied_reasons': post['denied_reasons'],
            'injected_legal_admitted': _admitted_for(injected, identities),
            'slot_evidence': p2_placement_native.slot_evidence_summary(stamped),
        }
    return {
        'catalog_join': False,
        'arena_stage': arena_stage,
        'unmapped_generators': unmapped,
        'catalog_join_note': (
            'arena-only, no catalog join: no sidecar slot mapping was staged, so '
            'the probe ids are generator 4-byte file ids (Generator::_70), not '
            'p2_placement_catalog.all_slots() uid keys; nothing is stamped.'),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--stage', type=int, default=None,
                        help='arena stage; default is read from the probe document arena_stage field')
    parser.add_argument('--allow-unmapped', action='store_true')
    parser.add_argument('--out', type=Path, default=None)
    args = parser.parse_args(argv)

    probe = json.loads(args.probe.read_text())
    stage = args.stage if args.stage is not None else probe.get('arena_stage')
    if probe.get('catalog_join') and stage is None:
        parser.error('catalog-join probe requires --stage or an arena_stage field inside the probe document')
    report = run_audit(probe, arena_stage=stage, allow_unmapped=args.allow_unmapped)
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
