"""Independent AP world; M0 retains identity physical placements."""
import json
from dataclasses import dataclass
from pathlib import Path
from BaseClasses import Item, ItemClassification, Location, Region
from Options import PerGameCommonOptions
from worlds.AutoWorld import World
from .core.catalog import (GAME, ITEM_IDS, LOCATION_IDS, NAMES, CHECK_AREAS,
                           CHECK_REQUIREMENTS, UNLOCKS, REPAIR, REPAIR_COUNT)
from .core.seed import generate, fingerprint


@dataclass
class PikminOptions(PerGameCommonOptions):
    pass


class PikminItem(Item):
    game = GAME


class PikminLocation(Location):
    game = GAME


class PikminRandomizerWorld(World):
    game = GAME
    options_dataclass = PikminOptions
    item_name_to_id = ITEM_IDS
    location_name_to_id = LOCATION_IDS
    required_client_version = (0, 6, 0)

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        for area in dict.fromkeys(CHECK_AREAS.values()):
            region = Region(area, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            menu.connect(region)
            for name in NAMES:
                if CHECK_AREAS[name] == area:
                    region.locations.append(PikminLocation(self.player, name, LOCATION_IDS[name], region))

    def create_item(self, name):
        return PikminItem(name, ItemClassification.progression, ITEM_IDS[name], self.player)

    def create_items(self):
        self.multiworld.itempool += [self.create_item(name) for name in UNLOCKS]
        self.multiworld.itempool += [self.create_item(REPAIR) for _ in range(REPAIR_COUNT)]

    def set_rules(self):
        for name, needs in CHECK_REQUIREMENTS.items():
            self.get_location(name).access_rule = lambda state, needs=needs: all(state.has(n, self.player) for n in needs)
        self.multiworld.completion_condition[self.player] = lambda state: state.has(REPAIR, self.player, REPAIR_COUNT)

    def manifest(self):
        return generate(str(self.multiworld.seed_name), "ap", self.multiworld.player_name[self.player])

    def fill_slot_data(self):
        manifest = self.manifest()
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_output(self, output_directory):
        path = Path(output_directory) / (self.multiworld.get_out_file_name_base(self.player) + ".pikmin.json")
        path.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
