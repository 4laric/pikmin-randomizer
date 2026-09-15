"""Lane 18 contested-cargo, nest and release model (#168/#220).

Host-side model of the source ``PanModokiBase`` cargo rules used by the small
Breadbug (38) and Giant Breadbug (40): eligibility, single-channel contest
strength, interruption (``Damage``/``giveup``) release, death throw-up recovery
and the 15-slot treasure cap. It also encodes the identity invariants for a
combined Giant/small/nest arena (``coexistence_ok``). It records what the family
must prove natively and does not itself mutate a save or an actor. See
``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``.
"""
import math

CARRY_CHANNEL = 'PCS_Unk2'          # Breadbug drag channel (PCS_Unk2)
PIKMIN_CHANNEL = 'PCS_Carry'        # Ordinary Pikmin carry channel
PCS_IDLE = 0xFFFF
MAX_TREASURE_SLOTS = 15
TAKEOVER_STALL_SECONDS = 0.5
NEST_DROP_HEIGHT = 10.0
THROW_UP_RING_RADIUS = 40.0

NEST_JIGUMO = 0                     # enemyNest.cpp:60-67 crawmad nest model (Jigumo 64)
NEST_BREADBUG = 1                   # both Breadbug species map here
NEST_DEATH_FADE_FRAMES = 80         # enemyNestMgr.cpp:143-152

# Giant/small coexistence roles. A combined arena declares each generator role
# separately; the invariants below are identity-disjointness only and do not
# imply shared cargo or P2 contest ownership.
ROLE_GIANT = 'giant'
ROLE_SMALL = 'small'
ROLE_NEST = 'nest'
MAX_GENERATOR_ID = 0xffffffff

DRAG = 'drag'                       # Breadbug wins the contest (Back)
PULLED = 'pulled'                   # Pikmin win the contest (Pulled)

EAT = 'eat'
DROP = 'drop'
RECOVER = 'recover'
DIGEST = 'digest'

RELEASE_REASONS = (EAT, DROP, RECOVER, DIGEST)

# Audited per-variant source parameters. Anchors: retail enemyparm.txt proper
# block 2 (fp03 carry speed, fp06 press damage), general block 1 (fp00 health),
# PanModoki.h/OoPanModoki.h weight thresholds (ip01 11/1), panModoki.cpp
# :1738-1744 Giant Purple-only press, and fp00 nest scale.
VARIANT_PARAMS = {
    'small': {'id': 38, 'name': 'PanModoki', 'health': 1100.0,
              'weight_threshold': 11, 'carry_speed': 35.0, 'press_damage': 200.0,
              'nest_scale': 1.0, 'purple_only_press': False,
              'nest_house_type': NEST_BREADBUG},
    'giant': {'id': 40, 'name': 'OoPanModoki', 'health': 2000.0,
              'weight_threshold': 1, 'carry_speed': 45.0, 'press_damage': 100.0,
              'nest_scale': 2.0, 'purple_only_press': True,
              'nest_house_type': NEST_BREADBUG},
}


def carry_strength(min_pikis, max_pikis):
    """Source ``mCarryStrength``: ``(pelletMin + pelletMax) * 0.5``."""
    if type(min_pikis) is not int or type(max_pikis) is not int:
        raise ValueError('Carry bounds must be integers')
    if min_pikis < 0 or max_pikis < min_pikis:
        raise ValueError('Invalid carry bounds')
    return (min_pikis + max_pikis) * 0.5


def carriers_win(carrier_count, min_pikis, max_pikis):
    """True when Pikmin carriers strictly out-pull the Breadbug each frame."""
    if type(carrier_count) is not int or carrier_count < 0:
        raise ValueError('Invalid carrier count')
    return carrier_count >= carry_strength(min_pikis, max_pikis)


def targetable(*, already_stuck, pellet_carryable, treasure_slots, min_weight,
               weight_limit, variant='small'):
    """Source ``isTargetable`` eligibility for a candidate cargo pellet.

    ``variant='small'`` (id 38) targets strictly lighter cargo
    (``weight_limit > min_weight``); ``variant='giant'`` (id 40) targets cargo at
    or above its threshold (``weight_limit <= min_weight``).
    """
    if variant not in ('small', 'giant'):
        raise ValueError('Unknown breadbug variant: ' + repr(variant))
    if not pellet_carryable or already_stuck:
        return False
    if treasure_slots >= MAX_TREASURE_SLOTS:
        return False
    if variant == 'small':
        return weight_limit > min_weight
    return weight_limit <= min_weight


