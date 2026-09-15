"""The placement catalog driving a real generated seed.

The seed bridge ``resolve_placement_layout`` binds a *set* of catalog slots to
each admitted source (consuming the admitted cohort and the placement document),
and the sidecar records every ``(generator, slot)`` pair, so the probe's
``P2_PLACEMENT_SLOT`` markers join to the full binding set rather than a single
picked slot.

Because the committed admitted cohort is empty (deny by default) and
``randomizer.seed.generate`` has no roster-injection parameter, the admitted
cohort is injected the same way ``tests/test_pikmin2_seed_generation.py`` does
it: ``experimental.pikmin2_seed_bridge.admitted_ids`` is patched for the
duration of ``generate``. The placement document is the real
``p2_placement_catalog.build_document()`` with the Snow/Dwarf Orange cohort's
acceptance labelled injected (evidence stamped to True + ``accepted_gates``
filled), filtered to the arena's stage-0 ground slots.

This is the seed/manifest/sidecar half. The runtime half lives in
``scripts/run_p2_seed_placement.py`` (stage the Dwarf Orange arena, write the
seed-derived sidecar, run the native probe, audit).
"""
import json

from randomizer import p2_placement
from randomizer import p2_placement_catalog

ARENA_STAGE = 0
COHORT_IDENTITIES = ('YellowKochappy', 'BlueKochappy')
BLUEKOCHAPPY_SOURCE = 44
YELLOWKOCHAPPY_SOURCE = 45
ADMITTED_COHORT = (BLUEKOCHAPPY_SOURCE, YELLOWKOCHAPPY_SOURCE)
ARENA_SOURCE_GENERATOR = 211001
ARENA_GENERATORS = (211001, 211002)
SIDECAR_HEADER = 'P2_PLACEMENT_SLOTS_1'
SIDECAR_NAME = 'p2-placement-slots.txt'


def placement_document(arena_stage=ARENA_STAGE, identities=COHORT_IDENTITIES,
                       catalog_doc=None):
    """Return the real catalog restricted to the arena, with the cohort accepted.

    Clearly labelled INJECTED: the catalog ships deny-by-default, so for the
    end-to-end integration proof every stage-``arena_stage`` ground slot's
    ``xyz``/``terrain``/``route`` evidence is set to True and the cohort profiles
    are given ``accepted_gates=['arena']``. This is natural-admission shaping for
    the bridge, not a claim that a real native run accepted the cohort.
    """
    if catalog_doc is None:
        catalog_doc = p2_placement_catalog.build_document()
    doc = json.loads(json.dumps(catalog_doc))
    doc['slots'] = [slot for slot in doc['slots']
                    if slot['stage'] == arena_stage and slot['terrain'] == 'ground']
    for slot in doc['slots']:
        slot.setdefault('evidence', {})
        for key in ('xyz', 'terrain', 'route'):
            slot['evidence'][key] = True
    for profile in doc['profiles']:
        if profile['identity'] in identities:
            profile['accepted_gates'] = ['arena']
    return p2_placement.validate_document(doc)


def generate_admitted_seed(seed_name, document, slot='Player1',
                           admitted=ADMITTED_COHORT):
    """Produce a real ``randomizer.seed.generate`` manifest on an injected cohort.

    ``randomizer.seed.generate`` calls the roster ``load_and_validate`` (deny by
    default) and the seed-bridge ``resolve_placement_layout``; the admitted cohort
    is injected by temporarily patching
    ``experimental.pikmin2_seed_bridge.admitted_ids`` (the same mechanism the
    seed-generation test uses), then restored.
    """
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer.seed import generate as _generate
    saved = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(admitted)
    try:
        return _generate(seed_name, p2_enemies=True, p2_placement=document)
    finally:
        bridge.admitted_ids = saved


def seed_slots(manifest, source_id=BLUEKOCHAPPY_SOURCE):
    """Return the sorted catalog slot uids the seed bound to ``source_id``.

    The seed binds a *set* of stage-0 ground slots to each admitted source; this
    returns the whole set (never a single slot), so a sidecar consumer carries
    every binding rather than a pick of one.
    """
    return sorted(int(binding['target']) for binding in manifest['p2_layout']['bindings']
                  if binding['source_id'] == source_id)


def seed_slot_uids(manifest):
    """Return ``{source_id: sorted [slot uids]}`` for the seed's full binding set.

    Every binding is accumulated per source (earlier a one-off used a dict
    comprehension that kept only the last binding per source and was unused).
    """
    by_source = {}
    for binding in manifest['p2_layout']['bindings']:
        by_source.setdefault(binding['source_id'], []).append(int(binding['target']))
    return {source_id: sorted(uids) for source_id, uids in by_source.items()}


def write_sidecar(directory, generator_slots):
    """Write the ``p2-placement-slots.txt`` sidecar mapping every generator.

    ``generator_slots`` is an iterable of ``(generator_id, slot_uid)`` pairs; the
    full set is written (one line per generator) so the probe reports one
    ``P2_PLACEMENT_SLOT`` per generator that resolves.
    """
    from pathlib import Path
    path = Path(directory) / SIDECAR_NAME
    lines = [SIDECAR_HEADER]
    lines += [f'{int(generator_id)} {int(slot_uid)}' for generator_id, slot_uid in generator_slots]
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    return path
