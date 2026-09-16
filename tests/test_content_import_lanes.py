"""Adversarial checks against copies of the complete checked-in content plan."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.check_content_import_lanes import InvalidPlan, ROOT, read_json, validate_plan


class ContentLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = read_json(ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
        path = ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json'
        cls.inventory = read_json(path)
        cls.sha = hashlib.sha256(path.read_bytes()).hexdigest()

    def altered(self):
        return copy.deepcopy(self.plan)

    def check(self, plan):
        return validate_plan(plan, self.inventory, self.sha)

    def test_complete_canonical_plan(self):
        result = self.check(self.plan)
        self.assertEqual(result['lanes'], 53)
        self.assertEqual(result['floors'], {'p2-cave': 105, 'p2-challenge': 59})
        self.assertEqual(result['categories']['p1-challenge'], 5)

    def test_missing_and_duplicate_source_fail(self):
        plan = self.altered()
        plan['lanes'].pop()
        with self.assertRaises(InvalidPlan): self.check(plan)
        plan = self.altered()
        plan['lanes'][-1] = copy.deepcopy(plan['lanes'][-2])
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_duplicate_lane_issue_and_path_claims(self):
        for field in ('lane', 'issue', 'owned_files'):
            with self.subTest(field=field):
                plan = self.altered()
                plan['lanes'][1][field] = copy.deepcopy(plan['lanes'][0][field])
                with self.assertRaises(InvalidPlan): self.check(plan)

    def test_casefold_and_directory_owned_path_conflicts(self):
        for path in (self.plan['lanes'][0]['owned_files'][0].upper(), 'experimental/content_lanes'):
            plan = self.altered()
            plan['lanes'][1]['owned_files'][0] = path
            with self.assertRaises(InvalidPlan): self.check(plan)

    def test_escaping_and_noncanonical_owned_paths(self):
        for path in ('../native/pc_port.cpp', 'C:/shared/file.py', '/tmp/file.py', 'experimental/./file.py', 'experimental\\file.py'):
            plan = self.altered()
            plan['lanes'][0]['owned_files'][0] = path
            with self.assertRaises(InvalidPlan): self.check(plan)

    def test_source_path_hash_and_inventory_pin_drift(self):
        plan = self.altered()
        plan['inventory_sha256'] = '0' * 64
        with self.assertRaises(InvalidPlan): self.check(plan)
        for field, value in (('source', 'user/Mukki/mapunits/caveinfo/fake.txt'), ('source_sha256', '0' * 64)):
            plan = self.altered()
            plan['lanes'][0][field] = value
            with self.assertRaises(InvalidPlan): self.check(plan)

    def test_exact_cave_floor_and_roster_details(self):
        for field in ('first', 'unit_pool', 'enemy_ids', 'treasure_ids'):
            plan = self.altered()
            value = plan['lanes'][0]['details']['floors'][0]
            value[field] = [] if field.endswith('_ids') else 2 if field == 'first' else 'different.txt'
            with self.assertRaises(InvalidPlan): self.check(plan)
        plan = self.altered()
        plan['lanes'][0]['details']['floor_count'] += 1
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_exact_challenge_timing_roster_sprays_and_indices(self):
        for field, value in (('floor_seconds', [999]), ('spicy_sprays', 999), ('ui_index', 99),
                             ('table_order', 99), ('pikmin_by_native_color_and_maturity', [[100]])):
            plan = self.altered()
            lane = next(x for x in plan['lanes'] if x['category'] == 'p2-challenge')
            lane['details'][field] = value
            with self.assertRaises(InvalidPlan): self.check(plan)

    def test_p1_known_keys_and_native_destination_identity(self):
        for field, value in (('level_key', 'campaign:impact'), ('native_area_id', 5), ('stage_info_index', 0)):
            plan = self.altered()
            lane = next(x for x in plan['lanes'] if x['category'] == 'p1-challenge')
            lane['details'][field] = value
            with self.assertRaises(InvalidPlan): self.check(plan)

    def test_missing_acceptance_dependencies_and_phases(self):
        for field in ('acceptance', 'preparation_dependencies', 'runtime_dependencies', 'phases'):
            plan = self.altered()
            plan['lanes'][0][field] = []
            with self.assertRaises(InvalidPlan): self.check(plan)
        plan = self.altered()
        plan['lanes'][0]['phases'][0]['acceptance'] = []
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_duplicate_acceptance_rejected(self):
        plan = self.altered()
        lane = plan['lanes'][0]
        lane['acceptance'].append(lane['acceptance'][0])
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_no_completion_claim_or_runtime_readiness(self):
        for field, value in (('state', 'done'), ('work_class', 'existing'), ('runtime_completed', True), ('issue', True)):
            plan = self.altered()
            plan['lanes'][0][field] = value
            with self.assertRaises(InvalidPlan): self.check(plan)
        plan = self.altered()
        plan['lanes'][0]['phases'][1]['ready'] = True
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_existing_issue_and_surface_course_preserved(self):
        plan = self.altered()
        plan['lanes'][0]['issue'] = 900001
        with self.assertRaises(InvalidPlan): self.check(plan)
        plan = self.altered()
        lane = next(x for x in plan['lanes'] if x['category'] == 'p2-overworld')
        lane['details']['course'] = 'test_map'
        with self.assertRaises(InvalidPlan): self.check(plan)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            for raw in ('{"schema":1,"schema":2}', '{"schema":NaN}'):
                path.write_text(raw)
                with self.assertRaises(InvalidPlan): read_json(path)

    def test_cli_default_and_malformed_file_exit_codes(self):
        command = [sys.executable, str(ROOT / 'scripts/check_content_import_lanes.py')]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('53 lanes', result.stdout)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text('{}')
            result = subprocess.run(command + ['--plan', str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith('FAIL:'))


if __name__ == '__main__':
    unittest.main()
