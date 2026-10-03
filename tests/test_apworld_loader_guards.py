"""Negative controls for shipped-YAML qualification; actual fill runs separately."""
import copy
import unittest

from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate
from randomizer.enemy_catalog import validate as validate_catalog
from randomizer.seed import generate
from scripts.test_apworld_loader_manifest import assert_shipped_catalog


class ShippedCatalogGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admitted = set(admitted_ids(load_and_validate()))
        cls.manifest = generate(1153, slot="Player1", all_areas=True,
                                collection_checks=True, permanent_checks=True,
                                campaign_enemies=True, p2_enemies=True,
                                p2_density="sampled-v1")
        cls.locations = {row["name"]: row["id"] for row in cls.manifest["enemy_catalog"]["checks"]}

    def check(self, manifest, admitted=None, locations=None):
        assert_shipped_catalog(manifest, self.admitted if admitted is None else admitted,
                               validate_catalog, self.locations if locations is None else locations)

    def test_full_packaged_cohort(self):
        self.check(self.manifest)

    def test_narrowed_yaml_pool_rejected(self):
        narrowed = generate(1153, slot="Player1", all_areas=True,
                            collection_checks=True, permanent_checks=True,
                            campaign_enemies=True, p2_enemies=True,
                            p2_species=[min(self.admitted)], p2_density="sampled-v1")
        with self.assertRaisesRegex(AssertionError, "narrowed"):
            self.check(narrowed)

    def test_unplaced_counts_without_frozen_cohort_size(self):
        changed = copy.deepcopy(self.manifest)
        extra = max(self.admitted) + 1
        changed["p2_layout"].setdefault("unplaced", []).append(extra)
        self.check(changed, self.admitted | {extra})
        changed["p2_layout"]["unplaced"].remove(extra)
        changed["p2_layout"].setdefault("boss_arenas", {}).setdefault("unplaced", []).append(extra)
        self.check(changed, self.admitted | {extra})

    def test_wrong_density_rejected(self):
        changed = copy.deepcopy(self.manifest)
        changed["p2_layout"]["density"] = "legacy"
        with self.assertRaisesRegex(AssertionError, "density"):
            self.check(changed)

    def test_missing_surviving_p1_or_p2_check_rejected(self):
        for game in ("p1", "p2"):
            changed = copy.deepcopy(self.manifest)
            checks = changed["enemy_catalog"]["checks"]
            checks.remove(next(row for row in checks if row["game"] == game))
            with self.subTest(game=game), self.assertRaises(ValueError):
                self.check(changed)

    def test_actual_fill_missing_or_wrong_id_rejected(self):
        name = next(iter(self.locations))
        for locations in ({k: v for k, v in self.locations.items() if k != name},
                          dict(self.locations, **{name: -1})):
            with self.subTest(locations=locations), self.assertRaisesRegex(AssertionError, "actual AP fill"):
                self.check(self.manifest, locations=locations)


if __name__ == "__main__":
    unittest.main()