def release_plan(reason, held_slots=0):
    """Classify a cargo release by source outcome.

    - ``EAT``: ``endCarry`` consumes carcasses/items and kills stuck Pikmin;
      treasure slot 0 stays captured-alive inside the nest matrix.
    - ``DROP``: an interruption (press/hipdrop ``Damage`` state) gives up the
      pull channel and drops the cargo in place.
    - ``RECOVER``: losing the contest returns the cargo to the carriers.
    - ``DIGEST``: entering the underground ``Hide`` state digests the held cargo.
    """
    if reason not in RELEASE_REASONS:
        raise ValueError('Unknown release reason: ' + repr(reason))
    if type(held_slots) is not int or held_slots < 0:
        raise ValueError('Invalid held-slot count')
    if held_slots > MAX_TREASURE_SLOTS:
        raise ValueError('Held treasure exceeds the source slot cap')
    if reason == EAT:
        return {'reason': EAT, 'keeps_slot0_in_nest': held_slots > 0,
                'returns_cargo': False, 'cargo_consumed': True}
    if reason == DROP:
        return {'reason': DROP, 'keeps_slot0_in_nest': False,
                'returns_cargo': True, 'cargo_consumed': False}
    if reason == RECOVER:
        return {'reason': RECOVER, 'keeps_slot0_in_nest': False,
                'returns_cargo': True, 'cargo_consumed': False}
    return {'reason': DIGEST, 'keeps_slot0_in_nest': True,
            'returns_cargo': False, 'cargo_consumed': True}


def throw_up_positions(nest_x, nest_y, nest_z, count):
    """Death throw-up geometry: nest + 10y, radial ring ``TAU*i/n`` (skipped n=1)."""
    if type(count) is not int or not 0 <= count <= MAX_TREASURE_SLOTS:
        raise ValueError('Invalid throw-up count')
    if count == 1:
        return [(nest_x, nest_y + NEST_DROP_HEIGHT, nest_z)]
    spots = []
    for i in range(count):
        angle = 2.0 * math.pi * i / count
        spots.append((nest_x + THROW_UP_RING_RADIUS * math.cos(angle),
                      nest_y + NEST_DROP_HEIGHT,
                      nest_z + THROW_UP_RING_RADIUS * math.sin(angle)))
    return spots


def reconcile_death(held_slots, released):
    """Exactly-once recovery: every held treasure is returned, none created."""
    if type(held_slots) is not int or not 0 <= held_slots <= MAX_TREASURE_SLOTS:
        raise ValueError('Invalid held-slot count')
    if type(released) is not int or released < 0:
        raise ValueError('Invalid released count')
    return {'held': held_slots, 'returned': released,
            'lost': held_slots - released if released <= held_slots else 0,
            'duplicated': released > held_slots}


