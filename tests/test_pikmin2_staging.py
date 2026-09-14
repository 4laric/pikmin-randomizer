"""P2 content staging: manifest validation, atomic staging, caching and receipts."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experimental.pikmin2_staging import (
    KINDS, SCHEMA, StagingError, load_manifest, stage, validate_manifest)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def scenario(root, count=3):
    source = root / 'source'
    source.mkdir(parents=True)
    entries = []
    blobs = {}
    for index in range(count):
        name = f'src{index}.bin'
        data = f'payload-{index}'.encode()
        (source / name).write_bytes(data)
        blobs[name] = data
        entries.append(dict(id=f'asset{index}', kind=KINDS[index % len(KINDS)],
                            source=name, destination=f'tree/{index}/{name}',
                            sha256=sha(data)))
    return dict(schema=SCHEMA, version=3, entries=entries), source, blobs


class StagingTests(unittest.TestCase):
    def test_happy_path_stages_files_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, blobs = scenario(tmp)
            run = tmp / 'run'
            receipt = stage(manifest, run, base=base)
            self.assertEqual(receipt['manifest_version'], 3)
            self.assertEqual(receipt['summary'],
                             dict(entries=3, cleaned_temp=0, staged=3, cached=0, repaired=0))
            for row in receipt['entries']:
                self.assertTrue(row['staged'])
                self.assertEqual(row['status'], 'staged')
                self.assertTrue((run / row['destination']).is_file())
            self.assertEqual(receipt['entries'][0]['source_sha256'], sha(blobs['src0.bin']))
            self.assertEqual(json.loads((tmp / 'run-staging-receipt.json').read_text()), receipt)

    def test_cached_replay_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, _ = scenario(tmp)
            run = tmp / 'run'
            first = stage(manifest, run, base=base)
            stamps = {row['destination']: (run / row['destination']).stat().st_mtime_ns
                      for row in first['entries']}
            second = stage(manifest, run, base=base)
            self.assertEqual(second['staged_digest'], first['staged_digest'])
            self.assertEqual(second['summary']['cached'], 3)
            self.assertEqual(second['summary']['staged'], 0)
            self.assertTrue(all(not row['staged'] for row in second['entries']))
            for destination, stamp in stamps.items():
                self.assertEqual((run / destination).stat().st_mtime_ns, stamp)

    def test_missing_source_fails_by_id_without_partial_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, _ = scenario(tmp)
            manifest['entries'][1]['source'] = 'absent.bin'
            run = tmp / 'run'
            with self.assertRaises(StagingError) as caught:
                stage(manifest, run, base=base)
            self.assertIn('asset1', str(caught.exception))
            self.assertFalse(run.exists())

    def test_wrong_source_hash_fails_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, _ = scenario(tmp)
            manifest['entries'][0]['sha256'] = '0' * 64
            with self.assertRaises(StagingError) as caught:
                stage(manifest, tmp / 'run', base=base)
            self.assertIn('asset0', str(caught.exception))
            self.assertIn('mismatch', str(caught.exception))

    def test_repairs_interrupted_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, blobs = scenario(tmp)
            run = tmp / 'run'
            first = stage(manifest, run, base=base)
            target = run / manifest['entries'][0]['destination']
            target.write_bytes(b'corrupt')
            stale = target.parent / 'leftover.mod.staging'
            stale.write_bytes(b'partial')
            repaired = stage(manifest, run, base=base)
            self.assertEqual(target.read_bytes(), blobs['src0.bin'])
            self.assertFalse(stale.exists())
            self.assertEqual(repaired['summary']['repaired'], 1)
            self.assertEqual(repaired['summary']['cleaned_temp'], 1)
            self.assertEqual(repaired['summary']['cached'], 2)
            self.assertEqual(repaired['staged_digest'], first['staged_digest'])

    def test_deterministic_digest_and_file_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            manifest, base, _ = scenario(tmp)
            first = stage(manifest, tmp / 'run_a', base=base)
            second = stage(manifest, tmp / 'run_b', base=base)
            self.assertEqual(first, second)
            path = base / 'manifest.json'
            path.write_text(json.dumps(manifest))
            from_file = stage(path, tmp / 'run_c')
            self.assertEqual(from_file['staged_digest'], first['staged_digest'])
            self.assertEqual(from_file['entries'], first['entries'])


class ManifestTests(unittest.TestCase):
    def test_rejects_malformed_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, _ = scenario(Path(tmp), 1)
            for mutate in (lambda m: m.update(schema=2),
                           lambda m: m.update(version=0),
                           lambda m: m.update(version='3'),
                           lambda m: m.update(entries={}),
                           lambda m: m['entries'][0].update(kind='mesh'),
                           lambda m: m['entries'][0].update(sha256='nope'),
                           lambda m: m['entries'][0].pop('id'),
                           lambda m: m['entries'][0].update(destination='/abs/x'),
                           lambda m: m['entries'][0].update(destination='../escape'),
                           lambda m: m['entries'][0].update(destination='a/../../b'),
                           lambda m: m['entries'][0].update(destination='C:/abs'),
                           lambda m: m['entries'][0].update(destination='tree/x.staging'),
                           lambda m: m.update(entries=[dict(kind='model', source='s',
                                                            destination='d', sha256=sha(b's'))]),
                           lambda m: m['entries'].append(copy.deepcopy(m['entries'][0]))):
                broken = copy.deepcopy(manifest)
                mutate(broken)
                with self.assertRaises(ValueError):
                    validate_manifest(broken)

    def test_rejects_duplicate_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, _ = scenario(Path(tmp), 2)
            manifest['entries'][1]['destination'] = manifest['entries'][0]['destination']
            with self.assertRaises(ValueError):
                validate_manifest(manifest)

    def test_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'broken.json'
            path.write_text('{')
            with self.assertRaises(ValueError):
                load_manifest(path)

    def test_normalizes_backslash_destinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, _, _ = scenario(Path(tmp), 1)
            manifest['entries'][0]['destination'] = 'tree\\nested\\file.bin'
            self.assertEqual(validate_manifest(manifest)['entries'][0]['destination'],
                             'tree/nested/file.bin')


if __name__ == '__main__':
    unittest.main()


def test_staging_rejects_junction_escape(tmp_path):
    import os
    import pytest
    manifest, source, _ = scenario(tmp_path, 1)
    run = tmp_path / 'run'
    run.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    if os.name == 'nt':
        import _winapi
        _winapi.CreateJunction(str(outside), str(run / 'tree'))
    else:
        (run / 'tree').symlink_to(outside, target_is_directory=True)
    with pytest.raises(StagingError, match='escapes'):
        stage(manifest, run, base=source)
    assert not list(outside.iterdir())
