"""Pikmin 2 flora / Candypop source behavior reference (lane 23, #171).

Pure-Python, side-effect-free, engine-independent encoding of the source
behavior for the 25 flora identities in the #171 audit: Pellet Posy
(``Pelplant``, enemy ID 0), the six Candypop Buds (``BluePom`` 3 ..
``RandPom`` 8), the nonspawnable shared base ``Pom`` (82) and the seventeen
enemy-manager plants (46-52, 80/81, 85-92). Nothing here executes game
behavior, touches the ISO or a native build. Every fact carries a source
citation in its comment (paths are relative to ``native/pikmin2-research``
unless they name a disc file). Header constructor defaults and US GPVE01
revision 0 disc values are kept as distinct fields and never flattened.

This is a behavior *policy model* only. Pellet capture/release on the posy and
the Onion-side seed reward, the native Candypop actor, plant spawn placement
and Hikari camera-facing work remain with the receiver/native lanes. Audit:
``docs/PIKMIN2_FLORA_AUDIT.md`` (#171). Asset contract:
``docs/PIKMIN2_FLORA_ASSETS.md`` (#353).
"""
import math

# Facts the audit labels reconstructed / approximated rather than extracted
# from a serialized table. ``plant_floor_offset`` additionally conflicts with
# the later asset contract (see that function).
RECONSTRUCTED = (
    # audit "floor offset" reading vs the FLORA_ASSETS section 5 correction
    'plant_floor_offset',
    # which disc value (45/20) belongs to small vs large brown figwort
    'brown_figwort_offset_assignment',
)


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Expected finite number')
    return value


def _species(name, table):
    if name not in table:
        raise ValueError('Unknown flora identity')
    return table[name]


def _cycle_index(elapsed_seconds, change_seconds):
    """Integer cycle step with a small epsilon so exact multiples floor right."""
    if elapsed_seconds < 0.0 or change_seconds <= 0.0:
        raise ValueError('Invalid colour cycle time')
    return int(math.floor(elapsed_seconds / change_seconds + 1e-9))


# ---------------------------------------------------------------------------
# Identity, registration and spawnability (audit lines 12-25)
# ---------------------------------------------------------------------------

# enemyInfo.h:59 (Pelplant = 0), :62-67 (BluePom..RandPom = 3-8),
# :105-111 (Tanpopo..Wakame_l = 46-52), :139-151 (Tukushi..KareOoinu_l =
# 80/81/85-92), :141 (EnemyID_Pom = 82). Registry rows: enemyInfo.cpp:10
# (Pelplant), :18 (Pom base), :19-24 (colour buds), :70-86 (plants).
FLORA = {
    'Pelplant': 0,
    'BluePom': 3, 'RedPom': 4, 'YellowPom': 5,
    'BlackPom': 6, 'WhitePom': 7, 'RandPom': 8,
    'Tanpopo': 46, 'Clover': 47, 'HikariKinoko': 48,
    'Ooinu_s': 49, 'Ooinu_l': 50, 'Wakame_s': 51, 'Wakame_l': 52,
    'Tukushi': 80, 'Watage': 81,
    'DaiodoRed': 85, 'DaiodoGreen': 86, 'Magaret': 87, 'Nekojarashi': 88,
    'Chiyogami': 89, 'Zenmai': 90, 'KareOoinu_s': 91, 'KareOoinu_l': 92,
    'Pom': 82,
}

# The six colour buds are one class (Game::Pom::Obj) registered with parent
# EnemyID_Pom and the literal resource "Pom" (enemyInfo.cpp:19-24); the
# per-slot identity is stamped from the six colour counts (PomMgr.cpp:95-109).
POM_SPECIES = ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom',
               'RandPom')
POM_BASE = 'Pom'
POM_BASE_ID = 82  # enemyInfo.h:141, EFlag_UseOwnID only, no EFlag_CanBeSpawned

# enemyInfo.h:35,141 and the inventory classify the base as a shared
# implementation dependency that must never be exposed as a spawnable
# identity (audit line 18, 55-58).
NONSPAWNABLE_BASES = {POM_BASE: POM_BASE_ID}

