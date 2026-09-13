"""Source-backed, bounded flora/Candypop import; no native actor install.

Covers enemy IDs 0 Pelplant (Pellet Posy); 3-8 BluePom/RedPom/YellowPom/
BlackPom/WhitePom/RandPom (Lapis Lazuli/Crimson/Golden/Violet/Ivory/Queen
Candypop Buds); and ambient flora 46 Tanpopo (Dandelion), 47 Clover,
48 HikariKinoko (Common Glowcap), 49/50 Ooinu_s/Ooinu_l (Figwort), 51/52
Wakame_s/Wakame_l (Shoot) from the US GPVE01 revision 0 disc. Source audit:
docs/PIKMIN2_FLORA_ASSETS.md (issue #353, parent #171). Extraction follows the
ground-invertebrate lane: hashed disc reads, preserved metadata text, bounded
weighted/rigid pose sampling. No btk playback, no behavior execution, and the
Pellet-to-Pom conversion math is a reference predicate only.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import time
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_breadbug_assets import parameter_blocks, collision_nodes
from experimental.pikmin2_convert import blocks, decode, u16, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks, sample_frames

# Identity map. enemyInfo.h:59 (Pelplant = 0), :62-67 (BluePom..RandPom = 3-8),
# :105-111 (Tanpopo..Wakame_l = 46-52). EnemyID_Pom (82, enemyInfo.h:141) is the
# Candypop shared base and is deliberately not a claimed spawnable identity.
SPECIES = {
    'Pelplant': 0,
    'BluePom': 3, 'RedPom': 4, 'YellowPom': 5,
    'BlackPom': 6, 'WhitePom': 7, 'RandPom': 8,
    'Tanpopo': 46, 'Clover': 47, 'HikariKinoko': 48,
    'Ooinu_s': 49, 'Ooinu_l': 50, 'Wakame_s': 51, 'Wakame_l': 52,
}

# Flora is split into two source classes: the enemy-parms flora (Pelplant and
# the six Candypop colours, each with a species ProperParms block) and the
# prop flora (the Plants::Obj scenery family, which allocates a plain
# EnemyParmsBase with no proper block, plantsMgr.cpp:18-21).
ENEMY_FLORA = ('Pelplant', 'BluePom', 'RedPom', 'YellowPom', 'BlackPom',
               'WhitePom', 'RandPom')
PROP_FLORA = ('Tanpopo', 'Clover', 'HikariKinoko', 'Ooinu_s', 'Ooinu_l',
              'Wakame_s', 'Wakame_l')
CLASSIFICATION = {name: ('enemy_flora' if name in ENEMY_FLORA else 'prop_flora')
                  for name in SPECIES}

POM_SPECIES = ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom',
               'RandPom')
POM_BASE = 'Pom'
POM_BASE_ID = 82  # enemyInfo.h:141

# The colour buds register with parent EnemyID_Pom and empty resource slots
# (enemyInfo.cpp:18-24), so model/animation/parm/collision all resolve to the
# base "Pom" resource directory. Pelplant and the plants use EFlag_UseOwnID.
SHARED_BASE = {name: POM_BASE for name in POM_SPECIES}

# Two-identity (small/large) source groups. 49/50 and 51/52 are registered as
# separate IDs (each with its own Obj/Mgr and resources); the small sibling is
# EFlag_HasNoInfo and folds into the large sibling for Piklopedia purposes.
VARIANT_GROUPS = {'Ooinu': ('Ooinu_s', 'Ooinu_l'),
                  'Wakame': ('Wakame_s', 'Wakame_l')}

COMMON_NAME = {
    'Pelplant': 'Pellet Posy',
    'BluePom': 'Lapis Lazuli Candypop Bud', 'RedPom': 'Crimson Candypop Bud',
    'YellowPom': 'Golden Candypop Bud', 'BlackPom': 'Violet Candypop Bud',
    'WhitePom': 'Ivory Candypop Bud', 'RandPom': 'Queen Candypop Bud',
    'Tanpopo': 'Dandelion', 'Clover': 'Clover',
    'HikariKinoko': 'Common Glowcap', 'Ooinu_s': 'Figwort (red small)',
    'Ooinu_l': 'Figwort (red large)', 'Wakame_s': 'Shoot (small)',
    'Wakame_l': 'Shoot (large)',
}

PARM_SOURCE = 'enemy/parm/enemyParms.szs'
# Every flora parm subdir on GPVE01 rev 0 ships enemyanimmgr/enemyparm/enemycoll
# but NO enemystoneinfo.txt (petrification is an enemy-only parm); absent members
# are recorded per species rather than required.
METADATA_FILES = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt', 'enemystoneinfo.txt')
REQUIRED_METADATA = ('enemyanimmgr.txt', 'enemyparm.txt', 'enemycoll.txt')
MAX_POSES = 12
# Registration filenames include a capital 'L' for the large Figwort/Shoot
# (ooinu_L.bca, wakame_L.bca) while anim.szs stores the members lowercased; the
# shared sheargrub parser rejects the capitals, so this lane parses the same
# token grammar with a case-insensitive file pattern and resolves members by
# casefold at extraction time.
ANIM_FILE = re.compile(r'[A-Za-z0-9_]+\.bca')

# Clip order equals the AnimID enum registration order and the
# enemyanimmgr.txt row order for each species.
# Pelplant.h:328-340 (10 clips, with the bca stems from the enum comments);
# Pom.h:130-138 (6 clips, 'wait'/'dead' plus type1-type4); plantsMgr.h:36-39
# (single PLANTANIM_Default clip). The prop-flora stems use the species
# directory name and are confirmed on disc at extraction time.
CLIPS = {
    'Pelplant': ('damage3', 'dead3', 'grow1', 'grow2', 'wait1', 'wait2',
                 'wait3', 'bgrow1', 'bdamage1', 'bdead1'),
    'BluePom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'RedPom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'YellowPom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'BlackPom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'WhitePom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'RandPom': ('wait', 'dead', 'type1', 'type2', 'type3', 'type4'),
    'Tanpopo': ('tanpopo',),
    'Clover': ('clover',),
    'HikariKinoko': ('hikarikinoko',),
    'Ooinu_s': ('ooinu_s',),
    'Ooinu_l': ('ooinu_l',),
    'Wakame_s': ('wakame_s',),
    'Wakame_l': ('wakame_l',),
}

# Animation key events (frame, type) from each enemyanimmgr.txt on disc,
# cross-checked against docs/PIKMIN2_FLORA_ASSETS.md. Event frames are data
# only: no pellet attach/release, Pikmin swallow, sprout birth or colour
# change executes (see LIMITATIONS).
# Pelplant wait1/wait2/wait3 0:0 29:1, grow/damage/dead no keys.
# Pom type1 25:2 (open arms), type3 20:2 (spit); wait/dead/type2/type4 end only.
EXPECTED_EVENTS = {
    'Pelplant': {
        'damage3': [], 'dead3': [], 'grow1': [], 'grow2': [],
        'wait1': [[0, 0], [29, 1]], 'wait2': [[0, 0], [29, 1]],
        'wait3': [[0, 0], [29, 1]], 'bgrow1': [], 'bdamage1': [],
        'bdead1': [],
    },
    'BluePom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
                'type3': [[20, 2]], 'type4': []},
    'RedPom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
               'type3': [[20, 2]], 'type4': []},
    'YellowPom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
                  'type3': [[20, 2]], 'type4': []},
    'BlackPom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
                 'type3': [[20, 2]], 'type4': []},
    'WhitePom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
                 'type3': [[20, 2]], 'type4': []},
    'RandPom': {'wait': [], 'dead': [], 'type1': [[25, 2]], 'type2': [],
                'type3': [[20, 2]], 'type4': []},
    'Tanpopo': {'tanpopo': []},
    'Clover': {'clover': []},
    'HikariKinoko': {'hikarikinoko': []},
    'Ooinu_s': {'ooinu_s': []},
    'Ooinu_l': {'ooinu_l': []},
    'Wakame_s': {'wakame_s': []},
    'Wakame_l': {'wakame_l': []},
}

# Valid EnemyParmsBase general-block field identifiers (EnemyParmsBase.h:51-150).
# fp07 is not declared; unknown fp/ip keys must be rejected before mutation.
GENERAL_KEYS = frozenset(
    [f'fp{i:02}' for i in (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                           17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                           31, 32, 33, 34, 35, 36, 37, 38)]
    + [f'ip{i:02}' for i in range(1, 8)])

# State IDs from the headers.
# Pelplant.h:37-50, Pom.h:153-161. Prop flora allocate no FSM (plantsMgr.h).
STATE_IDS = {
    'Pelplant': {'waitsmall': 0, 'waitmiddle': 1, 'waitfull': 2,
                 'growsmallmid': 3, 'growmidfull': 4, 'damage': 5, 'dead': 6,
                 'witherfull': 7, 'withermiddle': 8, 'withersmall': 9},
    'BluePom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
                'swing': 5},
    'RedPom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
               'swing': 5},
    'YellowPom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
                  'swing': 5},
    'BlackPom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
                 'swing': 5},
    'WhitePom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
                 'swing': 5},
    'RandPom': {'wait': 0, 'dead': 1, 'open': 2, 'close': 3, 'shot': 4,
                'swing': 5},
    'Tanpopo': {}, 'Clover': {}, 'HikariKinoko': {}, 'Ooinu_s': {},
    'Ooinu_l': {}, 'Wakame_s': {}, 'Wakame_l': {},
}

# Header defaults for the species-specific ProperParms block(s).
# Pelplant.h:281-292, Pom.h:96-115. Prop flora allocate a plain EnemyParmsBase
# (CreatureParms::read + mGeneral.read only, EnemyParmsBase.h:162-166) and so
# have no proper block read at runtime.
PELPLANT_PROPER_DEFAULTS = {'fp01': 120.0, 'fp02': 120.0, 'fp03': 1.5}
POM_PROPER_DEFAULTS = {'ip01': 5, 'ip11': 1, 'ip13': 5, 'fp01': 30.0,
                       'fp02': 1.25, 'fp03': 0.15}
PROPER_PARM_DEFAULTS = {'Pelplant': dict(PELPLANT_PROPER_DEFAULTS)}
for _pom in POM_SPECIES:
    PROPER_PARM_DEFAULTS[_pom] = dict(POM_PROPER_DEFAULTS)
for _plant in PROP_FLORA:
    PROPER_PARM_DEFAULTS[_plant] = {}

# Retail-only keys serialized in the Pom proper block that the decomp's
# Pom::Parms::ProperParms (Pom.h:96-115) does not declare: ip02 and ip12 both
# read 1 on disc. They are preserved as data but are not header defaults.
PROPER_RETAIL_ONLY = {pom: ('ip02', 'ip12') for pom in POM_SPECIES}

# Retail (disc) values verified against enemyparms.szs on US GPVE01 rev 0.
# 'general' is the first EnemyParmsBase block; 'proper' the species block;
# 'extra' an unreferenced trailing block. Header defaults and disc values are
# reported separately, never flattened.
# Pelplant general fp00 health = 50, proper fp01/fp02/fp03 = 90/60/1.5.
# Buds proper: ip01/ip02/ip11/ip12 = 5/1/1/1, ip13 disc 9 (header 5), fp01
# disc 1.0 s (header 30), fp02 disc 2.6 s (header 1.25), fp03 disc 0.0
# (header 0.15). Prop general fp00 health 1100 (never read).
DISC_PARMS = {
    'Pelplant': {'general': {'fp00': 50.0},
                 'proper': {'fp01': 90.0, 'fp02': 60.0, 'fp03': 1.5}},
}
for _pom in POM_SPECIES:
    DISC_PARMS[_pom] = {'general': {},
                        'proper': {'ip01': 5, 'ip02': 1, 'ip11': 1,
                                   'ip12': 1, 'ip13': 9, 'fp01': 1.0,
                                   'fp02': 2.6, 'fp03': 0.0}}
DISC_PARMS.update({
    'Tanpopo': {'general': {'fp00': 1100.0}},
    'Clover': {'general': {'fp00': 1100.0},
               'extra': {'fp01': 25.0}},
    'HikariKinoko': {'general': {'fp00': 1100.0}},
    'Ooinu_s': {'general': {'fp00': 1100.0}},
    'Ooinu_l': {'general': {'fp00': 1100.0}},
    'Wakame_s': {'general': {'fp00': 1100.0}},
    'Wakame_l': {'general': {'fp00': 1100.0}},
})

LOOPS = {0: 'stop at end', 1: 'reset to start and stop', 2: 'repeat',
         3: 'reverse once then stop', 4: 'ping-pong repeat'}

# Pellet-to-Pom conversion is documented as a reference predicate only; no
# converter/arrival wiring is claimed (issue #353 non-claims).
REFERENCE_ONLY = True

LIMITATIONS = [
    'Sampled weighted/rigid poses with approximate materials; no skeletal playback or event execution.',
    'Animation key events, loop markers and parameter text are preserved as data only; no pellet attach/release, Pikmin swallow, sprout birth or colour change executes.',
    'No native runtime, AI/FSM, install, arena placement or generator wiring is provided by this slice.',
    'Candypop buds (BluePom..RandPom) share base Pom (ID 82) for model, animation, parm and collision; base 82 is unspawnable and not claimed as a spawnable identity.',
    'Pellet capture on the Pelplant head and Pom slot conversion math is a reference predicate only (reference_conversion); no converter, arrival or receiver wiring.',
    'Prop flora allocate a plain EnemyParmsBase: only CreatureParms and mGeneral are read (EnemyParmsBase.h:162-166), so general parameters are repurposed as LOD/floor volumes and no proper block is consumed (plantsMgr.cpp:18-21,46-48).',
    'No flora parm subdir ships enemystoneinfo.txt on this disc revision; the absent member is recorded per species in metadata_absent rather than required.',
    'Clover ships an unreferenced third fp01=25 parm block after its general block; it is verified and preserved but never read by Clover::Mgr (plantsMgr.cpp:46-48).',
    'Prop-flora clip stems/event streams follow the single-animation convention (plantsMgr.h:36-39); the Ooinu_l/Wakame_l registration names use a capital L (ooinu_L.bca, wakame_L.bca) while anim.szs stores lowercase members, resolved case-insensitively at extraction time.',
    'ShijimiChou spectralid child linkage (Tanpopo, Ooinu_l) is source-documented only (generalEnemyMgr.cpp:824-836) and is not wired here.',
]

# Opt-in converter tolerances per species (#186); strict defaults everywhere else.
# Pelplant authors zero/annihilated joint scales for hidden and grow-from-nothing
# segments, so its rigid bakes need the singular_normal fallback. HikariKinoko
# ships a shape-matrix type 1 (billboard) quad: 'billboard': 'static' bakes it
# through its rigid joint matrix (camera-facing orientation is not reproduced)
# and 'missing_normals': 'compute' derives the quad's normal from its own baked
# geometry because the source billboard shape carries no normal attribute.
# See docs/PIKMIN2_SINGULAR_SCALE.md (#405) and
# docs/PIKMIN2_BILLBOARD_FALLBACK.md (#429).
TOLERANCES = {
    'Pelplant': {'singular_normal': 'transpose-adjugate-zero'},
    'HikariKinoko': {'billboard': 'static', 'missing_normals': 'compute'},
}
# Opt-in BCA pose (scale) tolerances. 'singular_scale': 'allow' accepts an
# authored zero axis scale and must be paired with the matching
# singular_normal decode policy in TOLERANCES above.
POSE_TOLERANCES = {
    'Pelplant': {'singular_scale': 'allow'},
}

TEXT = (
    'P2_FLORA_1\n'
    'species Pelplant BluePom RedPom YellowPom BlackPom WhitePom RandPom '
    'Tanpopo Clover HikariKinoko Ooinu_s Ooinu_l Wakame_s Wakame_l\n'
    'pelplant_health 50\npelplant_grow_small_mid 90.0\n'
    'pelplant_grow_mid_full 60.0\npelplant_color_change_time 1.5\n'
    'pom_normal_max_slots 5\npom_queen_max_slots 1\n'
    'pom_queen_shot_multiplier 9\npom_remain_open_time 1.0\n'
    'pom_queen_color_change_time 2.6\npom_black_white_appearance_rate 0.15\n'
    'pom_black_white_appearance_rate_retail 0.0\n'
    'plant_health 1100\nclover_general_fp01 40.0\n'
    'clover_unused_extra_fp01 25.0\n'
    'candypop_shared_base Pom\n'
    'native_ready false\ngameplay_events_executed false\nbtk_playback false\n'
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resource_id(species):
    """Disc resource directory for a flora identity (EnemyInfo resources)."""
    if species not in SPECIES:
        raise ValueError('Unknown flora species')
    return SHARED_BASE.get(species, species)


def reference_conversion(species, amount, own_colour=False):
    """Reference-only Pellet-to-Pom conversion math (never executed here).

    Pelplant returns a pellet's Pikmin yield (its size 1/5/10/20); a Candypop
    returns the sprout count for Pikmin swallowed during its open window: one
    sprout per Pikmin, or the Queen ip13 multiplier, with an own-colour slot
    refund for the non-queen buds (Pom.cpp:280-322, PomState.cpp:177-190).
    """
    if species not in SPECIES:
        raise ValueError('Unknown flora species')
    if type(amount) is not int or amount < 0:
        raise ValueError('Invalid conversion amount')
    if species == 'Pelplant':
        if amount not in (1, 5, 10, 20):
            raise ValueError('Invalid pellet size')
        return {'species': species, 'input': amount, 'output': amount,
                'multiplier': 1, 'refund': False, 'reference_only': True}
    if species not in POM_SPECIES:
        raise ValueError('Not a Candypop bud')
    queen = species == 'RandPom'
    slots = DISC_PARMS[species]['proper']['ip11' if queen else 'ip01']
    multiplier = DISC_PARMS[species]['proper']['ip13'] if queen else 1
    if amount > slots:
        raise ValueError('Conversion exceeds lifetime slot budget')
    return {'species': species, 'input': amount, 'output': amount * multiplier,
            'multiplier': multiplier, 'refund': bool(own_colour) and not queen,
            'reference_only': True}


def flora_animation_rows(text):
    """Parse enemyanimmgr.txt for flora, keeping the capitalised large-variant stems.

    The shared sheargrub ``animation_rows`` restricts file stems to lowercase,
    but the disc registers Ooinu_l and Wakame_l as ``ooinu_L.bca`` and
    ``wakame_L.bca`` (while anim.szs stores lowercase members). This parser
    keeps the same token/event grammar with a case-insensitive file pattern;
    callers casefold the stem to resolve the archive member.
    """
    clean = re.sub(r'#[^\r\n]*', '', text)
    count = int(clean.split()[0])
    rows = []
    for block in re.findall(r'\{([^{}]*)\}', clean):
        fields = block.split()
        if len(fields) < 3 or not ANIM_FILE.fullmatch(fields[1]) or fields[-1] != '-1':
            raise ValueError('Invalid animation registration')
        events = fields[2:-1]
        if len(events) % 2:
            raise ValueError('Invalid animation event pairs')
        rows.append({'file': fields[1],
                     'events': [[int(events[i]), int(events[i + 1])]
                                for i in range(0, len(events), 2)]})
    if len(rows) != count or len({r['file'].casefold() for r in rows}) != count:
        raise ValueError('Animation registry count/identity mismatch')
    return rows


def profile(species, blocks_list, rows, metadata_absent=None):
    """Validate parsed metadata for one flora identity against the contract.

    ``blocks_list`` is parameter_blocks(enemyparm.txt). Enemy flora produce
    creature, general, proper (3 blocks); prop flora allocate a plain
    EnemyParmsBase and produce creature, general (2 blocks), except Clover which
    also ships a third, unreferenced block. ``rows`` is
    flora_animation_rows(enemyanimmgr.txt) in registration order. Duplicate keys
    are rejected by the parsers upstream; header defaults and disc values are
    reported separately, never flattened. ``metadata_absent`` records metadata
    members that do not exist for this species on disc.
    """
    if species not in SPECIES:
        raise ValueError('Unknown flora species')
    classification = CLASSIFICATION[species]
    entry = DISC_PARMS[species]
    extra = None
    if classification == 'enemy_flora':
        if len(blocks_list) != 3:
            raise ValueError(f'Expected 3 parameter blocks for {species}')
        general, proper = blocks_list[1], blocks_list[2]
    else:
        expected_length = 3 if 'extra' in entry else 2
        if len(blocks_list) != expected_length:
            raise ValueError(f'Expected {expected_length} parameter blocks for {species}')
        general, proper = blocks_list[1], {}
        if 'extra' in entry:
            extra = blocks_list[2]
            expected_extra = entry['extra']
            if set(extra) != set(expected_extra) or any(
                    not math.isclose(extra[key], float(value), rel_tol=0,
                                     abs_tol=1e-6)
                    for key, value in expected_extra.items()):
                raise ValueError(f'Unexpected {species} trailing disc block: {extra}')
    expected_proper = PROPER_PARM_DEFAULTS[species]
    allowed_proper = set(expected_proper) | set(PROPER_RETAIL_ONLY.get(species, ()))
    unknown_proper = set(proper) - allowed_proper
    if unknown_proper:
        raise ValueError(
            f'Unexpected {species} proper parameter keys: {sorted(unknown_proper)}')
    unknown_general = set(general) - GENERAL_KEYS
    if unknown_general:
        raise ValueError(
            f'Unexpected {species} general parameter keys: {sorted(unknown_general)}')
    for group in ('general', 'proper'):
        source = general if group == 'general' else proper
        for key, value in entry.get(group, {}).items():
            if key not in source or not math.isclose(source[key], float(value),
                                                     rel_tol=0, abs_tol=1e-6):
                raise ValueError(f'{species} disc {group} parameter {key} mismatch')
    defaulted = set(expected_proper) - set(proper)
    clips = tuple(Path(r['file']).stem.lower() for r in rows)
    if clips != CLIPS[species]:
        raise ValueError(f'Unexpected {species} clip registry: {clips}')
    for row in rows:
        name = Path(row['file']).stem.lower()
        if row['events'] != EXPECTED_EVENTS[species][name]:
            raise ValueError(f'{species} clip {name} key events mismatch')
    return {'enemy_id': SPECIES[species],
            'common_name': COMMON_NAME[species],
            'classification': classification,
            'resource': resource_id(species),
            'shared_base': SHARED_BASE.get(species),
            'state_ids': dict(STATE_IDS[species]),
            'anim_id_by_clip': {name: i for i, name in enumerate(CLIPS[species])},
            'parameter_blocks': blocks_list,
            'proper_header_defaults': dict(PROPER_PARM_DEFAULTS[species]),
            'proper_retail': {k: proper[k] for k in proper},
            'proper_retail_only': sorted(set(proper) - set(expected_proper)),
            'proper_keys_defaulted_from_header': sorted(defaulted),
            'unused_disc_blocks': [dict(extra)] if extra is not None else [],
            'metadata_absent': list(metadata_absent) if metadata_absent else [],
            }


def extract(iso, source, output, pose_limit=6):
    if type(pose_limit) is not int or not 2 <= pose_limit <= MAX_POSES:
        raise ValueError(f'Pose limit must be 2..{MAX_POSES}')
    if output.exists():
        raise ValueError('Output already exists')
    head = subprocess.check_output(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('Invalid source revision')
    index = disc_files(iso)
    source_hashes = {}
    started = time.perf_counter()
    with iso.open('rb') as disc:
        header = disc.read(8)
        if header[:6] != b'GPVE01':
            raise ValueError('Expected supplied US GPVE01 disc')

        def read(name):
            at, size = index[name]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated ISO resource')
            source_hashes[name] = sha(raw)
            return raw

        params = archive_files(read(PARM_SOURCE))
        output.mkdir(parents=True)
        report = dict(schema=1, policy='P2_FLORA_1',
                      disc_id=header[:6].decode(), disc_revision=header[7],
                      source_revision=head, source_sha256=source_hashes,
                      native_ready=False, gameplay_events_executed=False,
                      btk_playback=False, conversion_reference_only=REFERENCE_ONLY,
                      species={}, total_pose_bytes=0, total_poses=0)
        for species in SPECIES:
            resource = resource_id(species)
            root = output / species
            root.mkdir()
            model = archive_files(
                read(f'enemy/data/{resource}/model.szs'))['enemy.bmd']
            model_blocks = blocks(model)
            motions = archive_files(
                read(f'enemy/data/{resource}/anim.szs'))
            motion_members = {name.casefold(): name for name in motions}
            names = joints(model)
            (root / 'enemy.bmd').write_bytes(model)
            metadata = {}
            metadata_absent = []
            for filename in METADATA_FILES:
                key = resource.lower() + '/' + filename
                if key not in params:
                    metadata_absent.append(filename)
                    continue
                raw = params[key]
                metadata[filename] = sha(raw)
                (root / filename).write_bytes(raw)
            missing = [name for name in REQUIRED_METADATA
                       if name in metadata_absent]
            if missing:
                raise ValueError(f'Missing required {species} metadata: {missing}')
            envelopes = struct.unpack_from('>H', model_blocks['EVP1'], 8)[0]
            draws = struct.unpack_from('>H', model_blocks['DRW1'], 8)[0]
            blocks_list = parameter_blocks(
                params[resource.lower() + '/enemyparm.txt'])
            rows = flora_animation_rows(
                params[resource.lower() + '/enemyanimmgr.txt'].decode('shift_jis'))
            info = profile(species, blocks_list, rows, metadata_absent)
            info.update(role='shared-base colour bud' if species in POM_SPECIES
                        else 'concrete spawnable',
                        model_sha256=sha(model), joints=names,
                        metadata_sha256=metadata,
                        skinning=dict(envelopes=envelopes, draw_matrices=draws,
                                      weighted_baking=envelopes > 0,
                                      self_contained_resources=draws > 0),
                        collision=collision_nodes(
                            params[resource.lower() + '/enemycoll.txt'],
                            len(names)),
                        clips=[])
            reference = None
            for row in rows:
                member = motion_members.get(row['file'].casefold())
                if member is None:
                    raise ValueError(f'Missing {species} motion {row["file"]}')
                raw = motions[member]
                (root / member).write_bytes(raw)
                clip = dict(name=Path(member).stem,
                            source_sha256=sha(raw),
                            events=row['events'],
                            loop_attribute=raw[40],
                            loop_semantics=LOOPS.get(raw[40]),
                            event_loop_boundaries=[r for r in row['events']
                                                   if r[1] in (0, 1)],
                            pose_conversion_policy=dict(
                                POSE_TOLERANCES.get(species, {})),
                            decode_conversion_policy=dict(
                                TOLERANCES.get(species, {})),
                            poses=[], status='unsupported')
                try:
                    if raw[40] not in LOOPS:
                        raise ValueError('Unsupported source loop attribute')
                    pose_tolerances = POSE_TOLERANCES.get(species, {})
                    duration, _ = bca_pose(raw, 0, len(names), allow_scale=True,
                                           **pose_tolerances)
                    clip['source_frames'] = duration
                    frames = sample_frames(duration, pose_limit)
                    for number, frame in enumerate(frames):
                        try:
                            tolerances = TOLERANCES.get(species, {})
                            _, pose = bca_pose(raw, frame, len(names),
                                               allow_scale=True,
                                               **pose_tolerances)
                            matrices = draw_matrices(model_blocks, pose)
                            decoded = decode(model, True, bake_rigid=True,
                                             draw_matrices=matrices,
                                             **tolerances)
                            name = (f'flora_{species}_{clip["name"]}'
                                    f'_{number:02}.mod')
                            conversion = write_model(decoded, root / name,
                                                     'enemy.bmd')
                            conversion.update(source='enemy.bmd', output=name,
                                              weighted_pose_baked=envelopes > 0)
                            data = (root / name).read_bytes()
                            resources = resource_chunks(data)
                            if reference is not None and resources != reference:
                                raise ValueError(
                                    'Flora pose changes immutable render resources')
                            reference = resources
                            report['total_pose_bytes'] += len(data)
                            report['total_poses'] += 1
                            clip['poses'].append(
                                dict(file=name, frame=frame, bytes=len(data),
                                     sha256=sha(data)))
                            (root / Path(name).with_suffix('.json')).write_bytes(
                                (json.dumps(conversion, sort_keys=True, indent=2)
                                 + '\n').encode())
                        except (ValueError, KeyError, ArithmeticError) as error:
                            clip['poses'].append(
                                dict(frame=frame,
                                     unsupported_reason=f'{type(error).__name__}: {error}'))
                except (ValueError, KeyError, ArithmeticError) as error:
                    # Clip-level bca/loop failure; recorded, never fabricated.
                    clip['unsupported_reason'] = f'{type(error).__name__}: {error}'
                converted = [p for p in clip['poses'] if 'file' in p]
                if converted:
                    clip['status'] = 'converted'
                else:
                    clip['unsupported_reason'] = clip.get('unsupported_reason') or (
                        clip['poses'][0]['unsupported_reason']
                        if clip['poses'] else 'no sampled frames')
                info['clips'].append(clip)
            report['species'][species] = info
        report['limitations'] = list(LIMITATIONS)
        manifest = {k: v for k, v in report.items()
                    if k != 'extract_seconds'}
        (output / 'flora.json').write_bytes(
            (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
        report['extract_seconds'] = round(time.perf_counter() - started, 3)
        (output / 'p2-flora.txt').write_text(TEXT)
        return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pose-limit', type=int, default=6)
    a = p.parse_args()
    r = extract(a.iso, a.source, a.output, a.pose_limit)
    print(json.dumps({
        'bytes': r['total_pose_bytes'], 'poses': r['total_poses'],
        'seconds': r['extract_seconds'],
        'species': {s: {
            'clips': len(v['clips']),
            'converted': sum(c['status'] == 'converted' for c in v['clips']),
            'poses': sum(1 for c in v['clips']
                         for p in c['poses'] if 'file' in p),
            'unsupported_poses': sum(1 for c in v['clips']
                                     for p in c['poses'] if 'file' not in p),
            'skinning': v['skinning'],
        } for s, v in r['species'].items()}
    }, indent=2))
