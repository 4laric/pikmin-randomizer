"""Family facts for the P2 batch-2 install + arena lanes.

One entry per family drives :mod:`experimental.pikmin2_batch2_core`. The values
come from the batch-1 source contracts (commit ``a7c9ad7``) and the local US
GPVE01 revision 0 manifests under ``output/p2-lane-verify/``. P1 teki types are
from ``engine/include/teki.h``; a family with no P1 counterpart uses the neutral
Chappy (3, Dwarf Bulborb) placement vehicle and says so explicitly.
"""
from experimental.pikmin2_batch2_core import P1_CHAPPY_TYPE

P1_OTAMA_TYPE = 25    # teki.h:25, Wogpole
P1_BEATLE_TYPE = 17   # teki.h:17, Armored Cannon Beetle
P1_IWAGON_TYPE = 2    # teki.h:2, Rolling Boulder

_CHAPPY = 'Chappy (P1 Dwarf Bulborb)'
_CHAPPY_FAMILY = {P1_CHAPPY_TYPE: _CHAPPY}
_BEATLE_FAMILY = {P1_BEATLE_TYPE: 'Beatle (P1 Armored Cannon Beetle)',
                  P1_IWAGON_TYPE: 'Iwagon (P1 Rolling Boulder)',
                  P1_CHAPPY_TYPE: _CHAPPY}


def _row(species, control):
    """Evenly spaced engineered arena row plus a trailing ordinary control."""
    count = len(species)
    positions = tuple(((-(count - 1) / 2 + index) * 120.0, 30.0, 1850.0)
                      for index in range(count))
    return positions + ((240.0, 30.0, 1500.0),)


def _cfg(name, parent, manifest, policy, species, anchors, actors, ids, proxy,
         family, gates, blocked, limitations, source_yaw=None,
         scene='P1 Impact Site'):
    arena_species = tuple(actors) + ('P1 Chappy',)
    return dict(
        name=name, parent=parent, manifest=manifest, policy=policy, species=species,
        anchors=anchors, actors=tuple(actors),
        arena_ids=tuple(ids), arena_species=arena_species,
        arena_positions=_row(actors, 'P1 Chappy'),
        arena_proxy={**{s: proxy[s] for s in actors}, 'P1 Chappy': P1_CHAPPY_TYPE},
        arena_family=family, control='P1 Chappy', source_yaw=source_yaw, scene=scene,
        profile_header=f'P2_{name.upper()}_PROFILE_1'.replace('-', '_'),
        bank_header=f'P2_{name.upper()}_BANK_1'.replace('-', '_'),
        actors_header=f'P2_{name.upper()}_ACTORS_1'.replace('-', '_'),
        profile_txt=f'p2-{name}-profile.txt', bank_txt=f'p2-{name}-bank.txt',
        actors_txt=f'p2-{name}-actors.txt', install_json=f'{name}-install.json',
        gates=tuple(gates), blocked=dict(blocked), limitations=list(limitations))


MISSING = 'blocked: source behavior not registered; integration lead (#186)'
NO_PROXY = 'blocked: no P1 counterpart; Chappy placement vehicle only, identity NOT claimed'