# The enemy-parms flora (Pelplant + six buds, each with a ProperParms block)
# and the prop flora (Plants::Obj scenery, plain EnemyParmsBase, no proper
# block; plantsMgr.cpp:18-21).
ENEMY_FLORA = ('Pelplant',) + POM_SPECIES
PLANT_SPECIES = ('Tanpopo', 'Clover', 'HikariKinoko', 'Ooinu_s', 'Ooinu_l',
                 'Wakame_s', 'Wakame_l', 'Tukushi', 'Watage', 'DaiodoRed',
                 'DaiodoGreen', 'Magaret', 'Nekojarashi', 'Chiyogami',
                 'Zenmai', 'KareOoinu_s', 'KareOoinu_l')

CLASSIFICATION = {}
for _name in FLORA:
    if _name in NONSPAWNABLE_BASES:
        CLASSIFICATION[_name] = 'nonspawnable_base'
    elif _name in ENEMY_FLORA:
        CLASSIFICATION[_name] = 'enemy_flora'
    else:
        CLASSIFICATION[_name] = 'prop_flora'

# Every non-base identity is a registered spawnable ID. Ten of the plants are
# used placements in story caves (cave type 6 rosters, RandPlantUnit.cpp) or
# the surface (plantsgen.txt, baseGameSection.cpp:660-677); none appears at
# day end (audit lines 112-116). This is registration, not runtime placement.
SPAWNABLE_IDS = frozenset(name for name in FLORA if name not in NONSPAWNABLE_BASES)


def is_spawnable(species):
    """True for every registered identity except the shared base Pom (82).

    The base has no EFlag_CanBeSpawned and no Mgr slot; remapping it would
    corrupt the "unset enemy type" convention (audit lines 55-58, 132-133).
    """
    _species(species, FLORA)
    return species in SPAWNABLE_IDS


# ---------------------------------------------------------------------------
# Pellet Posy (Pelplant, enemy ID 0)
# ---------------------------------------------------------------------------

# StateID, Pelplant.h:37-50.
PELPLANT_STATES = {'waitsmall': 0, 'waitmiddle': 1, 'waitfull': 2,
                   'growsmallmid': 3, 'growmidfull': 4, 'damage': 5,
                   'dead': 6, 'witherfull': 7, 'withermiddle': 8,
                   'withersmall': 9}
PELPLANT_STATES_SOURCE = 'include/Game/Entities/Pelplant.h:37-50'

# Growth stage names used by the pure model.
PELPLANT_STAGES = ('small', 'middle', 'full')

# ProperParms: header constructor values (Pelplant.h:281-292) vs US GPVE01
# rev 0 disc (enemy/parm/enemyParms.szs pelplant/enemyparm.txt). fp01 is
# small->middle, fp02 middle->full, fp03 the random colour cycle. Header
# 120/120/1.5, disc 90/60/1.5.
PELPLANT_PROPER_HEADER = {'fp01': 120.0, 'fp02': 120.0, 'fp03': 1.5,
                          'source': 'include/Game/Entities/Pelplant.h:284-286'}
PELPLANT_PROPER_DISC = {'fp01': 90.0, 'fp02': 60.0, 'fp03': 1.5,
                        'source': 'enemy/parm/enemyParms.szs pelplant/enemyparm.txt'}

# General block disc health (Pelplant.cpp health 50; only Full is vulnerable).
PELPLANT_DISC_HEALTH = {'key': 'fp00', 'value': 50.0,
                        'source': 'enemy/parm/enemyParms.szs pelplant/enemyparm.txt'}

# Generator pellet sizes (audit lines 35-38); 10 and 20 use the bgrow1 clip
# and bdamage1/bdead1 are unreachable in code.
PELPLANT_PELLET_SIZES = (1, 5, 10, 20)
PELPLANT_PELLET_BGROW_SIZES = frozenset((10, 20))

# Collision part special code ending in '0' (the head, s__0 on disc) fells the
# posy instantly when a Pikmin latches (pelplant.cpp:485, :518).
PELPLANT_INSTANT_FELL_SUFFIX = '0'

# The colour cycle is purely time based (pelplant.cpp:407-450). No source makes
# the flower follow the attacking Pikmin's colour.
PELLET_FOLLOWS_ATTACKER_COLOUR = False
PELLET_COLOUR_CYCLE = ('blue', 'red', 'yellow')

# Dead state calls endCapture and releases the captured pellet rather than
# destroying it (pelplantState.cpp:445-451). There is no regrowth timer; a new
# posy is a generator respawn (audit lines 43-49).
PELPLANT_HAS_REGROWTH_TIMER = False


