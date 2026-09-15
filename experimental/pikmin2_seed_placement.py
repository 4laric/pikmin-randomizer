"""Lane-04 slice 3: the placement catalog driving a real generated seed.

Slice 2 hand-built the ``p2-placement-slots.txt`` sidecar from a lane-04
:func:`scripts.run_p2_catalog_placement.choose_slot`. This module flips that
dependency: the catalog slot uid now comes from the seed's ``p2_layout``, i.e.
from lane 03's seed bridge ``resolve_placement_layout`` (consuming lane 02's
admitted cohort and lane 04's placement document), so the native probe's
``P2_PLACEMENT_SLOT slot=...`` marker joins to the slot the *seed actually chose*
rather than a lane-04-side pick.

Because the committed lane 02 ledger admits nothing (deny by default) and
``randomizer.seed.generate`` has no roster-injection parameter, the admitted
cohort is injected the same way lane 03's own ``tests/test_pikmin2_seed_generation.py``
does it: ``experimental.pikmin2_seed_bridge.admitted_ids`` is patched for the
duration of ``generate``. The placement document is the real
``p2_placement_catalog.build_document()`` with the Snow/Dwarf Orange cohort's
acceptance labelled injected (evidence stamped to True + ``accepted_gates``
filled), filtered to the arena's stage-0 ground slots.

This is the seed/manifest/sidecar half. The runtime half lives in
``scripts/run_p2_seed_placement.py`` (stage the Dwarf Orange arena, write the
sidecar from the seed's chosen slot, run the native probe, audit).
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

    ``randomizer.seed.generate`` calls lane 02's ``load_and_validate`` (deny by
    default) and lane 03's ``resolve_placement_layout``; the admitted cohort is
    injected by temporarily patching ``experimental.pikmin2_seed_bridge.admitted_ids``
    (the same mechanism lane 03's own seed-generation test uses), then restored.
    """
    import experimental.pikmin2_seed_bridge as bridge
    from randomizer.seed import generate as _generate
    saved = bridge.admitted_ids
    bridge.admitted_ids = lambda roster: list(admitted)
    try:
        return _generate(seed_name, p2_enemies=True, p2_placement=document)
    finally:
        bridge.admitted_ids = saved


def seed_slot_uid(manifest, source_id=BLUEKOCHAPPY_SOURCE):
    """Return the catalog slot uid the seed bound to ``source_id``, or None."""
    for binding in manifest['p2_layout']['bindings']:
        if binding['source_id'] == source_id:
            return int(binding['target'])
    return None


def seed_slot_uids(manifest):
    """Return ``{source_id: slot_uid}`` for every binding in a seed layout."""
    return {binding['source_id']: int(binding['target'])
            for binding in manifest['p2_layout']['bindings']}


def write_sidecar(directory, generator_id, slot_uid):
    """Write the ``p2-placement-slots.txt`` sidecar mapping a generator to a slot."""
    from pathlib import Path
    path = Path(directory) / SIDECAR_NAME
    path.write_text(f'{SIDECAR_HEADER}\n{int(generator_id)} {int(slot_uid)}\n',
                    encoding='ascii')
    return path
