"""Per-floor Candypop bud slots: seeded local keys and the never-behind rule.

Cave-generation freeze (spec #468): a floor is a chain of hazard-free
``segment`` slots joined by ``choke`` gates, with ``leaf`` hazard alcoves and
``bud`` (Candypop) slots. A bud planted in segment ``k`` is a local key for any
choke/leaf encountered *after* segment ``k``: a requirement for type ``T`` is
met by ``T`` directly, or by a bud that provides ``T`` when at least its
conversion count ``N`` of Pikmin can be spent (5 vanilla)::

    type OR (has_matching_bud before segment AND pikmin_count >= N)

The requirement to reach segment ``k`` is the union of the gates on segments
``0..k`` (the fan-out's "union of chokes 1..k"). A bud must never be seeded
behind the type it provides, i.e. its provided type must not appear in that
accumulated requirement, otherwise the bud could only be obtained by already
having the very type it exists to supply.

This module is deterministic, does no file IO, holds no state and defines a
minimal local model. The lane-34 ``experimental/pikmin2_cave_schema`` module it
would otherwise extend is not present in this checkout; the record vocabulary
here mirrors that fan-out model so the two can be wired together later.
"""

from collections.abc import Iterable, Mapping, Sequence

DEFAULT_CONVERSION_COUNT = 5

# Mirrors lane 34's experimental.pikmin2_cave_schema.HAZARD_SPECIES: the species
# a hazard's alternate key needs. Choke/leaf hazards are translated into this
# species space before bud evaluation so a bud's ``provides`` compares like for
# like. Kept local because the lane-34 module is not importable in every
# consumer worktree.
HAZARD_SPECIES = {'water': 'blue', 'elec': 'yellow', 'fire': 'red', 'poison': 'white'}

VIOLATION_RULES = (
    'duplicate_bud',
    'invalid_conversion_count',
    'bud_behind_own_type',
    'segment_out_of_range',
)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _type_set(value):
    if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
        raise ValueError('Gate requirements must be an iterable of type strings')
    result = set()
    for item in value:
        if not isinstance(item, str) or not item:
            raise ValueError('Gate requirement must be a non-empty string')
        result.add(item)
    return result


def _gate_map(gates, declared_count):
    """Normalize a gate table to ``{segment_index: required_types}`` plus count.

    ``gates`` is either a sequence indexed by segment or a mapping from segment
    index to that segment's required types. ``declared_count`` (the optional
    ``segment_count``) may widen the range to cover ungated trailing segments;
    it may never be smaller than the gate table itself.
    """
    if isinstance(gates, Mapping):
        result = {}
        for key, value in gates.items():
            if not _is_int(key) or key < 0:
                raise ValueError('Gate segment keys must be non-negative integers')
            result[key] = _type_set(value)
        derived = max(result) + 1 if result else 0
    elif isinstance(gates, Sequence) and not isinstance(gates, (str, bytes)):
        result = {}
        for index, value in enumerate(gates):
            result[index] = _type_set(value)
        derived = len(gates)
    else:
        raise ValueError('gates must be a mapping or a sequence of requirement sets')
    if declared_count is None:
        count = derived
    else:
        if not _is_int(declared_count) or declared_count < 0:
            raise ValueError('segment_count must be a non-negative integer')
        if declared_count < derived:
            raise ValueError('segment_count is smaller than the gate table')
        count = declared_count
    for index in range(count):
        result.setdefault(index, set())
    return result, count


def segment_requirements(gates, segment_count=None):
    """Return ``{segment_index: required_types_to_reach_it}`` for every segment.

    The value for segment ``k`` is the union of the gates on segments ``0..k``,
    matching the frozen model's "requirement for anything in segment k = union
    of chokes 1..k". The result is a new mapping; the input is not mutated.
    """
    gate_map, count = _gate_map(gates, segment_count)
    accumulated = {}
    running = set()
    for index in range(count):
        running = running | gate_map[index]
        accumulated[index] = set(running)
    return accumulated


