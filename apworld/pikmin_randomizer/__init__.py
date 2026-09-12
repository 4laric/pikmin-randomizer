"""Independent AP world; M0 retains identity physical placements."""
import json
from dataclasses import dataclass
from pathlib import Path
from BaseClasses import Item, ItemClassification, Location, Region
from Options import PerGameCommonOptions, Toggle, Choice, Range, OptionSet, DeathLink
from worlds.AutoWorld import World
from .core.catalog import (GAME, ITEM_IDS, LOCATION_IDS, NAMES, CHECK_AREAS,
                           CHECK_REQUIREMENTS, UNLOCKS, REPAIR, REPAIR_COUNT, ALL_LOCATION_IDS,
                           active_names, item_pool, check_area, can_reach_manifest, FLARLIC, ALL_AREA_LOCATION_IDS, START_AREAS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS)
from .core.seed import generate, fingerprint
from .core.stats import UPGRADE_ITEMS
from .core.benefits import ALL_BENEFIT_ITEMS as BENEFIT_ITEMS, TRAP, TRAP_ITEMS


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


class DeathLinkPikmin(Range):
    """DeathLink unit. Every N ordinary Pikmin deaths (remainder kept across days) sends one link; each received link kills up to N living field Pikmin through their normal death, never Olimar or Onion stock. Links received while the game is closed are dropped."""
    display_name = 'DeathLink Pikmin'
    range_start = 1
    range_end = 100
    default = 10


@dataclass
class PikminOptions(PerGameCommonOptions):
    goal: GoalMode
    death_link: DeathLink
    death_link_pikmin: DeathLinkPikmin
    bomb_rock_weight: BombRockWeight
    bomb_trap_weight: BombTrapWeight
    progg_trap_weight: ProggTrapWeight
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


class PikminItem(Item):
    game = GAME


class PikminLocation(Location):
    game = GAME


class PikminRandomizerWorld(World):
    game = GAME
    options_dataclass = PikminOptions
    item_name_to_id = ITEM_IDS
    location_name_to_id = {**ALL_AREA_LOCATION_IDS, **MODERN_LOCATION_IDS}
    required_client_version = (0, 6, 0)
    # Universal Tracker: the manifest depends on the room seed, so a local
    # regeneration must reuse the authoritative manifest from slot_data.
    ut_can_gen_without_yaml = True

    @staticmethod
    def interpret_slot_data(slot_data):
        return slot_data

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        for _, area, _ in START_AREAS.values():
            region = Region(area, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            menu.connect(region)
            for name in active_names(self.manifest()):
                if check_area(name) == area:
                    region.locations.append(PikminLocation(self.player, name, self.manifest()['locations'][name], region))

    def create_item(self, name):
        classification = ItemClassification.trap if name in TRAP_ITEMS else ItemClassification.useful if name in BENEFIT_ITEMS or (name in UPGRADE_ITEMS and UPGRADE_ITEMS[name][1] != 'carry') else ItemClassification.progression
        return PikminItem(name, classification, ITEM_IDS[name], self.player)

    def create_items(self):
        # Sparse cap-10 starts need farming access before reverse fill spends
        # their opening population check. This can be delivered from another world.
        if self.manifest().get('starting_flarlic') == 1:
            early = FLARLIC if self.manifest()['profile'] == 'foh-day2' else 'Pikmin: Forest of Hope Access'
            self.multiworld.early_items[self.player][early] = max(
                1, self.multiworld.early_items[self.player].get(early, 0))
        repairs = 0
        for name in item_pool(self.manifest()):
            item = self.create_item(name)
            if name == REPAIR:
                repairs += 1
                if repairs > REPAIR_COUNT:
                    item.classification = ItemClassification.useful
            self.multiworld.itempool.append(item)

    def set_rules(self):
        expanded = bool(self.options.expanded_checks)
        for name in active_names(self.manifest()):
            self.get_location(name).access_rule = lambda state, name=name: can_reach_manifest(
                name, {item: state.count(item, self.player) for item in ITEM_IDS}, self.manifest())
        self.multiworld.completion_condition[self.player] = lambda state: state.has(REPAIR, self.player, REPAIR_COUNT) and (
            self.manifest().get('goal_mode') != 'emperor_bulblax' or can_reach_manifest('Pikmin: Secret Safe',
                {item: state.count(item, self.player) for item in ITEM_IDS}, self.manifest()))

    def manifest(self):
        if not hasattr(self, '_manifest'):
            passthrough = getattr(self.multiworld, 're_gen_passthrough', {}).get(GAME)
            if passthrough:
                manifest = passthrough['manifest']
                if fingerprint(manifest) != passthrough.get('manifest_fingerprint'):
                    raise ValueError('Universal Tracker slot_data manifest does not match its fingerprint')
                self._manifest = manifest
                return manifest
            self._manifest = generate(str(self.multiworld.seed_name), "ap", self.multiworld.player_name[self.player],
                            combined_captain=bool(self.options.collection_checks or self.options.permanent_checks or self.options.progressive_color_stats or self.options.per_spawn_enemies or self.options.group_spawn_enemies or self.options.miniboss_enemies or self.options.campaign_enemies or self.options.bomb_rock_weight.value or self.options.bomb_trap_weight.value or self.options.progg_trap_weight.value or self.options.goal.value), goal_mode=("repairs", "emperor_bulblax")[self.options.goal.value],
                            expanded=bool(self.options.expanded_checks), bomb_rock_weight=self.options.bomb_rock_weight.value, bomb_trap_weight=self.options.bomb_trap_weight.value,
                            death_link=bool(self.options.death_link), death_link_pikmin=self.options.death_link_pikmin.value, progg_trap_weight=self.options.progg_trap_weight.value,
                            starting_area=('forest', 'navel', 'random', 'impact', 'spring', 'trial')[self.options.starting_area.value],
                            starting_color=('red', 'yellow', 'blue', 'random')[self.options.starting_color.value], all_areas=bool(self.options.all_areas), enemy_shuffle=bool(self.options.enemy_shuffle), collection_checks=bool(self.options.collection_checks), starting_flarlic=self.options.starting_flarlic.value, randomize_color_stats=bool(self.options.randomize_color_stats), progressive_color_stats=bool(self.options.progressive_color_stats), permanent_checks=bool(self.options.permanent_checks), per_spawn_enemies=bool(self.options.per_spawn_enemies), group_spawn_enemies=bool(self.options.group_spawn_enemies), miniboss_enemies=bool(self.options.miniboss_enemies), campaign_enemies=bool(self.options.campaign_enemies),
                            random_start_areas=self.options.random_start_areas.value,
                            initial_stat_bounds={stat: [getattr(self.options, 'initial_' + stat + '_min').value, getattr(self.options, 'initial_' + stat + '_max').value] for stat in ('damage', 'movement', 'attack_rate')},
                            stat_upgrade_counts={stat: getattr(self.options, stat + '_upgrades').value for stat in ('damage', 'movement', 'attack_rate', 'carry')})
        return self._manifest

    def fill_slot_data(self):
        manifest = self.manifest()
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_output(self, output_directory):
        if getattr(self.multiworld, 'generation_is_fake', False): return
        path = Path(output_directory) / (self.multiworld.get_out_file_name_base(self.player) + ".pikmin.json")
        path.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