def pellet_growth(stage, elapsed_seconds, *, growing,
                  fp01_seconds=PELPLANT_PROPER_DISC['fp01'],
                  fp02_seconds=PELPLANT_PROPER_DISC['fp02']):
    """Seconds-based growth stage for the elapsed time in the current stage.

    small -> middle after fp01 and middle -> full after fp02, advancing only
    while the Growing flag is set (pelplantState.cpp:193-257, audit lines
    33-36). ``stage`` is one of PELPLANT_STAGES; full is terminal.
    """
    if stage not in PELPLANT_STAGES:
        raise ValueError('Unknown posy growth stage')
    _finite(elapsed_seconds)
    _finite(fp01_seconds)
    _finite(fp02_seconds)
    if not growing:
        return stage
    if stage == 'small':
        return 'middle' if elapsed_seconds >= fp01_seconds else 'small'
    if stage == 'middle':
        return 'full' if elapsed_seconds >= fp02_seconds else 'middle'
    return 'full'


def pellet_is_vulnerable(stage):
    """Only a full posy takes damage (Pelplant.h:187-190, audit lines 43-44)."""
    if stage not in PELPLANT_STAGES:
        raise ValueError('Unknown posy growth stage')
    return stage == 'full'


def pellet_size_uses_bgrow(size):
    """Pellet sizes 10 and 20 play bgrow1 (audit lines 36-38)."""
    if size not in PELPLANT_PELLET_SIZES:
        raise ValueError('Invalid pellet size')
    return size in PELPLANT_PELLET_BGROW_SIZES


def pellet_instant_fell(part_code):
    """True when a collision part's special code ends in '0' (s__0 head).

    A Pikmin latching such a part fells the posy instantly
    (pelplant.cpp:485, :518). ``part_code`` is the raw special code, which may
    be empty.
    """
    if not isinstance(part_code, str):
        raise ValueError('Expected part special code string')
    return part_code.endswith(PELPLANT_INSTANT_FELL_SUFFIX) and part_code != ''


def pellet_released_on_death(*, captured, state):
    """The dead state releases the captured pellet instead of destroying it.

    Returns True only in the dead state while a pellet is still captured
    (pelplantState.cpp:445-451). Any other state destroys nothing here.
    """
    if state not in PELPLANT_STATES:
        raise ValueError('Unknown posy state')
    return bool(captured) and state == 'dead'


def pellet_colour(*, generator_colour=None, random_setting, elapsed_seconds=0.0,
                  met_colours=(), change_seconds=PELPLANT_PROPER_DISC['fp03']):
    """Posy colour: fixed by the generator, or a time-based cycle when random.

    With the random setting the colour advances every fp03 seconds through
    Blue, Red, Yellow, skipping colours not yet met (pelplant.cpp:407-450,
    audit lines 39-42). It never follows the attacker's colour.
    """
    if not random_setting:
        if generator_colour not in PELLET_COLOUR_CYCLE:
            raise ValueError('Invalid generator colour')
        return generator_colour
    _finite(elapsed_seconds)
    _finite(change_seconds)
    step = _cycle_index(elapsed_seconds, change_seconds)
    cycle = [c for c in PELLET_COLOUR_CYCLE if c in set(met_colours)]
    if not cycle:
        raise ValueError('No met colours for the random cycle')
    return cycle[step % len(cycle)]


# ---------------------------------------------------------------------------
# Candypop Buds (Pom family, enemy IDs 3-8)
# ---------------------------------------------------------------------------

# StateID, Pom.h:153-161.
POM_STATES = {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
              'swing': 5}
POM_STATES_SOURCE = 'include/Game/Entities/Pom.h:153-161'

# The Queen's spitting colour cycle is a deterministic Blue/Red/Yellow cycle
# (Pom.cpp:330-355); it is not random (audit lines 74-75).
QUEEN_COLOUR_CYCLE = ('blue', 'red', 'yellow')

# ProperParms: header (Pom.h:96-115) vs disc. ip01 is the colour-bud lifetime
# slot budget, ip11 the Queen's; ip13 the Queen's shoots-per-Pikmin; fp01 the
# open time after the last swallow; fp02 the Queen colour cycle. ip02, ip12 and
# fp03 are serialized but unread (audit lines 70-73).
POM_PROPER_HEADER = {'ip01': 5, 'ip11': 1, 'ip13': 5, 'fp01': 30.0,
                     'fp02': 1.25, 'fp03': 0.15,
                     'source': 'include/Game/Entities/Pom.h:100-105'}
