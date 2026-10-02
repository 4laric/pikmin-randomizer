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
from .core.enemy_catalog import all_location_ids as p2_location_ids
from .core.stats import UPGRADE_ITEMS
from .core.benefits import ALL_BENEFIT_ITEMS as BENEFIT_ITEMS, TRAP, TRAP_ITEMS
from .core.compatibility import restore_slot_manifest


class PikminItem(Item):
    game = GAME


class PikminLocation(Location):
    game = GAME


class PikminRandomizerWorld(World):
    game = GAME
    options_dataclass = PikminOptions
    item_name_to_id = ITEM_IDS
    location_name_to_id = {**ALL_AREA_LOCATION_IDS, **MODERN_LOCATION_IDS, **p2_location_ids()}
    required_client_version = (0, 6, 0)
    ut_can_gen_without_yaml = True
    item_name_groups = {
        "Ship Repairs": {REPAIR},
        "Onions": {name for name in ITEM_IDS if name.endswith(" Onion")},
        "Area Access": {name for name in ITEM_IDS if name.endswith(" Access")},
        "Color Upgrades": set(UPGRADE_ITEMS),
        "Benefits": set(BENEFIT_ITEMS) - set(TRAP_ITEMS),
        "Traps": set(TRAP_ITEMS),
    }
    location_name_groups = {
        "Ship Parts": {name for name in location_name_to_id if name.startswith("Pikmin: ") and not name.endswith(" Discovery")},
        "Onion Discovery": {name for name in location_name_to_id if name.endswith(" Discovery")},
        "Population": {name for name in location_name_to_id if name.startswith("Population: ")},
        "Bestiary": {name for name in location_name_to_id if name.startswith("Bestiary: ")},
        "Exploration": {name for name in location_name_to_id if name.startswith("Explore: ")},
        "Structures": {name for name in location_name_to_id if name.startswith("Build: ")},
    }

    @staticmethod
    def interpret_slot_data(slot_data):
        manifest = restore_slot_manifest(slot_data)
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_early(self):
        passthrough = getattr(self.multiworld, "re_gen_passthrough", None) or {}
        if self.game in passthrough:
            self._manifest = restore_slot_manifest(passthrough[self.game])

    def create_regions(self):
        menu = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions.append(menu)
        resolved_checks = {r['name'] for r in self.seed_manifest().get('enemy_catalog', {}).get('checks', [])}
        if resolved_checks:
            bestiary = Region("Bestiary", self.player, self.multiworld)
            self.multiworld.regions.append(bestiary)
            menu.connect(bestiary)
            for name in active_names(self.seed_manifest()):
                if name in resolved_checks:
                    bestiary.locations.append(PikminLocation(self.player, name, self.seed_manifest()['locations'][name], bestiary))
        for _, area, _ in START_AREAS.values():
            region = Region(area, self.player, self.multiworld)
            self.multiworld.regions.append(region)
            menu.connect(region)
            for name in active_names(self.seed_manifest()):
                if name not in resolved_checks and check_area(name) == area:
                    region.locations.append(PikminLocation(self.player, name, self.seed_manifest()['locations'][name], region))

    def create_item(self, name):
        classification = ItemClassification.trap if name in TRAP_ITEMS else ItemClassification.useful if name in BENEFIT_ITEMS or (name in UPGRADE_ITEMS and UPGRADE_ITEMS[name][1] != 'carry') else ItemClassification.progression
        return PikminItem(name, classification, ITEM_IDS[name], self.player)

    def create_items(self):
        # Sparse cap-10 starts need farming access before reverse fill spends
        # their opening population check. This can be delivered from another world.
        if self.seed_manifest().get('starting_flarlic') == 1:
            early = FLARLIC if self.seed_manifest()['profile'] == 'foh-day2' else 'Pikmin: Forest of Hope Access'
            self.multiworld.early_items[self.player][early] = max(
                1, self.multiworld.early_items[self.player].get(early, 0))
        repairs = 0
        for name in item_pool(self.seed_manifest()):
            item = self.create_item(name)
            if name == REPAIR:
                repairs += 1
                if repairs > REPAIR_COUNT:
                    item.classification = ItemClassification.useful
            self.multiworld.itempool.append(item)

    def set_rules(self):
        expanded = bool(self.options.expanded_checks)
        for name in active_names(self.seed_manifest()):
            self.get_location(name).access_rule = lambda state, name=name: can_reach_manifest(
                name, {item: state.count(item, self.player) for item in ITEM_IDS}, self.seed_manifest())
        self.multiworld.completion_condition[self.player] = lambda state: state.has(REPAIR, self.player, REPAIR_COUNT) and (
            self.seed_manifest().get('goal_mode') != 'emperor_bulblax' or can_reach_manifest('Pikmin: Secret Safe',
                {item: state.count(item, self.player) for item in ITEM_IDS}, self.seed_manifest()))

    def seed_manifest(self):
        # AP owns World.manifest for archipelago.json metadata. Keep seed data separate.
        if not hasattr(self, '_manifest'):
            passthrough = getattr(self.multiworld, 're_gen_passthrough', {}).get(GAME)
            if passthrough:
                self._manifest = restore_slot_manifest(passthrough)
                return self._manifest
            selected_p2 = None
            if self.options.p2_enemy_randomizer and self.options.p2_species.value:
                try:
                    selected_p2 = sorted({int(value) for value in self.options.p2_species.value})
                except (TypeError, ValueError):
                    raise ValueError('p2_species must contain retail numeric source IDs') from None
            self._manifest = generate(str(self.multiworld.seed_name), "ap", self.multiworld.player_name[self.player],
                            combined_captain=bool(self.options.collection_checks or self.options.permanent_checks or self.options.progressive_color_stats or self.options.per_spawn_enemies or self.options.group_spawn_enemies or self.options.miniboss_enemies or self.options.campaign_enemies or self.options.bomb_rock_weight.value or self.options.bomb_trap_weight.value or self.options.progg_trap_weight.value or self.options.prerelease_trap_weight.value or self.options.goal.value), goal_mode=("repairs", "emperor_bulblax")[self.options.goal.value],
                            expanded=bool(self.options.expanded_checks), bomb_rock_weight=self.options.bomb_rock_weight.value, bomb_trap_weight=self.options.bomb_trap_weight.value, progg_trap_weight=self.options.progg_trap_weight.value, prerelease_trap_weight=self.options.prerelease_trap_weight.value,
                            death_link=bool(self.options.death_link), death_link_pikmin=self.options.death_link_pikmin.value,
                            progressive_maturity=True, progressive_day_length=self.options.progressive_day_length.value, day_length_step=self.options.day_length_increment.value // 5 * 5, whistle_pluck_item=bool(self.options.whistle_pluck_item),
                            starting_area=('forest', 'navel', 'random', 'impact', 'spring', 'trial')[self.options.starting_area.value],
                            starting_color=('red', 'yellow', 'blue', 'random')[self.options.starting_color.value], all_areas=bool(self.options.all_areas), enemy_shuffle=bool(self.options.enemy_shuffle), collection_checks=bool(self.options.collection_checks), starting_flarlic=self.options.starting_flarlic.value, randomize_color_stats=bool(self.options.randomize_color_stats), progressive_color_stats=bool(self.options.progressive_color_stats), permanent_checks=bool(self.options.permanent_checks),                             per_spawn_enemies=bool(self.options.per_spawn_enemies), group_spawn_enemies=bool(self.options.group_spawn_enemies), miniboss_enemies=bool(self.options.miniboss_enemies), campaign_enemies=bool(self.options.campaign_enemies), p2_enemies=bool(self.options.p2_enemy_randomizer), p2_checks=bool(self.options.p2_enemy_randomizer), p2_species=(selected_p2 if selected_p2 is not None else 'playable' if self.options.p2_enemy_randomizer and self.options.p2_enemy_pool.value == 0 else 'full' if self.options.p2_enemy_randomizer and self.options.p2_enemy_pool.value == 2 else None),
                            p2_second_captain=bool(self.options.p2_second_captain),
                            p2_proxy_tier=('proven' if self.options.p2_enemy_randomizer and self.options.p2_enemy_pool.value == 2 else None),
                            p2_density=((None, 'all-targets-v1', 'bounded-coverage-v1', 'sampled-v1')[self.options.p2_density.value] if self.options.p2_enemy_randomizer else None),
                            p2_placement=(self.options.p2_placement.value or None),
                            random_start_areas=self.options.random_start_areas.value,
                            initial_stat_bounds={stat: [getattr(self.options, 'initial_' + stat + '_min').value, getattr(self.options, 'initial_' + stat + '_max').value] for stat in ('damage', 'movement', 'attack_rate')},
                            stat_upgrade_counts={stat: getattr(self.options, stat + '_upgrades').value for stat in ('damage', 'movement', 'attack_rate', 'carry')})
        return self._manifest

    def fill_slot_data(self):
        manifest = self.seed_manifest()
        return {"manifest": manifest, "manifest_fingerprint": fingerprint(manifest)}

    def generate_output(self, output_directory):
        if getattr(self.multiworld, 'generation_is_fake', False): return
        path = Path(output_directory) / (self.multiworld.get_out_file_name_base(self.player) + ".pikmin.json")
        path.write_text(json.dumps(self.seed_manifest(), indent=2) + "\n", encoding="utf-8")
