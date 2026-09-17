"""Family consumer boundary for Waterwraith99 generated identity (#572).

Correlates the generated birth triple for BlackMan (source 99) with its
owned Tyre helper (98):

1. P2_SEED_RESOLVE source_id=99 target=<uid> (genteki birth, ENEMY_P2 seed).
2. P2_GENERATED_PLACEMENT source_id=99 target=<uid> generator=<gen>
   bound=1 (narrow native bind path; reviewed placement99 provider #575,
   accepted slot 568677317).
3. P2_WATERWRAITH_BIRTH phase=fall attached=1 id=99 helper=98
   generator=<gen> (family register claim on the spawned actor; the
   generator field does not exist yet -- a family marker follow-on owned
   by this lane records it when the bind path lands).

Tyre98 is attached helper evidence, never an identity: no gate table is
produced for 98 and no 98 marker can satisfy this verdict. The legacy
fixed-encounter birth (same BIRTH line with no resolve/placement
markers, generator 0) is reported as fixed-encounter, never generated.

Verdict is PASS only when resolve and placement agree on the accepted
slot 568677317, the family birth names id 99 with helper 98 attached,
the birth generator field is present and equals the placement
generator (numeric register tie -- staged-only ties never pass), and no
injected-birth taint is present. Missing placement (the live state
before #575) and untied register births fail closed with the exact
reason. No generated slot UID beyond the reviewed 568677317 is accepted.
"""
import re

SOURCE_ID = 99
HELPER_ID = 98

# Reviewed generated slot for BlackMan99 (placement99 provider #575
# WATERWRAITH_GENERATED_SLOTS, mirrored in
# pc_p2_generated_placement_waterwraith_slot): stage-2 Navel water-cavern
# slot navel_0-29_645. Only this uid is a real generated slot for 99.
ACCEPTED_SLOT = '568677317'

_RE_RESOLVE = re.compile(
    r'P2_SEED_RESOLVE\s+source_id=(?P<source>\d+)\s+target=(?P<target>\d+)')
_RE_PLACEMENT = re.compile(
    r'P2_GENERATED_PLACEMENT\s+source_id=(?P<source>\d+)\s+'
    r'target=(?P<target>\d+)(?:\s+generator=(?P<placed_gen>\d+))?\s+'
    r'bound=(?P<bound>[01])\b')
_RE_BIRTH = re.compile(
    r'P2_WATERWRAITH_BIRTH\s+phase=(?P<phase>\S+)\s+attached=(?P<attached>[01])\s+'
    r'id=(?P<id>\d+)\s+helper=(?P<helper>\d+)(?:\s+generator=(?P<generator>\d+))?')

_BIRTH_TOKENS = ('P2_SEED_RESOLVE', 'P2_GENERATED_PLACEMENT',
                 'P2_WATERWRAITH_BIRTH')

# Captain-safety scan tokens (#632): engine death/extinction markers that
# must never underlie a birth PASS. Advisory: reported separately, never
# mixed into the triple verdict silently.
_CAPTAIN_TOKENS = ('p2_fixture_captain_down', 'captain_down', 'orimadead',
                   'navidead', 'extinction', 'game_over')


def _tainted(line):
    lowered = line.lower()
    return 'injected' in lowered or 'health_zero' in lowered


def fixed_birth_present(log_text):
    """True when the legacy fixed-encounter birth marker is present."""
    if not log_text:
        return False
    return any(_RE_BIRTH.search(line) and _RE_BIRTH.search(line).group('id') == str(SOURCE_ID)
               for line in log_text.splitlines())


def captain_safety_scan(log_text):
    """Flag captain-down/extinction markers (test-equivalent guard).

    Returns [(line_number, line)] hits, case-insensitive. An empty list
    means no safety signal was observed; any hit must BLOCK a birth PASS
    claim regardless of the triple verdict.
    """
    hits = []
    if not log_text:
        return hits
    for number, line in enumerate(log_text.splitlines(), 1):
        lowered = line.lower()
        if any(token in lowered for token in _CAPTAIN_TOKENS):
            hits.append((number, line.strip()[:160]))
    return hits


