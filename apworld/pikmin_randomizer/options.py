"""Player-facing options for the Pikmin Randomizer world."""
from dataclasses import dataclass
from Options import PerGameCommonOptions, Toggle, Choice, Range, OptionSet, DeathLink, OptionDict


class ExpandedChecks(Toggle):
    """Legacy expanded check catalog. Modern collection checks already enable capacity and all five areas."""
    display_name = "Expanded Checks"
    default = 0


class StartingArea(Choice):
    """Randomized includes Impact, Forest of Hope, Forest Navel and Distant Spring; excludes Final Trial. New starts enable the expanded five-area catalog."""
    display_name = 'Starting Area'
    option_forest = 0
    option_navel = 1
    option_randomized = 2
    option_impact = 3
    option_spring = 4
    option_trial = 5
    default = 0


class StartingColor(Choice):
    """Starting Onion and 20 Pikmin. Non-default enables expanded checks."""
    display_name = 'Starting Color'
    option_red = 0
    option_yellow = 1
    option_blue = 2
    option_randomized = 3
    default = 0


class CollectionChecks(Toggle):
    """Bestiary corpse deliveries (Puffy Blowhog defeat and Clamclamp pearl), plus total population 10/25/50/100 per color. Enables all five areas; no scout or landing checks."""
    display_name = 'Corpse Delivery and Total Population Checks'
    default = 1


class CampaignEnemies(Toggle):
    """Campaign-wide compatible ground, frog, flying, small-enemy and aquatic pools, with a Teki miniboss in Hope, Navel and Spring. Impact's scheduled Mamuta is included. Final Trial bosses/hazards and scripted drops remain pinned. Overrides older enemy toggles."""
    display_name = 'Campaign Enemy Randomizer'
    default = 0


class P2EnemyRandomizer(Toggle):
    """Experimental: place admitted Pikmin 2 source enemies in the randomizer through the versioned admission bridge. Off by default. When enabled, the admitted cohort is placed on the committed accepted-placement document (docs/PIKMIN2_ADMITTED_PLACEMENT.json); an empty or unaccepted admission set still fails closed with a clear error, and no P1 enemy is ever substituted."""
    display_name = 'Pikmin 2 Enemy Bridge (experimental)'
    default = 0


class P2EnemyPool(Choice):
    """Which admitted Pikmin 2 enemies the bridge may place. playable: only species the
    launcher can stage and run today (Blue Kochappy, Mamuta, the four elemental Otakara);
    slots only other species could fill stay vanilla. all: every admitted species."""
    display_name = 'Pikmin 2 enemy pool'
    option_playable = 0
    option_all = 1
    default = 0


class P2Placement(OptionDict):
    """Experimental lane-04 p2-placement-v1 document. Required when enabling
    P2 enemies. Supply reviewed placement evidence; empty or denied placements
    fail generation. This option never grants enemy admission."""
    display_name = 'Pikmin 2 placement document'
    default = {}


class GroupSpawnEnemies(Toggle):
    """Experimental: one seeded species per fixed-count dwarf/Sheargrub generator. Preserves counts and schedules; implies per-spawn adult mode. Physical route acceptance pending."""
    display_name = 'Grouped Family Enemies'
    default = 0


class MinibossEnemies(Toggle):
    """Experimental adult replacements: one Puffstool, Mamuta and Cannon Beetle. Implies per-spawn enemies."""
    display_name = "Experimental Miniboss Enemies"
    default = 0

class PerSpawnEnemies(Toggle):
    """Opt-in individual adult Bulborb/Bulbear assignments at 15 named points. Overrides global enemy_shuffle. Other species remain vanilla; enables modern collection checks. Requires matching generator assets."""
    display_name = 'Per-Spawn Adult Enemies'
    default = 0


class RandomizeColorStats(Toggle):
    """Seeded damage, movement and attack rate at 25/50/75/100% per color. Carrying strength starts at 1. Throw height and color abilities stay vanilla. Enables all-area checks."""
    display_name = "Randomize Color Stats"
    default = 0


class PermanentChecks(Toggle):
    """Add 43 individual walls, bridges and boxes. Enables collection checks; 105 total checks. Climbing sticks are excluded because they reset daily. Obstacle routes currently require all colors conservatively; boxes also require field capacity 100."""
    display_name = 'Permanent Structure and Granular Population Checks'
    default = 0


class ProgressiveColorStats(Toggle):
    """Receive per-color stat upgrades as AP items. Vanilla or rolled bases; configurable counts default to four damage/carry and two movement/attack-rate upgrades per color (36 items). Enables permanent checks to fit the larger pool. Stacks additively with rolled stats."""
    display_name = "Progressive Color Stats"
    default = 0


class StartingFlarlic(Range):
    """Initial field capacity in tens. Remaining Flarlic items raise the cap to 100. Enables expanded checks."""
    display_name = "Starting Flarlic"
    range_start = 1
    range_end = 10
    default = 1


class RandomStartAreas(OptionSet):
    """Eligible areas when starting_area is randomized. Must be nonempty. Final Trial is never eligible."""
    display_name = 'Random Starting Areas'
    valid_keys = frozenset({'impact', 'forest', 'navel', 'spring'})
    default = valid_keys