def bud_slot(segment_index, provides, conversion_count=DEFAULT_CONVERSION_COUNT):
    """Build a validated bud slot record.

    ``segment_index`` is a non-negative int, ``provides`` a non-empty type or
    hazard string (for example ``"purple"``, ``"white"``, ``"water"``,
    ``"elec"``) and ``conversion_count`` the positive ``N`` (default 5). Raw
    mappings that bypass this helper are still accepted by :func:`validate_buds`
    so untrusted tables produce diagnostics instead of tracebacks.
    """
    if not _is_int(segment_index) or segment_index < 0:
        raise ValueError('Bud segment_index must be a non-negative integer')
    if not isinstance(provides, str) or not provides:
        raise ValueError('Bud provides must be a non-empty string')
    if not _is_int(conversion_count) or conversion_count <= 0:
        raise ValueError('Bud conversion_count must be a positive integer')
    return dict(segment_index=segment_index, provides=provides,
                conversion_count=conversion_count)


def _bud_fields(record):
    if not isinstance(record, Mapping):
        raise ValueError('Bud record must be a mapping')
    if 'provides' not in record:
        raise ValueError('Bud record must provide a type')
    provides = record['provides']
    if not isinstance(provides, str) or not provides:
        raise ValueError('Bud provides must be a non-empty string')
    return (record.get('segment_index'),
            provides,
            record.get('conversion_count', DEFAULT_CONVERSION_COUNT))


def validate_buds(floor):
    """Report bud-slot violations for one floor as a deterministic list.

    ``floor`` is a mapping with at least:

    - ``gates`` — a sequence indexed by segment or a mapping from segment index
      to the set/list of types required to enter that segment;
    - ``buds`` — a sequence of bud records.

    It may also carry ``segment_count`` to bound otherwise-ungated segments.
    Each violation is a dict with a stable ``rule`` key from
    :data:`VIOLATION_RULES`, plus the offending ``segment_index`` and
    ``provides`` (and ``conversion_count``/``first_provides`` where relevant).
    The input mapping is never mutated.
    """
    if not isinstance(floor, Mapping):
        raise ValueError('Floor must be a mapping')
    if 'gates' not in floor:
        raise ValueError('Floor must provide a gates table')
    gate_map, count = _gate_map(floor['gates'], floor.get('segment_count'))
    accumulated = {}
    running = set()
    for index in range(count):
        running = running | gate_map[index]
        accumulated[index] = set(running)
    buds = floor.get('buds', ())
    if isinstance(buds, (str, bytes)) or not isinstance(buds, Sequence):
        raise ValueError('Floor buds must be a sequence of records')
    violations = []
    seen = {}
    for record in buds:
        segment_index, provides, conversion_count = _bud_fields(record)
        in_range = _is_int(segment_index) and 0 <= segment_index < count
        if not in_range:
            violations.append(dict(rule='segment_out_of_range',
                                   segment_index=segment_index, provides=provides))
        if not _is_int(conversion_count) or conversion_count <= 0:
            violations.append(dict(rule='invalid_conversion_count',
                                   segment_index=segment_index, provides=provides,
                                   conversion_count=conversion_count))
        if _is_int(segment_index):
            if segment_index in seen:
                violations.append(dict(rule='duplicate_bud',
                                       segment_index=segment_index, provides=provides,
                                       first_provides=seen[segment_index]))
            else:
                seen[segment_index] = provides
        if in_range and provides in accumulated[segment_index]:
            violations.append(dict(rule='bud_behind_own_type',
                                   segment_index=segment_index, provides=provides))
    return sorted(violations, key=lambda row: (
        row['segment_index'] if _is_int(row['segment_index']) else -1,
        row['rule'], row['provides']))


