"""Independent AP world; M0 retains identity physical placements."""
import json
from dataclasses import dataclass
from pathlib import Path
from BaseClasses import Item, ItemClassification, Location, Region
from Options import PerGameCommonOptions, Toggle
from worlds.AutoWorld import World
from .core.catalog import (GAME, ITEM_IDS, LOCATION_IDS, NAMES, CHECK_AREAS,
                           CHECK_REQUIREMENTS, UNLOCKS, REPAIR, REPAIR_COUNT, ALL_LOCATION_IDS,
                           active_names, item_pool, check_area, can_reach, FLARLIC)
from .core.seed import generate, fingerprint


class ExpandedChecks(Toggle):
    """Enable Flarlic capacity, field population, first-defeat bestiary and exploration checks."""
    display_name = "Expanded Checks"
    default = 0


@dataclass
class PikminOptions(PerGameCommonOptions):
    expanded_checks: ExpandedChecks


class PikminItem(Item):
    game = GAME


class PikminLocation(Location):
    game = GAME


class PikminRandomizerWorld(World):
    game = GAME
    options_dataclass = PikminOptions
    item_name_to_id = ITEM_IDS
    location_name_to_id = ALL_LOCATION_IDS
    required_client_version = (0, 6, 0)

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        for area in dict.fromkeys(CHECK_AREAS.values()):
            region = Region(area, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            menu.connect(region)
            for name in active_names(self.manifest()):
                if check_area(name) == area:
                    region.locations.append(PikminLocation(self.player, name, ALL_LOCATION_IDS[name], region))

    def create_item(self, name):
        return PikminItem(name, ItemClassification.progression, ITEM_IDS[name], self.player)

    def create_items(self):
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
            self.get_location(name).access_rule = lambda state, name=name: can_reach(
                name, {item: state.count(item, self.player) for item in ITEM_IDS}, expanded)
        self.multiworld.completion_condition[self.player] = lambda state: state.has(REPAIR, self.player, REPAIR_COUNT)

    def manifest(self):
        return generate(str(self.multiworld.seed_name), "ap", self.multiworld.player_name[self.player],
                        expanded=bool(self.options.expanded_checks))

    def fill_slot_data(self):
        manifest = self.manifest()
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_output(self, output_directory):
        path = Path(output_directory) / (self.multiworld.get_out_file_name_base(self.player) + ".pikmin.json")
        path.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
