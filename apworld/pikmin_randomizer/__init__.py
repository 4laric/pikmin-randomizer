"""Independent AP world; M0 retains identity physical placements."""
import json
from pathlib import Path
from BaseClasses import Item, ItemClassification, Location, Region
from worlds.AutoWorld import World
from .options import PikminOptions
from .core.catalog import (GAME, ITEM_IDS, LOCATION_IDS, NAMES, CHECK_AREAS,
                           CHECK_REQUIREMENTS, UNLOCKS, REPAIR, REPAIR_COUNT, ALL_LOCATION_IDS,
                           active_names, item_pool, check_area, can_reach_manifest, FLARLIC, ALL_AREA_LOCATION_IDS, START_AREAS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS)
from .core.seed import generate, fingerprint
from .core.stats import UPGRADE_ITEMS
from .core.benefits import ALL_BENEFIT_ITEMS as BENEFIT_ITEMS, TRAP, TRAP_ITEMS


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
                            combined_captain=bool(self.options.collection_checks or self.options.permanent_checks or self.options.progressive_color_stats or self.options.per_spawn_enemies or self.options.group_spawn_enemies or self.options.miniboss_enemies or self.options.campaign_enemies or self.options.bomb_rock_weight.value or self.options.bomb_trap_weight.value or self.options.progg_trap_weight.value or self.options.prerelease_trap_weight.value or self.options.goal.value), goal_mode=("repairs", "emperor_bulblax")[self.options.goal.value],
                            expanded=bool(self.options.expanded_checks), bomb_rock_weight=self.options.bomb_rock_weight.value, bomb_trap_weight=self.options.bomb_trap_weight.value, progg_trap_weight=self.options.progg_trap_weight.value, prerelease_trap_weight=self.options.prerelease_trap_weight.value,
                            death_link=bool(self.options.death_link), death_link_pikmin=self.options.death_link_pikmin.value,
                            starting_area=('forest', 'navel', 'random', 'impact', 'spring', 'trial')[self.options.starting_area.value],
                            starting_color=('red', 'yellow', 'blue', 'random')[self.options.starting_color.value], all_areas=bool(self.options.all_areas), enemy_shuffle=bool(self.options.enemy_shuffle), collection_checks=bool(self.options.collection_checks), starting_flarlic=self.options.starting_flarlic.value, randomize_color_stats=bool(self.options.randomize_color_stats), progressive_color_stats=bool(self.options.progressive_color_stats), permanent_checks=bool(self.options.permanent_checks), per_spawn_enemies=bool(self.options.per_spawn_enemies), group_spawn_enemies=bool(self.options.group_spawn_enemies), miniboss_enemies=bool(self.options.miniboss_enemies), campaign_enemies=bool(self.options.campaign_enemies), p2_enemies=bool(self.options.p2_enemy_randomizer), p2_species=('playable' if self.options.p2_enemy_randomizer and self.options.p2_enemy_pool.value == 0 else None),
                            p2_placement=(self.options.p2_placement.value or None),
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