POM_PROPER_DISC = {'ip01': 5, 'ip02': 1, 'ip11': 1, 'ip12': 1, 'ip13': 9,
                   'fp01': 1.0, 'fp02': 2.6, 'fp03': 0.0,
                   'source': 'enemy/parm/enemyParms.szs pom/enemyparm.txt'}
POM_UNREAD_KEYS = ('ip02', 'ip12', 'fp03')

# Pikmin enter only through a press on the slot part (radius 30) while armed
# (Pom.cpp:154-169); any colour is accepted.
POM_SLOT = {'joint': 'jnt_center', 'radius': 30.0, 'press_only': True,
            'accepts_any_colour': True,
            'source': 'src/plugProjectNishimuraU/Pom.cpp:154-201'}

# Queen sprouts are leaf Pikihead births launched with random bearing
# (Pom.cpp:280-322, audit lines 66-73).
POM_SPROUT_LAUNCH = (110.0, 750.0, 110.0)
POM_SPROUT_MATURITY = 'leaf'
POM_BULBMIN_NOT_COUNTED_AS_LOSS = True

# Bud colour and per-species budget/multiplier/refund table. The colour-bud
# budget is ip01 (5) and the Queen's ip11 (1); throwing in a colour bud's own
# colour refunds the slot (Pom.cpp:296-298). BlackPom is the Violet bud
# (purple) and WhitePom the Ivory bud (white).
CANDYPOPS = {
    'BluePom': {'enemy_id': 3, 'colour': 'blue', 'budget_key': 'ip01',
                'budget': 5, 'queen': False, 'shot_multiplier': 1,
                'own_colour_refund': True},
    'RedPom': {'enemy_id': 4, 'colour': 'red', 'budget_key': 'ip01',
               'budget': 5, 'queen': False, 'shot_multiplier': 1,
               'own_colour_refund': True},
    'YellowPom': {'enemy_id': 5, 'colour': 'yellow', 'budget_key': 'ip01',
                  'budget': 5, 'queen': False, 'shot_multiplier': 1,
                  'own_colour_refund': True},
    'BlackPom': {'enemy_id': 6, 'colour': 'purple', 'budget_key': 'ip01',
                 'budget': 5, 'queen': False, 'shot_multiplier': 1,
                 'own_colour_refund': True},
    'WhitePom': {'enemy_id': 7, 'colour': 'white', 'budget_key': 'ip01',
                 'budget': 5, 'queen': False, 'shot_multiplier': 1,
                 'own_colour_refund': True},
    'RandPom': {'enemy_id': 8, 'colour': None, 'budget_key': 'ip11',
                'budget': 1, 'queen': True, 'shot_multiplier': 9,
                'own_colour_refund': False},
}

# Story-cave spawn gating, PomMgr.cpp:38-89 (audit lines 75-80): Violet
# (BlackPom) and Ivory (WhitePom) refuse to spawn on floors 1-2 (or in
# Emergence Cave and White Flower Garden) once the player already holds 20 of
# that colour; Ivory additionally needs Whites met except in White Flower
# Garden; Lapis (BluePom) and Golden (YellowPom) need their colour met.
POM_EARLY_FLOORS = (1, 2)
POM_EARLY_CAVES = ('Emergence Cave', 'White Flower Garden')
POM_COLOUR_CAP = {'BlackPom': 20, 'WhitePom': 20}
POM_COLOUR_MET_REQUIRED = {'BluePom': 'blue', 'YellowPom': 'yellow',
                           'WhitePom': 'white'}
POM_WHITE_FLOWER_GARDEN = 'White Flower Garden'

# Dropped buds land exactly on their point (excluded from drop jitter) and are
# invulnerable once they land; death only from an exhausted budget. Bitter
# immune, no shadow, no corpse (audit lines 79-82).
POM_EXCLUDED_FROM_DROP_JITTER = True
POM_INVULNERABLE_AFTER_LANDING = True
POM_BITTER_IMMUNE = True
POM_HAS_SHADOW = False
POM_HAS_CORPSE = False

# First Violet / Ivory bud cutscene trigger radius (navi_demoCheck.cpp:42).
POM_CUTSCENE_TRIGGER_RADIUS = 350.0


def candypop_budget(species):
    """Lifetime slot budget: ip01 (5) for colour buds, ip11 (1) for the Queen."""
    info = _species(species, CANDYPOPS)
    return info['budget']


