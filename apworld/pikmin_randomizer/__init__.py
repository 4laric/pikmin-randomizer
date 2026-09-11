"""Independent AP world; M0 retains identity physical placements."""
import json
from dataclasses import dataclass
from pathlib import Path
from BaseClasses import Item, ItemClassification, Location, Region
from Options import PerGameCommonOptions, Toggle, Choice, Range
from worlds.AutoWorld import World
from .core.catalog import (GAME, ITEM_IDS, LOCATION_IDS, NAMES, CHECK_AREAS,
                           CHECK_REQUIREMENTS, UNLOCKS, REPAIR, REPAIR_COUNT, ALL_LOCATION_IDS,
                           active_names, item_pool, check_area, can_reach_manifest, FLARLIC, ALL_AREA_LOCATION_IDS, START_AREAS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS)
from .core.seed import generate, fingerprint
from .core.stats import UPGRADE_ITEMS
from .core.benefits import BENEFIT_ITEMS


class ExpandedChecks(Toggle):
    """Enable Flarlic capacity, field population, first-defeat bestiary and exploration checks."""
    display_name = "Expanded Checks"
    default = 0


class StartingArea(Choice):
    """Randomized includes all five areas. New starts enable the expanded five-area catalog."""
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
    """Count corpse deliveries at Onions and total living population up to 500 per color. Enables all-area expanded checks."""
    display_name = 'Corpse Delivery and Total Population Checks'
    default = 1


class RandomizeColorStats(Toggle):
    """Seeded damage (25-200%), movement/attack rate (50-150%), and carrying strength (1-5) per color. Throw height and color abilities stay vanilla. Enables all-area checks."""
    display_name = "Randomize Color Stats"
    default = 0


class PermanentChecks(Toggle):
    """Enable 57 color-specific total-population milestones and 51 individual walls, climbing sticks, bridges and boxes. Enables collection checks; 158 total checks. Obstacle routes currently require all colors conservatively; boxes also require field capacity 100."""
    display_name = 'Permanent Structure and Granular Population Checks'
    default = 0


class ProgressiveColorStats(Toggle):
    """Receive per-color stat upgrades as AP items. Vanilla or rolled bases; damage and carry have two upgrades, movement and attack rate one. Enables collection checks. Stacks additively with rolled stats."""
    display_name = "Progressive Color Stats"
    default = 0


class StartingFlarlic(Range):
    """Initial field capacity in tens. Remaining Flarlic items raise the cap to 100. Enables expanded checks."""
    display_name = "Starting Flarlic"
    range_start = 1
    range_end = 10
    default = 1


@dataclass
class PikminOptions(PerGameCommonOptions):
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
        classification = ItemClassification.useful if name in BENEFIT_ITEMS or (name in UPGRADE_ITEMS and UPGRADE_ITEMS[name][1] != 'carry') else ItemClassification.progression
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
        self.multiworld.completion_condition[self.player] = lambda state: state.has(REPAIR, self.player, REPAIR_COUNT)

    def manifest(self):
        if not hasattr(self, '_manifest'):
            self._manifest = generate(str(self.multiworld.seed_name), "ap", self.multiworld.player_name[self.player],
                            expanded=bool(self.options.expanded_checks),
                            starting_area=('forest', 'navel', 'random', 'impact', 'spring', 'trial')[self.options.starting_area.value],
                            starting_color=('red', 'yellow', 'blue', 'random')[self.options.starting_color.value], all_areas=bool(self.options.all_areas), enemy_shuffle=bool(self.options.enemy_shuffle), collection_checks=bool(self.options.collection_checks), starting_flarlic=self.options.starting_flarlic.value, randomize_color_stats=bool(self.options.randomize_color_stats), progressive_color_stats=bool(self.options.progressive_color_stats), permanent_checks=bool(self.options.permanent_checks))
        return self._manifest

    def fill_slot_data(self):
        manifest = self.manifest()
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_output(self, output_directory):
        path = Path(output_directory) / (self.multiworld.get_out_file_name_base(self.player) + ".pikmin.json")
        path.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