def _strength(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Invalid contest strength')
    if not math.isfinite(value) or value < 0:
        raise ValueError('Invalid contest strength')
    return float(value)


def variant_params(variant):
    """Return a copy of the audited small (38) / giant (40) source parameters.

    ``small``: health 1100, weight threshold ip01=11, carry speed fp03=35,
    press damage fp06=200, nest scale 1.0 and an ordinary (non-Purple) press.
    ``giant``: health 2000, threshold ip01=1, carry speed 45, press damage 100,
    nest scale 2.0 and a Purple-only press. Both map to ``NEST_BREADBUG``.
    """
    if variant not in VARIANT_PARAMS:
        raise ValueError('Unknown breadbug variant: ' + repr(variant))
    return dict(VARIANT_PARAMS[variant])


def press_damage(variant, *, purple):
    """Source press damage, or 0.0 when the variant rejects the press.

    The Giant Breadbug rejects any non-Purple Pikmin press
    (``panModoki.cpp:1738-1744``); the small Breadbug accepts every press.
    """
    if type(purple) is not bool:
        raise ValueError('purple must be a bool')
    params = variant_params(variant)
    if params['purple_only_press'] and not purple:
        return 0.0
    return params['press_damage']


def arbitrate(claim_strength, challenger_strength,
              claim_channel=CARRY_CHANNEL, challenger_channel=PIKMIN_CHANNEL):
    """Single-channel contest arbitration (``PelletCarry::pullable``).

    The current holder claims on ``claim_channel`` with ``claim_strength``; the
    incoming pull uses ``challenger_channel`` with ``challenger_strength``.
    An idle claim (``claim_channel is None``) or a same-channel challenge is
    accepted: the challenger wins without a stall. A cross-channel challenge
    needs a *strictly greater* strength; on success it takes over with a 0.5 s
    pellet stall (``TAKEOVER_STALL_SECONDS``), otherwise the claim defends.

    Returns ``{'winner', 'reason', 'cross_channel', 'stall_seconds', ...}``
    where ``winner`` is ``'claim'`` or ``'challenger'``.
    """
    claim = _strength(claim_strength)
    challenger = _strength(challenger_strength)
    if claim_channel is None:
        return {'winner': 'challenger', 'reason': 'idle', 'cross_channel': False,
                'stall_seconds': 0.0, 'claim_strength': claim,
                'challenger_strength': challenger}
    if claim_channel == challenger_channel:
        return {'winner': 'challenger', 'reason': 'same_channel',
                'cross_channel': False, 'stall_seconds': 0.0,
                'claim_strength': claim, 'challenger_strength': challenger}
    if challenger > claim:
        return {'winner': 'challenger', 'reason': 'stronger', 'cross_channel': True,
                'stall_seconds': TAKEOVER_STALL_SECONDS, 'claim_strength': claim,
                'challenger_strength': challenger}
    return {'winner': 'claim', 'reason': 'defended', 'cross_channel': True,
            'stall_seconds': 0.0, 'claim_strength': claim,
            'challenger_strength': challenger}


def contest_frames(breadbug_strength, carrier_power_by_frame):
    """Per-frame winner sequence for a Breadbug dragging contested cargo.

    ``carrier_power_by_frame`` is the Pikmin carrier strength for each frame
    (each ordinary carrier contributes 1). While the Breadbug holds the channel
    it drags (``DRAG``/Back); once the carriers strictly out-pull it, it is
    dragged (``PULLED``). Cross-channel takeover is judged each frame.
    """
    breadbug = _strength(breadbug_strength)
    frames = []
    for power in carrier_power_by_frame:
        result = arbitrate(breadbug, _strength(power))
        frames.append(PULLED if result['winner'] == 'challenger' else DRAG)
    return tuple(frames)


def nest_ownership(owner_alive, house_type):
    """Parent-bound nest ownership/lifetime state.

    Both Breadbug species assign ``NEST_BREADBUG=1``; only the Jigumo crawmad
    maps to ``NEST_JIGUMO=0`` (``enemyNest.cpp:60-67``). The nest exists only
    while its owner lives and is never autonomous.
    """
    if type(owner_alive) is not bool:
        raise ValueError('owner_alive must be a bool')
    if house_type not in (NEST_JIGUMO, NEST_BREADBUG):
        raise ValueError('Unknown nest house type')
    return {'owner_alive': owner_alive, 'house_type': house_type,
            'owner': 'breadbug' if house_type == NEST_BREADBUG else 'jigumo',
            'parent_bound': True, 'active': owner_alive}


def nest_collision_after_death(frames_since_kill):
    """True while the dead nest still has collision.

    ``killNest`` sets ``mDeathTimer=1``; collision stays up for 80 frames and is
    then dropped (``enemyNestMgr.cpp:143-152``).
    """
    if type(frames_since_kill) is not int or frames_since_kill < 0:
        raise ValueError('Invalid frames-since-kill')
    return frames_since_kill < NEST_DEATH_FADE_FRAMES


def _coexistence_ids(ids, role):
    if not isinstance(ids, (list, tuple)) or isinstance(ids, (str, bytes)):
        raise ValueError('Coexistence ids for %s must be a list or tuple' % role)
    result = []
    for identity in ids:
        if type(identity) is not int:
            raise ValueError('Coexistence generator id for %s must be an int' % role)
        if not 0 <= identity <= MAX_GENERATOR_ID:
            raise ValueError('Coexistence generator id for %s is out of range' % role)
        result.append(identity)
    if len(set(result)) != len(result):
        raise ValueError('Duplicate generator id within the %s role' % role)
    return result


def coexistence_report(giant_ids, small_ids, nest_ids):
    """Identity invariants a Giant/small Breadbug coexistence arena must satisfy.

    A combined arena declares three disjoint generator roles: the Giant actors,
    the small Breadbug actors and the nests. This is identity bookkeeping only and
    never models shared cargo or P2 contest ownership. Violations are reported
    (rather than raised) so callers can surface the exact reason:

    * at least one Giant actor is declared;
    * exactly one nest per Giant actor (``len(nest_ids) == len(giant_ids)``);
    * the Giant, small and nest generator id sets are pairwise disjoint, so no
      actor is reused across roles and no small actor is claimed as a nest.
    """
    giants = _coexistence_ids(giant_ids, ROLE_GIANT)
    smalls = _coexistence_ids(small_ids, ROLE_SMALL)
    nests = _coexistence_ids(nest_ids, ROLE_NEST)
    violations = []
    if not giants:
        violations.append('no giant actors declared')
    if len(nests) != len(giants):
        violations.append('expected one nest per giant (%d giants, %d nests)'
                          % (len(giants), len(nests)))
    giant_set, small_set, nest_set = set(giants), set(smalls), set(nests)
    for left, right, left_name, right_name in (
            (giant_set, small_set, ROLE_GIANT, ROLE_SMALL),
            (giant_set, nest_set, ROLE_GIANT, ROLE_NEST),
            (small_set, nest_set, ROLE_SMALL, ROLE_NEST)):
        shared = sorted(left & right)
        if shared:
            violations.append('%s and %s share generator ids: %s'
                              % (left_name, right_name,
                                 ', '.join(str(i) for i in shared)))
    return {
        'ok': not violations,
        'giant_ids': giants,
        'small_ids': smalls,
        'nest_ids': nests,
        'giant_count': len(giants),
        'small_count': len(smalls),
        'nest_count': len(nests),
        'pairs': [{'giant': giant, 'nest': nest}
                  for giant, nest in zip(giants, nests)],
        'small_actors_independent': not (small_set & (giant_set | nest_set)),
        'violations': violations,
    }


def coexistence_ok(giant_ids, small_ids, nest_ids):
    """True when the declared Giant/small/nest generator roles are disjoint.

    Requires at least one Giant, exactly one nest per Giant, and pairwise
    disjoint Giant/small/nest generator ids. Malformed containers or ids raise
    ``ValueError``; a well-formed but invalid arrangement returns ``False``.
    """
    return coexistence_report(giant_ids, small_ids, nest_ids)['ok']


# ---------------------------------------------------------------------------
# Native P2CargoContest consumer mirror (lane 18, small Breadbug id 38).
#
# The native side drives lane-06 ``P2CargoContest`` for the small Breadbug
# (source id 38, native carry power 2) and emits the agreed ``P2_BREADBUG_*``
# markers. This section is a self-contained Python mirror of that header-only
# state machine (integer rules only) plus regex parsing and gate validation
# for the native log lines. See ``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``.
# ---------------------------------------------------------------------------
import re

SMALL_CONTEST_IDENTITY = 'onion:p2:38:0'

# Fixed small-Breadbug contest parameters; ``source_token`` and ``identity`` are
# filled in by ``small_contest_config`` because the token names the generator.
SMALL_CONTEST_CONFIG = {
    'min_threshold': 1,
    'max_threshold': 2,
    'freeze_seconds': 0.5,
    'required_carriers': 1,
    'max_carriers': 0,
}

OUTCOME_HELD = 'held'
OUTCOME_STOLEN = 'stolen'
OUTCOME_RELEASED = 'released'

REASON_TIMEOUT = 'timeout'
REASON_INTERRUPTED = 'interrupted'
REASON_OWNER_DIED = 'owner_died'
REASON_REVISIT = 'revisit'


def small_contest_config(generator):
    """Small Breadbug (38) P2 cargo-contest consumer configuration.

    ``identity`` is fixed to ``onion:p2:38:0`` and ``source_token`` becomes
    ``nest:<generator>``. Two carriers are required to reach ``max_threshold=2``
    and steal; a single carrier (strength 1) stays held because one carrier is
    not below ``required_carriers`` and ``1 < min_threshold`` is False.
    """
    if type(generator) is not int:
        raise ValueError('Generator id must be an int')
    if not 0 <= generator <= MAX_GENERATOR_ID:
        raise ValueError('Generator id out of range')
    config = dict(SMALL_CONTEST_CONFIG)
    config['identity'] = SMALL_CONTEST_IDENTITY
    config['source_token'] = 'nest:%d' % generator
    return config


class SmallContestMirror:
    """Python mirror of lane-06 ``P2CargoContest`` for the small Breadbug.

    Every carrier token contributes strength 1, so ``max_threshold=2`` needs two
    carriers to steal and a single carrier stays held. Stolen is sticky: once
    stolen, ``update``, ``interrupt``, ``on_owner_died``, ``on_revisit`` and
    ``reset`` all leave the outcome unchanged.
    """

    def __init__(self, generator, config=None):
        if config is None:
            config = small_contest_config(generator)
        else:
            config = dict(config)
        self.identity = config['identity']
        self.source_token = config['source_token']
        self.min_threshold = config['min_threshold']
        self.max_threshold = config['max_threshold']
        self.freeze_seconds = config['freeze_seconds']
        self.required_carriers = config['required_carriers']
        self.max_carriers = config['max_carriers']
        self._started = None
        self._outcome = OUTCOME_HELD
        self._reason = None
        self._granted = set()

    @property
    def outcome(self):
        return self._outcome

    @property
    def reason(self):
        return self._reason

    def begin(self):
        """Reset to Held; the durable exactly-once receipt latch is not cleared."""
        self._outcome = OUTCOME_HELD
        self._reason = None
        self._started = None
        return self._outcome

    def update(self, now_seconds, carrier_tokens):
        """Advance the contest with ``carrier_tokens`` (each contributing 1)."""
        now = _strength(now_seconds)
        if isinstance(carrier_tokens, (str, bytes)) or not isinstance(
                carrier_tokens, (list, tuple)):
            raise ValueError('carrier_tokens must be a list or tuple')
        tokens = list(carrier_tokens)
        for token in tokens:
            if not isinstance(token, str):
                raise ValueError('Carrier token must be a string')
        if self._outcome == OUTCOME_STOLEN:
            return self._outcome
        if self._started is None:
            self._started = now
        if self.max_carriers:
            tokens = tokens[:self.max_carriers]
        strengths = [1] * len(tokens)
        total = sum(strengths)
        strong = sum(1 for strength in strengths if strength > 0)
        if self.max_threshold > 0 and total >= self.max_threshold:
            self._outcome = OUTCOME_STOLEN
            self._reason = None
        elif strong < self.required_carriers:
            if self.freeze_seconds > 0 and now - self._started >= self.freeze_seconds:
                self._outcome = OUTCOME_RELEASED
                self._reason = REASON_TIMEOUT
            else:
                self._outcome = OUTCOME_HELD
                self._reason = None
        else:
            self._outcome = OUTCOME_HELD
            self._reason = None
        return self._outcome

    def _mark_released(self, reason):
        if self._outcome == OUTCOME_STOLEN:
            return self._outcome
        self._outcome = OUTCOME_RELEASED
        self._reason = reason
        return self._outcome

    def interrupt(self):
        return self._mark_released(REASON_INTERRUPTED)

    def on_owner_died(self):
        return self._mark_released(REASON_OWNER_DIED)

    def on_revisit(self):
        return self._mark_released(REASON_REVISIT)

    def reset(self):
        return self._mark_released(REASON_REVISIT)

    def grant_receipt(self, key=None):
        """Grant exactly once, raising unless the last outcome is Stolen.

        The receipt is de-duplicated in-process by ``key`` (defaults to the
        consumer ``source_token``), mirroring the native ``mReceiptGranted``
        latch plus durable ledger de-dupe.
        """
        if self._outcome != OUTCOME_STOLEN:
            raise ValueError('Grant receipt requires a stolen outcome')
        dedupe_key = self.source_token if key is None else key
        if dedupe_key in self._granted:
            return False
        self._granted.add(dedupe_key)
        return True


_MARKER_RE = re.compile(
    r'(P2_BREADBUG_CONTEST_BEGIN|P2_BREADBUG_CONTEST_UPDATE|'
    r'P2_BREADBUG_CONTEST_STOLEN|P2_BREADBUG_CONTEST_GRANT|'
    r'P2_BREADBUG_OWNER_DIED|P2_BREADBUG_REVISIT)\b')
_FIELD_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("[^"]*"|\S+)')


def _marker_fields(line):
    marker = _MARKER_RE.match(line)
    if marker is None:
        return None, None
    fields = {}
    for key, value in _FIELD_RE.findall(line):
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        fields[key] = value
    return marker.group(1), fields


def _field_int(fields, name):
    value = fields.get(name, '0')
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError('Malformed %s value in marker: %r' % (name, value))


def parse_contest_consumer(text, generator):
    """Parse P2 Breadbug cargo-contest markers into observed events.

    Only marker lines whose ``generator=`` equals ``generator`` are counted. The
    result records whether each gate input was observed (``began``, ``held``,
    ``stolen``, ``released``, ``granted``, ``owner_died``, ``revisit``), plus the
    exact grant count and duplicate flag for the exactly-once check.
    """
    target = str(generator)
    events = {
        'generator': generator,
        'began': False,
        'held': False,
        'stolen': False,
        'released': False,
        'granted': False,
        'grant_duplicate': False,
        'grants': 0,
        'owner_died': False,
        'owner_died_released': False,
        'revisit': False,
        'update_outcomes': [],
        'pass_marker': False,
    }
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('PASS P2_BREADBUG_CONTEST'):
            events['pass_marker'] = True
            continue
        marker, fields = _marker_fields(line)
        if marker is None:
            continue
        if fields.get('generator') is not None and fields['generator'] != target:
            continue
        if marker == 'P2_BREADBUG_CONTEST_BEGIN':
            events['began'] = True
        elif marker == 'P2_BREADBUG_CONTEST_UPDATE':
            outcome = fields.get('outcome')
            if outcome in (OUTCOME_HELD, OUTCOME_STOLEN, OUTCOME_RELEASED):
                events[outcome] = True
                events['update_outcomes'].append(outcome)
        elif marker == 'P2_BREADBUG_CONTEST_STOLEN':
            events['stolen'] = True
            if _field_int(fields, 'released') == 1:
                events['released'] = True
        elif marker == 'P2_BREADBUG_CONTEST_GRANT':
            if _field_int(fields, 'granted') == 1:
                events['granted'] = True
                events['grants'] += 1
            if _field_int(fields, 'duplicate') == 1:
                events['grant_duplicate'] = True
        elif marker == 'P2_BREADBUG_OWNER_DIED':
            events['owner_died'] = True
            if _field_int(fields, 'released') == 1:
                events['owner_died_released'] = True
        elif marker == 'P2_BREADBUG_REVISIT':
            if _field_int(fields, 'rearmed') == 1:
                events['revisit'] = True
    return events


def validate_contest_consumer(events):
    """Assert the four P2 Breadbug contest-consumer gates from observed events.

    (a) a begin marker was observed; (b) a full contest ran (held then
    stolen + released + granted); (c) an owner death released the cargo
    (``released=1``); and (d) the grant was emitted exactly once: exactly one
    ``granted=1`` and one ``duplicate=1`` (the refused re-grant across the
    revisit proves the durable ledger did not re-credit it).
    """
    began = bool(events.get('began'))
    held = bool(events.get('held'))
    stolen = bool(events.get('stolen'))
    released = bool(events.get('released'))
    granted = bool(events.get('granted'))
    owner_died = bool(events.get('owner_died'))
    owner_died_released = bool(events.get('owner_died_released'))
    grants = int(events.get('grants', 0))
    grant_duplicate = bool(events.get('grant_duplicate'))

    gate_began = began
    gate_contest = held and stolen and released and granted
    gate_owner_died = owner_died and owner_died_released
    gate_grant = granted and grants == 1 and grant_duplicate

    checks = {
        'began': began,
        'held': held,
        'stolen': stolen,
        'released': released,
        'granted': granted,
        'owner_died': owner_died,
        'owner_died_released': owner_died_released,
        'grant_exactly_once': gate_grant,
        'gate_began': gate_began,
        'gate_held_then_stolen_released_granted': gate_contest,
        'gate_owner_died_released': gate_owner_died,
        'gate_grant_exactly_once': gate_grant,
    }
    passed = gate_began and gate_contest and gate_owner_died and gate_grant
    return {'passed': passed, 'checks': checks}