class InitialStatMinimum(Choice):
    """Minimum initial percentage when randomize_color_stats is on. Use 25, 50, 75 or 100; must not exceed maximum. Rolls use 25-point steps."""
    display_name = 'Initial Stat Minimum'
    option_25 = 25
    option_50 = 50
    option_75 = 75
    option_100 = 100
    default = 25


class InitialStatMaximum(InitialStatMinimum):
    """Maximum initial percentage when randomize_color_stats is on. Use 25, 50, 75 or 100; must not be below minimum."""
    display_name = 'Initial Stat Maximum'
    default = 100


class DamageUpgrades(Range):
    """Copies per color when progressive_color_stats is on. Each adds 25 percentage points of base damage."""
    display_name = 'Damage Upgrades Per Color'
    range_start = 0
    range_end = 4
    default = 4


class CarryUpgrades(DamageUpgrades):
    """Copies per color when progressive_color_stats is on. Each adds 1 carrying strength; initial strength stays 1."""
    display_name = 'Carry Upgrades Per Color'


class MovementUpgrades(Range):
    """Copies per color when progressive_color_stats is on. Each adds 25 percentage points of movement speed."""
    display_name = 'Movement Upgrades Per Color'
    range_start = 0
    range_end = 2
    default = 2


class AttackRateUpgrades(MovementUpgrades):
    """Copies per color when progressive_color_stats is on. Each adds 25 percentage points of attack rate."""
    display_name = 'Attack Rate Upgrades Per Color'


class GoalMode(Choice):
    """Repairs completes at 25 repairs. Emperor Bulblax unlocks his fight at 25 repairs and requires defeating him; Final Trial Access is still required."""
    display_name = "Goal"
    option_repairs = 0
    option_emperor_bulblax = 1
    default = 1


class BombRockWeight(Range):
    """Filler weight for deliveries of three loose bomb rocks at a landing Onion. Pikmin Delivery / Flower Shower weights are 2 / 1. Zero disables. Queued until a safe gameplay landing; not required by logic."""
    display_name = 'Bomb Rock Delivery Weight'
    range_start = 0
    range_end = 10
    default = 1


class BombTrapWeight(Range):
    """Filler weight for five lit bomb rocks around Olimar. Zero disables. Waits for active gameplay; queued ambushes are spaced apart. Replaces filler, never progression."""
    display_name = "Bomb Ambush Weight"
    range_start = 0
    range_end = 10
    default = 0


class ProggTrapWeight(Range):
    """Filler weight for one Smoky Progg near Olimar. Zero disables. Waits for active gameplay and no living Progg in the area."""
    display_name = "Smoky Progg Ambush Weight"
    range_start = 0
    range_end = 10
    default = 0


class PrereleaseTrapWeight(Range):
    """Filler weight for Faithful to Prerelease: geysers and Candypop Buds become Beady Long Legs for 60 active seconds in the current area. Zero disables."""
    display_name = "Faithful to Prerelease Weight"
    range_start = 0
    range_end = 10
    default = 0


class DeathLinkPikmin(Range):
    """DeathLink unit. Every N ordinary Pikmin deaths (remainder kept across days) sends one link; each received link kills up to N living field Pikmin through their normal death, never Olimar or Onion stock. Links received while the game is closed are dropped."""
    display_name = 'DeathLink Pikmin'
    range_start = 1
    range_end = 100
    default = 10


@dataclass
class PikminOptions(PerGameCommonOptions):
    death_link: DeathLink
    death_link_pikmin: DeathLinkPikmin
    goal: GoalMode
    bomb_rock_weight: BombRockWeight
    bomb_trap_weight: BombTrapWeight
    progg_trap_weight: ProggTrapWeight
    prerelease_trap_weight: PrereleaseTrapWeight
    random_start_areas: RandomStartAreas
    initial_damage_min: InitialStatMinimum
    initial_damage_max: InitialStatMaximum
    initial_movement_min: InitialStatMinimum
    initial_movement_max: InitialStatMaximum
    initial_attack_rate_min: InitialStatMinimum
    initial_attack_rate_max: InitialStatMaximum
    damage_upgrades: DamageUpgrades
    movement_upgrades: MovementUpgrades
    attack_rate_upgrades: AttackRateUpgrades
    carry_upgrades: CarryUpgrades
    campaign_enemies: CampaignEnemies
    p2_enemy_randomizer: P2EnemyRandomizer
    p2_enemy_pool: P2EnemyPool
    p2_placement: P2Placement
    group_spawn_enemies: GroupSpawnEnemies
    miniboss_enemies: MinibossEnemies
    per_spawn_enemies: PerSpawnEnemies
    permanent_checks: PermanentChecks
    progressive_color_stats: ProgressiveColorStats
    randomize_color_stats: RandomizeColorStats
    starting_flarlic: StartingFlarlic
    expanded_checks: ExpandedChecks
    starting_area: StartingArea
    starting_color: StartingColor
    all_areas: Toggle
    enemy_shuffle: Toggle
    collection_checks: CollectionChecks
