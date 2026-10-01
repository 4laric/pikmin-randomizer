"""Focused fail-closed tests for the Damagumo bind-mod conversion driver (#727)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental import pikmin2_damagumo_bind_mod_conversion as D

REVERIFY = Path('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
                'prerequisites/damagumo-converter-artifact-landing/out/reverify')
VISUAL_TREE = Path('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
                   'planning-shards/enemies-3/prepared/damagumo56-observer')


class ConversionDriverTests(unittest.TestCase):
    def test_pinned_hashes(self):
        self.assertEqual(D.FAMILY_JSON_SHA256,
                         'f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94')
        self.assertEqual(D.ENEMY_BMD_SHA256,
                         '8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961')
        self.assertEqual(D.SLOT_JSON_SHA256,
                         '61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c')
        self.assertEqual((D.SPECIES, D.ENEMY_ID, D.MOD),
                         ('Damagumo', 56, 'longlegs_Damagumo_bind_00.mod'))

    def test_reverify_hashes(self):
        D.check_json_hash(REVERIFY / 'damagumo-family.json',
                          D.FAMILY_JSON_SHA256, 'family json')
        D.check_hash(REVERIFY / 'Demon/enemy.bmd', D.ENEMY_BMD_SHA256, 'enemy.bmd')

    def test_wrong_species_slot_refused(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'slot.json'
            bad.write_text(json.dumps({'species': 'Houdai', 'source_id': 66,
                                       'mesh': 'Demon/enemy.bmd'}), encoding='utf-8')
            with self.assertRaises(D.ConversionError):
                D.convert_damagumo(REVERIFY / 'damagumo-family.json',
                                   REVERIFY / 'Demon/enemy.bmd', bad,
                                   VISUAL_TREE, Path(tmp) / 'out')

    def test_missing_file_refused(self):
        with self.assertRaises(D.ConversionError):
            D.sha256_file('/nonexistent/path/file.bin')

    def test_full_conversion(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'out'
            receipt = D.convert_damagumo(
                REVERIFY / 'damagumo-family.json', REVERIFY / 'Demon/enemy.bmd',
                REVERIFY / 'damagumo-slot-312004.json', VISUAL_TREE, out)
            self.assertEqual(receipt['species'], 'Damagumo')
            self.assertEqual(receipt['enemy_id'], 56)
            self.assertEqual(receipt['output'], 'longlegs_Damagumo_bind_00.mod')
            self.assertEqual(receipt['vertices'], 902)
            self.assertEqual(receipt['triangles'], 1696)
            target = out / 'longlegs_Damagumo_bind_00.mod'
            self.assertTrue(target.is_file())
            self.assertEqual(target.stat().st_size, 104640)
            self.assertEqual(receipt['sha256'],
                             'c5642cc97a292210b1556465125685963c8403134b438398c9739a9f64827dc2')

    def test_no_overwrite(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'out'
            out.mkdir()
            (out / 'longlegs_Damagumo_bind_00.mod').write_bytes(b'x')
            with self.assertRaises(D.ConversionError):
                D.convert_damagumo(
                    REVERIFY / 'damagumo-family.json', REVERIFY / 'Demon/enemy.bmd',
                    REVERIFY / 'damagumo-slot-312004.json', VISUAL_TREE, out)


if __name__ == '__main__':
    unittest.main()
