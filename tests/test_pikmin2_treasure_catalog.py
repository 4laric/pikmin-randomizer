import copy
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from experimental.pikmin2_treasure_catalog import manifest, verify_native_catalog
from scripts.play_p2_economy import launch_command


def source():
    return dict(schema=1, disc='GPVE01 revision 0', reconciliation=dict(reconciled=True),
                entries=[dict(treasure_id=f'item_{i}', pellet_kind='otakara',
                              classification='campaign', unique='yes', config_index=i,
                              dictionary=i+1, value=180, weight=15, slots=25, code=0)
                         for i in range(201)])


class CatalogTests(unittest.TestCase):
    def test_deterministic_full_manifest(self):
        ledger = source()
        data = manifest(ledger)
        self.assertEqual(data, manifest(copy.deepcopy(ledger)))
        self.assertEqual(len(data.splitlines()), 202)
        self.assertTrue(data.startswith(b'P2_TREASURE_CATALOG_1 201\n'))

    def test_distinguishes_modes_and_preserves_strength_over_slots(self):
        ledger = source()
        ledger['entries'][0].update(classification='mode_only', weight=1000, slots=100)
        ledger['entries'][1].update(classification='unused', unique='no')
        self.assertIn(b'item_0 otakara mode_only 0 1 180 1000 100 0 yes', manifest(ledger))

    def test_source_and_count_refusal(self):
        for field, value in (('schema', 2), ('disc', 'PAL'), ('reconciliation', dict(reconciled=False)),
                             ('entries', source()['entries'][:-1])):
            with self.subTest(field=field):
                ledger = source(); ledger[field] = value
                with self.assertRaises(ValueError): manifest(ledger)

    def test_identity_refusal(self):
        for field, value in (('treasure_id', '../escape'), ('pellet_kind', 'carcass'),
                             ('classification', 'unknown'), ('unique', 'maybe'),
                             ('treasure_id', 'item_1'), ('dictionary', 2), ('config_index', 1)):
            with self.subTest(field=field, value=value):
                ledger = source(); ledger['entries'][0][field] = value
                with self.assertRaises(ValueError): manifest(ledger)

    def test_numeric_refusal(self):
        for field, value in (('dictionary', 0), ('dictionary', 202), ('value', -1),
                             ('value', 1000001), ('value', True), ('weight', 0),
                             ('weight', 1001), ('slots', 129), ('slots', 0),
                             ('config_index', 256), ('code', 65536)):
            with self.subTest(field=field, value=value):
                ledger = source(); ledger['entries'][0][field] = value
                with self.assertRaises(ValueError): manifest(ledger)

    def test_modified_and_oversized_catalog_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'catalog.txt'
            for data in (b'P2_TREASURE_CATALOG_1 201\n', b'x'*32769):
                path.write_bytes(data)
                with self.assertRaises(ValueError): verify_native_catalog(path)

    def test_launcher_reuses_normal_runner_and_isolates_catalog_env(self):
        with patch('scripts.play_p2_economy.verify_native_catalog', return_value=Path('private/catalog.txt')):
            command, env = launch_command('private/catalog.txt', ['manifest.json','--session-dir','private/session'])
        self.assertEqual(command[1:], ['-m','randomizer','run','manifest.json','--session-dir','private/session'])
        self.assertEqual(Path(env['PIKMIN_P2_TREASURE_CATALOG']), Path('private/catalog.txt'))
        self.assertEqual(env['PIKMIN_P2_ROOM_WINDOW'], '960x540')


if __name__ == '__main__': unittest.main()
