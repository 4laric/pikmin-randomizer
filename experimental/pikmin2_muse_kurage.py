"""Muse l58 Kurage57 generated-birth observer (#498, parent #243, wave #491).

Additive gate-1 observer for the Lesser Spotted Jellyfloat (Kurage, source
ID 57). It correlates the SAME real generated slot/generator across the
three independent birth markers a natural generated spawn must emit:

1. Source-ID resolve (``src/plugPikiNakata/genteki.cpp`` ``GenObjectTeki::birth``):
   ``P2_SEED_RESOLVE source_id=57 target=<uid> ...`` — the ENEMY_P2 seed
   binding resolved generator uid ``<uid>`` to source 57.
2. Generated placement (``native/pc_port/pc_p2_generated_placement.cpp``):
   ``P2_GENERATED_PLACEMENT source_id=57 target=<uid> bound=1`` — the spawned
   P1 stand-in actor was claimed for identity 57 on seed target ``<uid>``.
   (Owned by muse-placement l52/#492; currently only source IDs 23/59-62
   have a bind case, so this marker is absent for 57 until that lands.)
3. Kurage binding (``native/pc_port/pc_p2_kurage_teki.cpp``):
   ``P2_KURAGE_TEKI_READY generator=<gen> ...`` plus
   ``P2_KURAGE_CORPSE_READY generator=<gen> ... receipt=corpse:kurage:<gen>``.

The verdict is PASS only when all three markers are present, name source 57,
agree on one slot/generator, and carry no injected-birth taint
(``injected``/``health_zero`` tokens). Anything else fails closed with the
exact missing/mismatched reason. In particular the legacy
``p2-kurage-teki.txt`` sidecar auto-bind (historical generator 201001,
``P2_KURAGE_TEKI_READY`` with no resolve/placement markers) is reported as
``auto-bind without generated markers`` — never as a generated identity.

Scope: read-only log observation. It spawns nothing, binds nothing, mutates
no save, and touches no legacy lane-29 family module. Gates 2-6 are owned by
the lane-29 slices and are not re-evaluated here.
"""
import re

SOURCE_ID = 57
SPECIES = 'Kurage'

# Historical sidecar auto-bind generator used by the legacy l29 slices
# (``p2-kurage-teki.txt`` ``P2_KURAGE_TEKI_1 1`` + ``201001 0``). A TEKI_READY
# line for this generator proves the old private-adapter path, not a
# generated ENEMY_P2 spawn.
LEGACY_AUTO_BIND_GENERATOR = '201001'

_RE_RESOLVE = re.compile(
    r'P2_SEED_RESOLVE\s+source_id=(?P<source>\d+)\s+target=(?P<target>\d+)')
_RE_PLACEMENT = re.compile(
    r'P2_GENERATED_PLACEMENT\s+source_id=(?P<source>\d+)\s+'
    r'target=(?P<target>\d+)\s+bound=(?P<bound>[01])\b')
_RE_TEKI_READY = re.compile(
    r'P2_KURAGE_TEKI_READY\s+generator=(?P<generator>\d+)')
_RE_CORPSE_READY = re.compile(
    r'P2_KURAGE_CORPSE_READY\s+generator=(?P<generator>\d+).*?'
    r'receipt=corpse:kurage:(?P<receipt>\d+)')

_INJECTED_MARKERS = ('injected', 'health_zero', 'INJECTED')

_BIRTH_TOKENS = ('P2_SEED_RESOLVE', 'P2_GENERATED_PLACEMENT',
                 'P2_KURAGE_TEKI_READY', 'P2_KURAGE_CORPSE_READY')


def _tainted(line):
    lowered = line.lower()
    return any(marker in lowered for marker in ('injected', 'health_zero'))


