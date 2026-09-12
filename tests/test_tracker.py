import copy
import unittest
from collections import Counter
from randomizer.seed import generate, fingerprint
from randomizer.catalog import ITEM_IDS, BLUE, REPAIR
from randomizer.tracker import TrackerModel, TrackerWindow


class TrackerTests(unittest.TestCase):
    def data(self, manifest):
        return dict(fingerprint=fingerprint(manifest), checked=[], received=[])

    def test_solo_checks_and_hidden_stats(self):
        m = generate('tracker', collection_checks=True, randomize_color_stats=True)
        model = TrackerModel(m); data = self.data(m)
        snap = model.snapshot(data)
        self.assertEqual(len(snap['rows']), len(m['locations']))
        self.assertEqual(sum('undiscovered' in line for line in snap['profiles']), 2)
        name = next(iter(m['locations'])); data['checked'] = [name]
        updated = model.snapshot(data)
        self.assertEqual(updated['inventory'], Counter({model.rewards[name]: 1}))
        self.assertEqual(next(r['status'] for r in updated['rows'] if r['name'] == name), 'Checked')
        self.assertTrue(all(set(r) == {'name', 'status', 'areas', 'source'} for r in updated['rows']))

    def test_ap_only_received_items_grant_unlocks(self):
        m = generate('tracker', 'ap', collection_checks=True, randomize_color_stats=True)
        model = TrackerModel(m); data = self.data(m)
        data['checked'] = [next(iter(m['locations']))]
        self.assertFalse(model.snapshot(data)['inventory'])
        data['received'] = [ITEM_IDS[BLUE], ITEM_IDS[REPAIR], ITEM_IDS[REPAIR]]
        snap = model.snapshot(data)
        self.assertEqual(snap['inventory'][REPAIR], 2)
        self.assertIn('Blue: unlocked', snap['onions'])
        self.assertEqual(sum('undiscovered' in line for line in snap['profiles']), 1)

    def test_filters_and_seeded_sources(self):
        m = generate('tracker', campaign_enemies=True)
        model = TrackerModel(m); rows = model.snapshot(self.data(m))['rows']
        for area in model.areas.values():
            self.assertTrue(all(area in r['areas'] for r in model.filter_rows(rows, area=area)))
        selected = model.filter_rows(rows, query='population', status='All checks')
        self.assertEqual(len(selected), 12)
        self.assertTrue(all(r['status'] == 'Available' for r in model.filter_rows(rows, status='Available')))
        self.assertEqual(len(model.filter_rows(rows, status='All checks')), len(rows))

    def test_legacy_and_wrong_identity(self):
        m = generate('legacy'); model = TrackerModel(m)
        data = self.data(m); model.snapshot(data)
        data['fingerprint'] = 'wrong'
        with self.assertRaises(ValueError): model.snapshot(data)

    def test_widgets_refresh_and_filter(self):
        import tkinter as tk
        root = tk.Tk(); root.withdraw()
        try:
            m = generate('widgets', campaign_enemies=True, progressive_color_stats=True)
            window = TrackerWindow(root, m, lambda: None)
            window.update(self.data(m)); root.update_idletasks()
            self.assertEqual(len(window.checks.get_children()), 113)
            window.query.set('population'); root.update_idletasks()
            self.assertEqual(len(window.checks.get_children()), 12)
            window.status.set('Checked')
            self.assertFalse(window.checks.get_children())
            window.hide()
        finally:
            root.destroy()
