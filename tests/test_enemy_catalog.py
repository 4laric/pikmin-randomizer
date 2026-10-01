"""Actual seeded source inventory, not host models or a potential species pool."""
import copy
import json
import unittest
from pathlib import Path

from experimental.pikmin2_enemy_roster import load_and_validate
from randomizer import enemy_catalog as catalog
from randomizer.catalog import BESTIARY_TARGETS, MODERN_LOCATION_IDS
from randomizer.seed import generate, validate, fingerprint

ROOT = Path(__file__).resolve().parents[1]


class EnemyCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.placement = json.loads((ROOT / "docs/PIKMIN2_ADMITTED_PLACEMENT.json").read_text())
        cls.roster = load_and_validate()

    def build(self, **kwargs):
        manifest = generate("enemy-catalog-1046", collection_checks=True, p2_enemies=True,
                            p2_species="playable", **kwargs)
        manifest["enemy_catalog"] = catalog.resolve(manifest, self.placement, self.roster)
        catalog.validate(manifest["enemy_catalog"], manifest)
        return manifest

    def test_real_catalog_contains_both_games_and_keeps_part_goal(self):
        manifest = self.build()
        self.assertEqual({r["game"] for r in manifest["enemy_catalog"]["checks"]}, {"p1", "p2"})
        names = catalog.active_names(manifest)
        self.assertIn("Pikmin: Secret Safe", names)
        self.assertIn("Bestiary: Deliver Pearly Clamclamp Pearl", names)
        self.assertNotIn("Bestiary: Deliver Puffstool", names)
        self.assertEqual(manifest["locations"]["Pikmin: Secret Safe"], MODERN_LOCATION_IDS["Pikmin: Secret Safe"])

    def test_sampled_out_does_not_create_check_but_holder_counts_as_placed(self):
        manifest = self.build(p2_density="sampled-v1")
        placed = {r["source_id"] for r in manifest["p2_layout"]["bindings"]}
        checks = {r["species"] for r in manifest["enemy_catalog"]["checks"] if r["game"] == "p2"}
        self.assertEqual(checks, placed - catalog.NO_CHECK_SPECIES)
        # A holder can seat an ordinary-sample unplaced identity (#901).
        self.assertFalse((set(manifest["p2_layout"].get("unplaced", [])) - placed) & checks)

    def test_aliases_replace_and_arena_mates_do_not_survive(self):
        manifest = self.build()
        sources = {r["uid"]: r for r in manifest["enemy_catalog"]["sources"]}
        arenas = {a["id"]: a for a in self.placement["arenas"]}
        for row in manifest["p2_layout"]["boss_arenas"]["placed"]:
            arena = arenas[row["arena"]]
            for uid in arena["spawn_uids"]:
                self.assertEqual((sources[uid]["game"], sources[uid]["species"]), ("p2", row["source_id"]))
                self.assertEqual(sources[uid]["first_day"], arena["first_day"])
            self.assertFalse(set(arena["suppress_uids"]) & sources.keys())

    def test_p2_source_and_p1_host_have_distinct_ids(self):
        manifest = self.build()
        rows = manifest["enemy_catalog"]["checks"]
        self.assertTrue(any(r["game"] == "p1" and r["species"] == 3 for r in rows))
        for row in rows:
            if row["game"] == "p2":
                self.assertNotIn(row["id"], MODERN_LOCATION_IDS.values())
                self.assertTrue(row["name"].startswith("Bestiary: Deliver P2 "))

    def test_binding_order_does_not_change_catalog_or_ids(self):
        manifest = self.build()
        other = copy.deepcopy(manifest)
        other["p2_layout"]["bindings"].reverse()
        self.assertEqual(manifest["enemy_catalog"], catalog.resolve(other, self.placement, self.roster))
        ids = {r["species"]: r["id"] for r in manifest["enemy_catalog"]["checks"] if r["game"] == "p2"}
        other = generate("different", collection_checks=True, p2_enemies=True, p2_species="playable")
        other_catalog = catalog.resolve(other, self.placement, self.roster)
        for row in other_catalog["checks"]:
            if row["game"] == "p2" and row["species"] in ids:
                self.assertEqual(row["id"], ids[row["species"]])

    def test_foreign_or_missing_source_rejected(self):
        manifest = self.build()
        for change in (lambda r: r.update(sources=[]), lambda r: r["sources"].append(1),
                       lambda r: r.update(id=True), lambda r: r.update(native_index=0)):
            other = copy.deepcopy(manifest["enemy_catalog"])
            change(other["checks"][0])
            with self.assertRaises(ValueError):
                catalog.validate(other, manifest)

    def test_omitted_check_rejected_for_either_game(self):
        manifest = self.build()
        for game in ("p1", "p2"):
            other = copy.deepcopy(manifest["enemy_catalog"])
            victim = next(row for row in other["checks"] if row["game"] == game)
            other["checks"].remove(victim)
            with self.assertRaises(ValueError):
                catalog.validate(other, manifest)

    def test_proxy_never_creates_source_behavior_check(self):
        manifest = self.build()
        species = manifest["p2_layout"]["bindings"][0]["source_id"]
        result = catalog.resolve(manifest, self.placement, self.roster, proxy_ids=[species])
        catalog.validate(result, manifest)
        self.assertTrue(any(s["game"] == "proxy" and s["species"] == species for s in result["sources"]))
        self.assertFalse(any(r["game"] == "p2" and r["species"] == species for r in result["checks"]))

    def test_surviving_p1_check_uses_only_unreplaced_sources(self):
        manifest = self.build()
        replacement_uids = {int(r["target"]) for r in manifest["p2_layout"]["bindings"]}
        for row in manifest["enemy_catalog"]["checks"]:
            if row["game"] == "p1":
                self.assertFalse(set(row["sources"]) & replacement_uids)
                self.assertEqual(row["id"], MODERN_LOCATION_IDS[row["name"]])
                self.assertEqual(BESTIARY_TARGETS[row["name"]][0], row["species"])

    def test_product_generation_roundtrip_pool_and_tracker(self):
        from randomizer.tracker import TrackerModel
        from randomizer.catalog import active_names, item_pool
        for density in (None, 'bounded-coverage-v1', 'sampled-v1'):
            manifest = generate('product-catalog', mode='ap', p2_enemies=True,
                                p2_checks=True, p2_species='playable', p2_density=density)
            validate(manifest)
            restored = json.loads(json.dumps(manifest))
            self.assertEqual(fingerprint(manifest), fingerprint(restored))
            self.assertEqual(set(active_names(manifest)), set(manifest['locations']))
            self.assertEqual(len(item_pool(manifest)), len(manifest['locations']))
            model = TrackerModel(restored)
            snapshot = model.snapshot(dict(fingerprint=fingerprint(restored), checked=[], received=[]))
            p2_rows = [r for r in snapshot['rows'] if r['name'].startswith('Bestiary: Deliver P2 ')]
            self.assertTrue(p2_rows)
            self.assertTrue(all(r['source'] and r['areas'] for r in p2_rows))

    def test_production_catalog_tamper_rejected(self):
        manifest = generate('strict-catalog', p2_enemies=True, p2_checks=True, p2_species='playable')
        for field, value in (('stage', 4), ('first_day', 30), ('species', 0)):
            other = copy.deepcopy(manifest)
            source = next(r for r in other['enemy_catalog']['sources'] if r['game'] == 'p2' and r[field] != value)
            source[field] = value
            with self.assertRaises(ValueError):
                validate(other)

    def test_new_catalog_is_opt_in_for_existing_seed_api(self):
        legacy = generate('legacy-p2', p2_enemies=True, p2_species='playable')
        self.assertNotIn('enemy_catalog', legacy)
        self.assertNotIn(catalog.CAPABILITY, legacy['capabilities'])
        with self.assertRaises(ValueError):
            generate('invalid', p2_checks=True)

    def test_heavy_corpse_needs_capacity_and_campaign_colors(self):
        from randomizer.catalog import can_reach_manifest, ITEM_IDS, FLARLIC, BLUE
        manifest = generate('heavy-corpse', p2_enemies=True, p2_checks=True,
                            p2_species='playable', starting_flarlic=1)
        heavy = next(r for r in manifest['enemy_catalog']['checks'] if r['game']=='p2' and r['carry_min']==30)
        inventory = {name: 1 for name in ITEM_IDS}
        inventory[FLARLIC] = 0
        self.assertFalse(can_reach_manifest(heavy['name'], inventory, manifest))
        inventory[FLARLIC] = 2
        self.assertTrue(can_reach_manifest(heavy['name'], inventory, manifest))
        inventory[BLUE] = 0
        self.assertFalse(can_reach_manifest(heavy['name'], inventory, manifest))


if __name__ == "__main__":
    unittest.main()
