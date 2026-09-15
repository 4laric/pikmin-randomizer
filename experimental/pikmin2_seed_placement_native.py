"""Lane-04 slice 4 native co-occurrence validator (pure Python).

Closes the loop across the three native markers a single room run emits:

* ``P2_PLACEMENT_SLOT generator=<g> slot=<u> ...``  -- lane-04 placement probe:
  generator ``g`` maps (sidecar) to catalog slot ``u``.
* ``P2_SEED_RESOLVE source_id=<s> target=<u> ...``  -- seed bridge: catalog slot
  ``u`` resolves to source ``s``.
* ``P2_ENEMY_READY ... source_id=<s> ... generator=<g> ...`` -- identity birth:
  generator ``g`` births source ``s``.

The exact agreement required is a closed chain `generator -> slot -> source` and
`generator -> birth source` for the same ``(generator, slot, source)`` triple, so
a marker that is stripped or that disagrees flips the result.

The Snow/Dwarf Orange cohort is pinned (source 44/45); a resolved source outside
the cohort is a failure. No lane paths appear here; this module only reads text.
"""
from dataclasses import dataclass
import re

SNOW_SOURCE = 45
ORANGE_SOURCE = 44
COHORT_SOURCES = (SNOW_SOURCE, ORANGE_SOURCE)

_SLOT_RE = re.compile(r'P2_PLACEMENT_SLOT generator=(\d+) slot=(\d+)')
_RESOLVE_RE = re.compile(r'P2_SEED_RESOLVE source_id=(\d+) target=(\d+)')
_READY_RE = re.compile(r'P2_ENEMY_READY .*?source_id=(\d+).*?generator=(\d+)')


@dataclass
class Cooccurrence:
    ok: bool
    reason: str
    generator: int | None = None
    slot: int | None = None
    source: int | None = None


def _placement_slots(text):
    return [(int(g), int(u)) for g, u in _SLOT_RE.findall(text) if int(u)]


def _resolves(text):
    return [(int(s), int(u)) for s, u in _RESOLVE_RE.findall(text)]


def _ready(text):
    return [(int(s), int(g)) for s, g in _READY_RE.findall(text)]


def validate_cooccurrence(text):
    """Return a :class:`Cooccurrence` verdict for a captured room log.

    ``ok`` is True only when at least one ``(generator, slot, source)`` chain is
    closed by all three markers and the source is a Snow/Dwarf Orange cohort
    member. The reason pinpoints the first gap so a flip test can name it.
    """
    slots = dict(_placement_slots(text))  # generator -> slot
    if not slots:
        return Cooccurrence(False, 'no mapped P2_PLACEMENT_SLOT marker')
    resolve_by_target = {}
    sources_seen = set()
    for source, target in _resolves(text):
        resolve_by_target[target] = source
        sources_seen.add(source)
    ready_by_generator = {}
    ready_sources = set()
    for source, generator in _ready(text):
        ready_by_generator[generator] = source
        ready_sources.add(source)
    non_cohort = sources_seen - set(COHORT_SOURCES)
    if non_cohort:
        return Cooccurrence(False, f'non-cohort source resolved: {sorted(non_cohort)}')

    for generator, slot in sorted(slots.items(), key=lambda row: row[1]):
        source = resolve_by_target.get(slot)
        if source is None:
            continue
        if source not in COHORT_SOURCES:
            return Cooccurrence(False, f'source {source} outside the cohort')
        if ready_by_generator.get(generator) != source:
            return Cooccurrence(
                False,
                f'generator {generator} resolved slot {slot} -> source {source} '
                f'but P2_ENEMY_READY births {ready_by_generator.get(generator)}',
                generator=generator, slot=slot, source=source,
            )
        return Cooccurrence(True, 'closed generator->slot->source and birth chain',
                            generator=generator, slot=slot, source=source)
    return Cooccurrence(
        False, f'no P2_SEED_RESOLVE matched a mapped slot: {sorted(slots.values())}')