def candypop_own_colour(species):
    """Bud colour (None for the cycling Queen)."""
    return _species(species, CANDYPOPS)['colour']


def candypop_accept(*, species, slot_pressed, armed, used_slots):
    """True when a Pikmin is accepted through the slot press.

    Entry needs a press on the slot part while the bud is armed and under its
    lifetime budget (Pom.cpp:154-169). Any colour is accepted, so no colour
    argument exists.
    """
    info = _species(species, CANDYPOPS)
    if type(used_slots) is not int or used_slots < 0:
        raise ValueError('Expected non-negative slot count')
    return bool(slot_pressed) and bool(armed) and used_slots < info['budget']


def candypop_refund(*, species, thrown_colour):
    """True when throwing the bud's own colour refunds a slot.

    Pom.cpp:296-298 refunds an own-colour throw for the colour buds; the Queen
    has no own-colour refund path (FLORA_ASSETS §2, §8).
    """
    info = _species(species, CANDYPOPS)
    if thrown_colour not in ('blue', 'red', 'yellow', 'purple', 'white'):
        raise ValueError('Unknown Pikmin colour')
    return bool(info['own_colour_refund'] and thrown_colour == info['colour'])


def candypop_close(*, seconds_since_last_swallow, remain_open_seconds,
                   budget_spent, pikmin_inside):
    """Close outcome after fp01 elapses or the budget is used.

    Returns None while still open; 'shot' if Pikmin are inside, else 'reopen'
    (PomState.cpp:101-235, audit lines 60-64). ``remain_open_seconds`` is fp01
    (1.0 disc; 30 header).
    """
    _finite(seconds_since_last_swallow)
    _finite(remain_open_seconds)
    closing = bool(budget_spent) or seconds_since_last_swallow >= remain_open_seconds
    if not closing:
        return None
    return 'shot' if pikmin_inside else 'reopen'


def candypop_shot_count(*, species, swallowed):
    """Sprouts born per swallowed Pikmin: ip13 (9) for the Queen, else 1.

    The stuck Pikmin is killed without counting as a loss and replaced by
    sprouts of the bud colour (Pom.cpp:280-322, audit lines 66-73).
    """
    info = _species(species, CANDYPOPS)
    if type(swallowed) is not int or swallowed < 0:
        raise ValueError('Expected non-negative Pikmin count')
    return swallowed * info['shot_multiplier']


def candypop_queen_colour(*, elapsed_seconds, met_colours,
                          change_seconds=POM_PROPER_DISC['fp02']):
    """Deterministic Queen colour cycle skipping unmet colours (Pom.cpp:330-355).

    Advances every fp02 seconds (2.6 disc) through Blue, Red, Yellow. Not
    random (audit lines 74-75).
    """
    _finite(elapsed_seconds)
    _finite(change_seconds)
    step = _cycle_index(elapsed_seconds, change_seconds)
    cycle = [c for c in QUEEN_COLOUR_CYCLE if c in set(met_colours)]
    if not cycle:
        raise ValueError('No met colours for the Queen cycle')
    return cycle[step % len(cycle)]


def candypop_spawn_allowed(*, species, floor, cave, met_colours, player_count):
    """Story-cave spawn gate for a Candypop bud (PomMgr.cpp:38-89).

    ``floor`` is 1-based; ``cave`` is the story cave display name. Returns
    False when the source refuses to place the bud.
    """
    info = _species(species, CANDYPOPS)
    if type(floor) is not int or floor < 1:
        raise ValueError('Expected 1-based floor')
    if type(player_count) is not int or player_count < 0:
        raise ValueError('Expected non-negative Pikmin count')
    met = set(met_colours)
    if species in POM_COLOUR_CAP:
        early = floor in POM_EARLY_FLOORS or cave in POM_EARLY_CAVES
        if early and player_count >= POM_COLOUR_CAP[species]:
            return False
    required = POM_COLOUR_MET_REQUIRED.get(species)
    if required and required not in met:
        if not (species == 'WhitePom' and cave == POM_WHITE_FLOWER_GARDEN):
            return False
    return True