DWEEVIL = _cfg(
    'dweevil', '#170', 'dweevils.json', 'P2_OTA_DWEEVIL_1',
    {'FireOtakara': 59, 'WaterOtakara': 60, 'GasOtakara': 61,
     'ElecOtakara': 62, 'BombOtakara': 93},
    {s: ('wait1', 'attack1', 'dead') for s in
     ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara', 'BombOtakara')},
    ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara', 'BombOtakara'),
    (349001, 349002, 349003, 349004, 349005, 349006),
    {s: P1_CHAPPY_TYPE for s in
     ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara', 'BombOtakara')},
    _CHAPPY_FAMILY,
    ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
     'combat', 'death_corpse', 'carrier_recovery', 'reload',
     'otakara_shared_base', 'change_texture_identity', 'elemental_discharge',
     'bomb_payload_lifecycle'),
    {'native_identity': MISSING,
     'natural_AI': 'blocked: shared OtakaraBase FSM not ported; placement vehicle only',
     'combat': 'blocked: fire/water/gas/electric receivers not registered',
     'death_corpse': 'blocked: corpse/carry behavior not registered',
     'otakara_shared_base': 'blocked: five dweevils share one OtakaraBase bank aliased to '
                            'FireOtakara; per-species change texture not staged',
     'change_texture_identity': 'blocked: procedural change texture is a runtime Mgr load, '
                                'not a sampled model pose',
     'elemental_discharge': 'blocked: fire/bubble/gas/electric discharge and treasure theft '
                            'not implemented',
     'bomb_payload_lifecycle': 'blocked: BombOtakara relies on the separate Bomb payload '
                               '(childID) whose birth/link/explosion lifetime is not ported'},
    ['Sampled poses with approximate materials; no skeletal playback or event execution.',
     'All five dweevils share one OtakaraBase model/anim bank aliased to FireOtakara; '
     'per-species identity is a procedural change texture only.',
     'BombOtakara payload lifecycle and all native FSM wiring are out of scope (#170).',
     'Tank (done) and Titan Dweevil / BigTreasure (#246) are separate and untouched.'])

FLORA = _cfg(
    'flora', '#171', 'flora.json', 'P2_FLORA_1',
    {'Pelplant': 0, 'BluePom': 3, 'RedPom': 4, 'YellowPom': 5, 'BlackPom': 6,
     'WhitePom': 7, 'RandPom': 8, 'Tanpopo': 46, 'Clover': 47, 'HikariKinoko': 48,
     'Ooinu_s': 49, 'Ooinu_l': 50, 'Wakame_s': 51, 'Wakame_l': 52},
    {'BluePom': ('wait', 'dead', 'type1'), 'RedPom': ('wait', 'dead', 'type1'),
     'YellowPom': ('wait', 'dead', 'type1'), 'BlackPom': ('wait', 'dead', 'type1'),
     'WhitePom': ('wait', 'dead', 'type1'), 'RandPom': ('wait', 'dead', 'type1'),
     'Tanpopo': ('tanpopo',), 'Clover': ('clover',), 'Ooinu_s': ('ooinu_s',),
     'Ooinu_l': ('ooinu_l',), 'Wakame_s': ('wakame_s',), 'Wakame_l': ('wakame_l',)},
    ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom', 'RandPom'),
    (353001, 353002, 353003, 353004, 353005, 353006, 353007),
    {s: P1_CHAPPY_TYPE for s in
     ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom', 'RandPom')},
    _CHAPPY_FAMILY,
    ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
     'combat', 'death_corpse', 'carrier_recovery', 'reload',
     'candypop_shared_pom_base', 'pellet_to_pom_conversion', 'pelplant_receptor',
     'sprout_birth', 'prop_flora_scenery'),
    {'native_identity': MISSING,
     'natural_AI': 'blocked: Candypop/Pelplant source behavior not ported; placement vehicle only',
     'combat': 'blocked: buds accept a Pikmin throw and convert it at runtime; not registered',
     'death_corpse': 'blocked: pellet drop/receptor behavior not registered',
     'candypop_shared_pom_base': 'blocked: six colour buds alias one shared Pom bank '
                                 '(enemyInfo.cpp); per-colour identity is not staged',
     'pellet_to_pom_conversion': 'blocked: pellet-to-Pom conversion math is a reference '
                                 'predicate only',
     'pelplant_receptor': 'blocked: Pelplant has no converted poses on this disc '
                          '(converter gap owned by #186)',
     'sprout_birth': 'blocked: sprout/seed production is engine-side, not an imported pose',
     'prop_flora_scenery': 'blocked: Tanpopo/Clover/Glowcap/Figwort/Shoot are scenery props, '
                           'not Piklopedia enemies'},
    ['Reference/import artifacts only; Pellet-to-Pom conversion is a reference predicate.',
     'Pelplant (0/10) and HikariKinoko (0/1) have no converted poses on this disc; recorded '
     'unsupported by the batch-1 lane and excluded from the visual actor set.',
     'All six Candypop buds alias one shared Pom bank; per-colour identity is not staged.'])

GROUND = _cfg(
    'ground', '#165', 'ground_inverts.json', 'P2_GROUND_INVERTS_1',
    {'Armor': 15, 'ElecBug': 28, 'Imomushi': 65, 'TamagoMushi': 68,
     'Sokkuri': 79, 'Hana': 84},
    {'Armor': ('dead', 'move', 'attack1'), 'ElecBug': ('dead', 'move', 'wait'),
     'Imomushi': ('dead', 'move1'), 'TamagoMushi': ('dead', 'move', 'wait'),
     'Sokkuri': ('run1', 'wait1', 'dead1'), 'Hana': ('dead', 'move1', 'attack1')},
    ('Armor', 'ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri', 'Hana'),
    (346001, 346002, 346003, 346004, 346005, 346006, 346007),
    {s: P1_CHAPPY_TYPE for s in
     ('Armor', 'ElecBug', 'Imomushi', 'TamagoMushi', 'Sokkuri', 'Hana')},
    _CHAPPY_FAMILY,
    ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
     'combat', 'death_corpse', 'carrier_recovery', 'reload',
     'armor_flint_reward', 'elecbug_charge', 'sokkuri_disguise', 'hana_ambush',
     'imomushi_plant_eat', 'tamagomushi_swarm'),
    {'native_identity': MISSING,
     'natural_AI': NO_PROXY,
     'combat': 'blocked: source attacks/receivers not registered',
     'death_corpse': 'blocked: corpse/carry behavior not registered',
     'armor_flint_reward': 'blocked: nectar/pellet spray reward on hit is not ported',
     'elecbug_charge': 'blocked: two-beetle charge/discharge link not ported',
     'sokkuri_disguise': 'blocked: terrain-disguise state changes are not ported',
     'hana_ambush': 'blocked: buried ambush/emerge behavior not ported',
     'imomushi_plant_eat': 'blocked: plant-eating state not ported',
     'tamagomushi_swarm': 'blocked: swarm birth from the ground manager not ported'},
    ['Sampled poses with approximate materials; no skeletal playback or event execution.',
     'Ground invertebrates have no audited P1 counterpart in this engine; the Chappy '
     'placement vehicle is used purely to stage the source visuals.',
     'Native registration, AI and receivers remain integration-lead work (#165/#186).'])

