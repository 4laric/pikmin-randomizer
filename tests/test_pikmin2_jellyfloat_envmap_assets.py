import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experimental.pikmin2_jellyfloat_envmap_assets import FAMILIES, build, checked_inputs
from experimental.pikmin2_kurage_material_patch import SOURCES


def digest(data):
    return hashlib.sha256(data).hexdigest()


class AssetPipelineTests(unittest.TestCase):
    def fixture(self, root):
        assets = root/'assets'; converted = root/'converted'
        asset_families = {}; converted_families = {}
        for species, model_hash in ((name, next(key for key, value in SOURCES.items() if value == name)) for name in FAMILIES):
            # Hash checking is separately covered below; patch it here to keep this fixture tiny.
            (assets/species).mkdir(parents=True); (assets/species/'enemy.bmd').write_bytes(species.encode())
            (converted/species).mkdir(parents=True); (converted/species/'wait.mod').write_bytes((species+' mod').encode())
            asset_families[species] = {'enemy_id': 57 if species == 'Kurage' else 72,
                                       'files': {'enemy.bmd': model_hash}}
            converted_families[species] = {'clips': [{'source': 'wait.bca', 'output': 'wait.mod', 'frames': 1}]}
        (assets/'manifest.json').write_text(json.dumps({'families': asset_families}))
        (converted/'manifest.json').write_text(json.dumps({'source': str(assets), 'families': converted_families}))
        return assets, converted

    def test_rejects_model_not_matching_extracted_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            assets, converted = self.fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, 'Unaudited'):
                checked_inputs(assets, converted)

    def test_build_records_every_original_clip_and_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); assets, converted = self.fixture(root)
            import experimental.pikmin2_jellyfloat_envmap_assets as pipeline
            actual = pipeline.sha_file
            original = actual
            model_hashes = iter(key for key in SOURCES)
            expected = {species: next(model_hashes) for species in FAMILIES}
            def fake_hash(path):
                path = Path(path)
                if path.name == 'enemy.bmd': return expected[path.parent.name]
                return actual(path)
            pipeline.sha_file = fake_hash
            def fake_exporter(model, mod, destination):
                destination.mkdir(parents=True)
                (destination/'patched.mod').write_bytes(Path(mod).read_bytes()+b' patched')
                (destination/'patch.json').write_text('{}')
                return {'source_sha256': fake_hash(model), 'before': actual(mod)}
            try:
                manifest = build(assets, converted, root/'result', fake_exporter)
            finally:
                pipeline.sha_file = original
            self.assertEqual(len(manifest['models']), 2)
            self.assertFalse(manifest['runtime_artifact'])
            self.assertFalse(manifest['full_material_fidelity'])
            for row in manifest['models']:
                self.assertEqual(row['source_mod'], 'wait.mod')
                self.assertTrue((root/'result'/row['patched_mod']).is_file())