def candypop_state_name(state_id):
    """Name (``wait|dead|open|close|shot|swing``) for a P2 source state index.

    ``POM_STATES`` indexes the six ``Game::Pom::Obj`` state IDs
    (Pom.h:153-161); the native module observably walks
    ``wait -> open -> swing -> close -> shot -> (dead | wait)``.
    """
    if type(state_id) is not int:
        raise ValueError('Expected an integer state id')
    for name, ident in POM_STATES.items():
        if ident == state_id:
            return name
    raise ValueError('Unknown Candypop state id')


def candypop_dead(*, budget_spent, sprout_pending):
    """True only on an exhausted lifetime budget with no pending sprouts.

    Death is budget-only (audit lines 79-82): no combat path and no corpse.
    ``sprout_pending`` is the outstanding sprout demand; the bud must settle
    conservation before it may die so a consumed Pikmin's sprouts are never
    silently discarded.
    """
    if type(sprout_pending) is not int or sprout_pending < 0:
        raise ValueError('Expected non-negative pending sprout count')
    return bool(budget_spent) and sprout_pending == 0


# ---------------------------------------------------------------------------
# Enemy-manager plants (seventeen IDs, 46-52 and 80/81/85-92)
# ---------------------------------------------------------------------------

# One base Plants::Obj with an empty subclass per species; separate resources,
# a single PLANTANIM_Default clip, no FSM (plantsMgr.h:36-39). Invulnerable,
# bitter-immune, no corpse; the disc health of 1100 is never read
# (audit lines 89-99).
PLANT_BASE = 'Plants'
PLANT_DISC_HEALTH = {'key': 'fp00', 'value': 1100.0, 'read': False,
                     'source': 'enemy/parm/enemyParms.szs <name>/enemyparm.txt'}
PLANT_ANIM_COUNT = 1
PLANT_HAS_FSM = False
PLANT_INVULNERABLE = True
PLANT_BITTER_IMMUNE = True
PLANT_HAS_CORPSE = False

# General parameters are repurposed as LOD volumes: territory lifts the sphere,
# private and home radius define cylinders for the paper, glowstems, glowcap,
# foxtail, horsetail, shoots and fiddlehead (audit lines 99-102).
PLANT_LOD_ROLES = {'territory': 'lifted_sphere',
                   'private_radius': 'cylinder',
                   'home_radius': 'cylinder',
                   'fp01': 'floor_offset'}

# The audit reads fp01 on Clover and the brown figworts as the general floor
# offset (25/45/20 disc, audit lines 100-102). The asset contract corrects
# Clover: its general fp01 is 40.0 and the 25.0 value belongs to an inert,
# unreferenced trailing block (FLORA_ASSETS §5, plantsMgr.cpp:46-48). The
# audit's brown-figwort-to-value assignment is not stated. RECONSTRUCTED.
PLANT_FLOOR_OFFSET = {
    'Clover': {'audit_disc': 25.0, 'general_fp01_disc': 40.0,
               'inert_extra_fp01_disc': 25.0},
    'KareOoinu_s': {'audit_disc': 45.0},
    'KareOoinu_l': {'audit_disc': 20.0},
}

# Sway-on-touch: a captain or Pikmin moving faster than 1 unit past the
# collision volume restarts the single clip; only captains trigger the touch
# sound (plants.cpp:141-166). Purple quakes also sway them.
PLANT_SWAY_MIN_SPEED = 1.0
PLANT_CAPTAIN_TOUCH_SOUND = 'PSSE_PL_TOUCH_LEAF'

# Spectralid spawn sentinel: a generator carrying the sentinel spawns five
# yellow Spectralids on the first touch (plants.cpp:187-201). Only Tanpopo,
# Ooinu_l and Magaret declare the child and reserve slots
# (enemyInfo.cpp:70,76,83; generalEnemyMgr.cpp:818-838); any other species so
# configured would spawn without a reservation.
SPECTRALID_PER_TOUCH = 5
SPECTRALID_DECLARED = ('Tanpopo', 'Ooinu_l', 'Magaret')
SPECTRALID_CHILD = 'ShijimiChou'

# Piklopedia: eleven entries (59-69) registered by finishing a sway;
# EFlag_HasNoInfo variants fold into a representative (enemyInfo.cpp:74,78;
# audit lines 108-111, inventory). Chiyogami is used content (Shower Room
# floor 2) with no representative entry.
PIKLOPEDIA_ENTRIES = {
    'HikariKinoko': 59, 'Clover': 60, 'Ooinu_l': 61, 'Tanpopo': 62,
    'Watage': 63, 'Tukushi': 64, 'Nekojarashi': 65, 'DaiodoRed': 66,
    'Magaret': 67, 'Zenmai': 68, 'Wakame_l': 69,
}
HAS_NO_INFO = ('Ooinu_s', 'Wakame_s', 'DaiodoGreen', 'Chiyogami',
               'KareOoinu_s', 'KareOoinu_l')