def from_floor_table(table):
    """Adapt a lane-34 seeded floor table into this module's bud model.

    Lane 34 (#473) persists the seeded table as a mapping with ``segments``,
    ``chokes`` (``after_segment``/``before_segment``/``hazard``) and
    ``buds`` (``segment``/``species``/``count``). This returns
    ``{'gates', 'buds', 'segment_count'}`` where each segment's gate is the set
    of **species** required to enter it (each choke hazard translated through
    :data:`HAZARD_SPECIES`) and each bud is a :func:`bud_slot` record. Feeding
    the result to :func:`validate_buds` re-checks the never-behind-its-own-type
    rule independently of the lane-34 validator, and :func:`bud_key_available`
    exposes the conversion count ``N`` to the logic consumer (lane 39).
    """
    if not isinstance(table, Mapping):
        raise ValueError('Floor table must be a mapping')
    segments = table.get('segments')
    if not isinstance(segments, Sequence) or isinstance(segments, (str, bytes)):
        raise ValueError('Floor table must carry a segment sequence')
    indices = []
    for segment in segments:
        if not isinstance(segment, Mapping) or not _is_int(segment.get('index')):
            raise ValueError('Segment must carry an integer index')
        indices.append(segment['index'])
    segment_count = (max(indices) + 1) if indices else 0
    gates = {}
    chokes = table.get('chokes', ())
    if not isinstance(chokes, Sequence) or isinstance(chokes, (str, bytes)):
        raise ValueError('Floor table chokes must be a sequence')
    for choke in chokes:
        if not isinstance(choke, Mapping):
            raise ValueError('Choke must be a mapping')
        before = choke.get('before_segment')
        hazard = choke.get('hazard')
        if not _is_int(before) or before < 0 or not isinstance(hazard, str):
            raise ValueError('Choke must carry a before_segment and hazard')
        gates.setdefault(before, set()).add(HAZARD_SPECIES.get(hazard, hazard))
    buds = []
    raw_buds = table.get('buds', ())
    if not isinstance(raw_buds, Sequence) or isinstance(raw_buds, (str, bytes)):
        raise ValueError('Floor table buds must be a sequence')
    for bud in raw_buds:
        if not isinstance(bud, Mapping):
            raise ValueError('Bud must be a mapping')
        buds.append(bud_slot(bud.get('segment'), bud.get('species'),
                             bud.get('count', DEFAULT_CONVERSION_COUNT)))
    return dict(gates=gates, buds=buds, segment_count=segment_count)


def bud_key_available(segment_index, required_type, buds, pikmin_count, *,
                      available_types=()):
    """Return whether the requirement at ``segment_index`` opens.

    Implements the frozen requirement ``type OR (bud AND pikmin_count >= N)``:

    - the ``type`` branch holds when ``required_type`` is ``None`` (no type
      requirement) or appears in ``available_types`` (the party can already
      supply that type from outside the path);
    - the bud branch holds when some record in ``buds`` provides
      ``required_type``, sits **strictly before** ``segment_index`` and has a
      positive conversion count ``N`` with ``pikmin_count >= N``.

    "Before" means strict segment-index ordering: a bud in segment ``j`` is a
    key for a gate at segment ``k`` if and only if ``j < k``. A bud in the same
    segment as the gate, or in any later segment, is never its own key; this is
    the never-behind-its-own-type rule applied at evaluation time. A bud whose
    ``conversion_count`` is missing defaults to
    :data:`DEFAULT_CONVERSION_COUNT`; a non-positive or malformed count never
    satisfies a gate.
    """
    if required_type is None:
        return True
    if isinstance(available_types, (str, bytes)):
        raise ValueError('available_types must be a collection, not a bare string')
    if required_type in available_types:
        return True
    if not _is_int(segment_index) or segment_index < 0:
        raise ValueError('segment_index must be a non-negative integer')
    if not _is_int(pikmin_count) or pikmin_count < 0:
        raise ValueError('pikmin_count must be a non-negative integer')
    if isinstance(buds, (str, bytes)) or not isinstance(buds, Sequence):
        raise ValueError('buds must be a sequence of records')
    for record in buds:
        segment, provides, conversion_count = _bud_fields(record)
        if provides != required_type:
            continue
        if not _is_int(segment) or segment >= segment_index:
            continue
        if not _is_int(conversion_count) or conversion_count <= 0:
            continue
        if pikmin_count >= conversion_count:
            return True
    return False