CANNON = _cfg(
    'cannon', '#169', 'cannon_projectile.json', 'P2_CANNON_PROJECTILE_1',
    {'Kabuto': 75, 'Rkabuto': 95, 'Fkabuto': 96, 'Rock': 19, 'Stone': 74,
     'Bomb': 36, 'Egg': 37, 'FminiHoudai': 97},
    {'Kabuto': ('wait', 'move', 'attack', 'dead'),
     'Rkabuto': ('wait', 'move', 'attack', 'dead'),
     'Fkabuto': ('wait', 'move', 'attack', 'dead'),
     'Rock': ('run', 'dead'), 'Stone': ('run', 'dead'),
     'Bomb': ('hit_start', 'hit_loop'), 'Egg': ('damage1',),
     'FminiHoudai': ('walk', 'dead1')},
    ('Kabuto', 'Rkabuto', 'Fkabuto', 'Rock', 'Bomb', 'Egg'),
    (350001, 350002, 350003, 350004, 350005, 350006, 350007),
    {'Kabuto': P1_BEATLE_TYPE, 'Rkabuto': P1_BEATLE_TYPE, 'Fkabuto': P1_BEATLE_TYPE,
     'Rock': P1_IWAGON_TYPE, 'Bomb': P1_CHAPPY_TYPE, 'Egg': P1_CHAPPY_TYPE},
    _BEATLE_FAMILY,
    ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
     'combat', 'death_corpse', 'carrier_recovery', 'reload',
     'cannon_projectile_pool', 'rock_roll', 'bomb_lifecycle', 'egg_drop',
     'buried_emerge', 'muzzle_alignment'),
    {'native_identity': MISSING,
     'natural_AI': 'blocked: source Cannon Beetle/Larvae FSM not ported; placement vehicle only',
     'combat': 'blocked: rock projectile and damage receivers not registered',
     'death_corpse': 'blocked: corpse/carry behavior not registered',
     'cannon_projectile_pool': 'blocked: multi-projectile pool and spawn points not ported',
     'rock_roll': 'blocked: rolling-boulder motion and collision not ported',
     'bomb_lifecycle': 'blocked: Bomb payload birth/link/explosion lifetime not ported',
     'egg_drop': 'blocked: egg drop/container behavior not ported',
     'buried_emerge': 'blocked: buried Kabuto emerge state not ported',
     'muzzle_alignment': 'blocked: dynamic muzzle transform not ported'},
    ['Sampled poses with approximate materials; no skeletal playback or event execution.',
     'Kabuto/Rkabuto/Fkabuto use the P1 Armored Cannon Beetle (Beatle 17) ancestor as a '
     'placement vehicle; Rock uses the P1 Rolling Boulder (Iwagon 2). Bomb and Egg have no '
     'audited ancestor and use the neutral Chappy vehicle.',
     'Projectile pool, muzzle alignment and buried-emerge behavior remain native work (#169/#186).'])

WATERWRAITH = _cfg(
    'waterwraith', '#175', 'waterwraith.json', 'P2_WATERWRAITH_1',
    {'Tyre': 98, 'BlackMan': 99},
    {'Tyre': ('tyre_move', 'tyre_getoff'),
     'BlackMan': ('kagebozu_wait', 'kagebozu_move', 'kagebozu_dead')},
    ('BlackMan', 'Tyre'), (352001, 352002, 352003),
    {'BlackMan': P1_CHAPPY_TYPE, 'Tyre': P1_CHAPPY_TYPE},
    _CHAPPY_FAMILY,
    ('native_identity', 'spawn_exact_xyz', 'control_undisturbed', 'natural_AI',
     'combat', 'death_corpse', 'carrier_recovery', 'reload',
     'boss_phases', 'tyre_roll_crush', 'purple_vulnerability', 'boss_corpse'),
    {'native_identity': MISSING,
     'natural_AI': NO_PROXY,
     'combat': 'blocked: Waterwraith damage/vulnerability receivers not registered',
     'death_corpse': 'blocked: boss corpse/reward behavior not registered',
     'boss_phases': 'blocked: Waterwraith is a dependent-actor boss; phases not ported',
     'tyre_roll_crush': 'blocked: Tyre child roller ownership/roll-crush not ported',
     'purple_vulnerability': 'blocked: Purple-Pikmin-only vulnerability is not ported',
     'boss_corpse': 'blocked: boss reward/corpse behavior not ported'},
    ['Sampled poses with approximate materials; no skeletal playback or event execution.',
     'BlackMan (Waterwraith) is a boss with a dependent Tyre child; staging both as '
     'independent vehicles is engineered placement, not production boss staging.',
     'Boss phases, vulnerability and reward behavior remain native work (#175/#186).'])

FAMILIES = {cfg['name']: cfg for cfg in
            (DWEEVIL, FLORA, GROUND, CANNON, WATERWRAITH)}