def validate_generated_birth(log_text):
    """Correlate the generated-birth triple for BlackMan 99.

    Returns (verdict, detail): verdict PASS only on full agreement on the
    accepted slot with a numeric register tie; otherwise FAIL with the
    exact missing/mismatched reason. Fixed-only births, missing placement
    arms, refusals, non-accepted slots, untied register births and taint
    all fail closed.
    """
    if not log_text or not log_text.strip():
        return ('FAIL', 'empty log: no generated-birth markers')

    lines = log_text.splitlines()
    resolve_targets = []
    placement_targets = []
    placement_generators = []
    placement_refused = []
    births = []
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
                    placement_generators.append(match.group('placed_gen'))
                else:
                    placement_refused.append(match.group('target'))
        match = _RE_BIRTH.search(line)
        if match:
            if _tainted(line):
                tainted_markers.append(line.strip())
            else:
                births.append(match)

    if tainted_markers:
        return ('FAIL',
                'injected-birth taint on birth markers: %s'
                % tainted_markers[0][:160])

    if not resolve_targets:
        if births:
            return ('FAIL',
                    'fixed-encounter birth is not a generated identity: '
                    'P2_WATERWRAITH_BIRTH id=99 present but no '
                    'P2_SEED_RESOLVE source_id=99 (fixed placement uses '
                    'generator 0)')
        return ('FAIL', 'missing P2_SEED_RESOLVE source_id=%d' % SOURCE_ID)

    if not placement_targets:
        if placement_refused:
            return ('FAIL',
                    'generated placement refused source_id=%d target=%s (bound=0)'
                    % (SOURCE_ID, placement_refused[0]))
        return ('FAIL',
                'missing P2_GENERATED_PLACEMENT source_id=%d bound=1 '
                '(placement99 provider unpublished: no case-99 arm in '
                'pc_p2_generated_placement at this pin)' % SOURCE_ID)

    if not births:
        return ('FAIL', 'missing P2_WATERWRAITH_BIRTH id=99 helper=98 '
                        '(family register never claimed the actor)')

    slots = set(resolve_targets) | set(placement_targets)
    if len(slots) > 1:
        return ('FAIL',
                'resolve/placement target disagreement: resolve=%s placement=%s'
                % (sorted(set(resolve_targets), key=int),
                   sorted(set(placement_targets), key=int)))
    slot = next(iter(slots))

    if slot != ACCEPTED_SLOT:
        return ('FAIL',
                'slot-not-accepted: slot=%s is not the reviewed BlackMan99 '
                'generated slot %s (placement99 provider #575)'
                % (slot, ACCEPTED_SLOT))

    good_births = [m for m in births
                   if m.group('id') == str(SOURCE_ID)
                   and m.group('helper') == str(HELPER_ID)
                   and m.group('phase') == 'fall'
                   and m.group('attached') == '1']
    if not good_births:
        return ('FAIL',
                'family birth does not name id=99 with attached helper=98; '
                'Tyre98 is attached evidence, never the identity')
    birth = good_births[-1]

    placed_gens = {g for g in placement_generators if g is not None}
    if len(placed_gens) != 1:
        return ('FAIL',
                'placement marker lacks a generator field; same-actor '
                'correlation unproven')
    placed_gen = next(iter(placed_gens))
    birth_gen = birth.group('generator')
    if birth_gen is None:
        return ('FAIL',
                'register tie not numeric: P2_WATERWRAITH_BIRTH logs no '
                'generator field (family marker follow-on open); '
                'staged-only ties never pass')
    if birth_gen != placed_gen:
        return ('FAIL',
                'actor disagreement: placement generator=%s register generator=%s; '
                'same spawned actor required' % (placed_gen, birth_gen))
    generator = placed_gen

    for line in lines:
        if _tainted(line) and (any(tok in line for tok in _BIRTH_TOKENS)
                               or slot in line or generator in line):
            return ('FAIL',
                    'injected-birth taint on correlated slot/generator %s: %s'
                    % (slot, line.strip()[:160]))

    return ('PASS',
            'generated BlackMan99 birth: slot=%s generator=%s helper=98 attached; '
            'resolve+placement+register agree (numeric register tie)'
            % (slot, generator))


def is_generated_identity(log_text):
    """True only when validate_generated_birth passes."""
    verdict, _ = validate_generated_birth(log_text)
    return verdict == 'PASS'