def validate_generated_birth(log_text):
    """Correlate the three generated-birth markers for Kurage 57.

    Returns ``(verdict, detail)`` where verdict is ``'PASS'`` or ``'FAIL'``
    and detail names the agreed slot/generator or the exact failure reason.
    Fail-closed: any missing marker, source mismatch, slot/generator
    disagreement, ``bound=0``, or injected-birth taint is FAIL.
    """
    if not log_text or not log_text.strip():
        return ('FAIL', 'empty log: no generated-birth markers')

    lines = log_text.splitlines()
    resolve_targets = []
    placement_targets = []
    placement_refused = []
    teki_generators = []
    corpse_generators = []
    tainted_markers = []

    for line in lines:
        match = _RE_RESOLVE.search(line)
        if match:
            if _tainted(line):
                tainted_markers.append(line.strip())
            elif match.group('source') == str(SOURCE_ID):
                resolve_targets.append(match.group('target'))
        match = _RE_PLACEMENT.search(line)
        if match:
            if _tainted(line):
                tainted_markers.append(line.strip())
            elif match.group('source') == str(SOURCE_ID):
                if match.group('bound') == '1':
                    placement_targets.append(match.group('target'))
                else:
                    placement_refused.append(match.group('target'))
        match = _RE_TEKI_READY.search(line)
        if match:
            if _tainted(line):
                tainted_markers.append(line.strip())
            else:
                teki_generators.append(match.group('generator'))
        match = _RE_CORPSE_READY.search(line)
        if match:
            if _tainted(line):
                tainted_markers.append(line.strip())
            elif match.group('generator') != match.group('receipt'):
                return ('FAIL',
                        'corpse receipt generator=%s disagrees with receipt id=%s'
                        % (match.group('generator'), match.group('receipt')))
            else:
                corpse_generators.append(match.group('generator'))

    if tainted_markers:
        return ('FAIL',
                'injected-birth taint on birth markers: %s'
                % tainted_markers[0][:160])

    if not resolve_targets:
        if teki_generators or corpse_generators:
            return ('FAIL',
                    'auto-bind without generated markers: Kurage binding present '
                    '(generator=%s) but no P2_SEED_RESOLVE source_id=57; '
                    'legacy sidecar binds (e.g. generator %s) are not generated '
                    'identities' % (teki_generators[0] if teki_generators else '?',
                                    LEGACY_AUTO_BIND_GENERATOR))
        return ('FAIL', 'missing P2_SEED_RESOLVE source_id=%d' % SOURCE_ID)

    if not placement_targets:
        if placement_refused:
            return ('FAIL',
                    'generated placement refused source_id=%d target=%s (bound=0)'
                    % (SOURCE_ID, placement_refused[0]))
        return ('FAIL',
                'missing P2_GENERATED_PLACEMENT source_id=%d bound=1 '
                '(muse-placement l52/#492 has not landed the case-57 bind yet)'
                % SOURCE_ID)

    if not teki_generators:
        return ('FAIL', 'missing P2_KURAGE_TEKI_READY generator marker')
    if not corpse_generators:
        return ('FAIL', 'missing P2_KURAGE_CORPSE_READY receipt marker')

    slots = set(resolve_targets) | set(placement_targets)
    if len(slots) > 1:
        return ('FAIL',
                'resolve/placement slot disagreement: resolve=%s placement=%s'
                % (sorted(set(resolve_targets), key=int),
                   sorted(set(placement_targets), key=int)))
    slot = next(iter(slots))

    generators = set(teki_generators) | set(corpse_generators)
    if len(generators) > 1:
        return ('FAIL',
                'Kurage binding generator disagreement: teki=%s corpse=%s'
                % (sorted(set(teki_generators), key=int),
                   sorted(set(corpse_generators), key=int)))
    generator = next(iter(generators))

    # The resolve/placement ``target`` is the seed slot uid
    # (``pc_randomizer_generator_id``); the Kurage binding logs the engine
    # generator field (``mGenerator->_70``). Both are emitted for the same
    # spawned actor, so a correlated birth must name one value. If the future
    # l52 bind logs an explicit ``seed_target`` alongside a differing engine
    # generator, this check names the pair instead of passing silently.
    if generator != slot:
        return ('FAIL',
                'slot/generator disagreement: seed slot=%s Kurage generator=%s; '
                'same spawned actor required' % (slot, generator))

    # A tainted line anywhere that touches the correlated birth — a birth
    # marker or the agreed slot/generator — disqualifies the natural claim,
    # even when the three markers themselves read clean (e.g. an injected
    # health-zero death on the same actor before the carry chain).
    for line in lines:
        if _tainted(line) and (any(tok in line for tok in _BIRTH_TOKENS)
                               or slot in line or generator in line):
            return ('FAIL',
                    'injected-birth taint on correlated slot/generator %s: %s'
                    % (slot, line.strip()[:160]))

    return ('PASS',
            'generated Kurage57 birth: slot/generator=%s resolve+placement+teki+corpse agree'
            % slot)


def is_generated_identity(log_text):
    """True only when ``validate_generated_birth`` passes.

    Convenience guard for consumers that must refuse the legacy auto-bind:
    returns False for the old 201001 sidecar path and for any injected run.
    """
    verdict, _ = validate_generated_birth(log_text)
    return verdict == 'PASS'