HAS_NO_INFO_FOLDED_INTO = {
    'Ooinu_s': 'Ooinu_l',
    'Wakame_s': 'Wakame_l',
    'DaiodoGreen': 'DaiodoRed',
    'KareOoinu_s': 'Ooinu_l',
    'KareOoinu_l': 'Ooinu_l',
    'Chiyogami': None,
}

# Cave type 6 plant rosters consume the weight as a target count across free
# plant spawn points, capped at 100; the surface reads plantsgen.txt per course
# after defaultgen.txt (RandPlantUnit.cpp; baseGameSection.cpp:660-677).
PLANT_CAVE_ROSTER_CAP = 100
PLANT_SURFACE_SOURCE = 'plantsgen.txt'


def plant_lod(species, volume):
    """Geometric role of a repurposed general parameter for plant LOD.

    Returns 'lifted_sphere', 'cylinder' or 'floor_offset', or None when the
    parameter is not a LOD volume for that species (audit lines 99-102).
    """
    _species(species, FLORA)
    if species not in PLANT_SPECIES:
        raise ValueError('Not a plant identity')
    role = PLANT_LOD_ROLES.get(volume)
    if role == 'floor_offset' and species not in PLANT_FLOOR_OFFSET:
        return None
    return role


def plant_floor_offset(species):
    """Audit/asset floor-offset reading for Clover/brown figworts.

    Returns the recorded disc values for a plant that carries a floor offset,
    else None. RECONSTRUCTED: the audit's "floor offset" reading conflicts
    with the asset contract for Clover and the brown-figwort assignment is
    not stated (see PLANT_FLOOR_OFFSET).
    """
    _species(species, FLORA)
    return PLANT_FLOOR_OFFSET.get(species)


plant_floor_offset.reconstructed = True


def plant_sways(*, mover, speed, past_volume):
    """True when a mover restarts the plant's sway clip.

    A captain or Pikmin moving faster than PLANT_SWAY_MIN_SPEED past the
    collision volume plays the sway clip; a Purple quake sways it regardless.
    Enemies pass through (plants.cpp:141-166, audit lines 93-99).
    """
    _finite(speed)
    if mover not in ('captain', 'pikmin', 'purple_quake', 'enemy'):
        raise ValueError('Unknown mover kind')
    if mover == 'purple_quake':
        return True
    if mover == 'enemy':
        return False
    return bool(past_volume) and abs(speed) > PLANT_SWAY_MIN_SPEED


def plant_touch_sound(mover):
    """Only captains trigger PSSE_PL_TOUCH_LEAF (plants.cpp:141-166)."""
    if mover not in ('captain', 'pikmin', 'purple_quake', 'enemy'):
        raise ValueError('Unknown mover kind')
    return PLANT_CAPTAIN_TOUCH_SOUND if mover == 'captain' else None


def spectralid_reserved(species):
    """True only for Tanpopo, Ooinu_l and Magaret (enemyInfo.cpp:70,76,83)."""
    _species(species, FLORA)
    return species in SPECTRALID_DECLARED


def spectralid_spawn(*, species, has_sentinel, first_touch):
    """Yellow Spectralids spawned on the plant's first touch.

    Five spawn when the generator carries the sentinel and this is the first
    touch (plants.cpp:187-201). A non-declaring species can still spawn them
    if its generator is flagged, but without a reserved slot
    (generalEnemyMgr.cpp:818-838) -- use spectralid_reserved to distinguish.
    """
    _species(species, FLORA)
    if species not in PLANT_SPECIES:
        raise ValueError('Not a plant identity')
    if not has_sentinel or not first_touch:
        return 0
    return SPECTRALID_PER_TOUCH


def piklopedia_number(species):
    """Piklopedia entry number, or None for a HasNoInfo/base identity."""
    _species(species, FLORA)
    return PIKLOPEDIA_ENTRIES.get(species)


def folded_into(species):
    """Representative entry a HasNoInfo variant folds into, else None."""
    _species(species, FLORA)
    return HAS_NO_INFO_FOLDED_INTO.get(species)
