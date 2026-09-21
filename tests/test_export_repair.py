import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from workflow import export_repair
from workflow.handoff import Rejected, digest


def operator_report():
    """The compact operator lives on the workflow line, not every lane base."""
    try:
        from workflow.operator import report
    except ImportError:
        return None
    return report


def receipt(evidence, sha256, **overrides):
    value = dict(root_commit='a' * 40, native_commit='b' * 40, native_dirty='',
                 export_evidence=evidence, export_sha256=sha256,
                 validation_path='output/validation.log', validation_sha256='c' * 64)
    value.update(overrides)
    return value


def lane(key, number, rec, **overrides):
    value = dict(lane=key, issue=number, state='done', generation=1, revision=1,
                 native={'head': 'b' * 40}, integration=rec)
    value.update(overrides)
    return value


def reg_for(root, state, at=1234.5):
    return SimpleNamespace(root=Path(root), snapshot=lambda: state, clock=lambda: at)


class ExportRepairTests(unittest.TestCase):
    def write(self, root, rel, text):
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_classification_distinguishes_the_operator_reasons(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            none_hash = self.write(root, 'output/none.json',
                                   json.dumps({'action': 'none-performed'}))
            clean_hash = self.write(root, 'output/clean.json', json.dumps({'action': 'exported'}))
            cases = {
                'missing': lane('missing', 1, receipt('output/absent.json', 'd' * 64)),
                'mismatch': lane('mismatch', 2, receipt('output/clean.json', 'e' * 64)),
                'none': lane('none', 3, receipt('output/none.json', none_hash)),
                'clean': lane('clean', 4, receipt('output/clean.json', clean_hash)),
                'text-evidence': lane('text-evidence', 5, receipt('output/absent.json', 'd' * 64)),
            }
            results = {key: export_repair.classify(root, value) for key, value in cases.items()}
            self.assertIsNone(results['clean'])
            self.assertEqual(results['mismatch'], export_repair.HASH_MISMATCH)
            self.assertEqual(results['none'], export_repair.NONE_PERFORMED)
            self.assertEqual(results['missing'], export_repair.UNAVAILABLE)
            self.assertEqual(results['text-evidence'], export_repair.UNAVAILABLE)
            self.assertIsNone(export_repair.classify(root, lane('tooling', 6, receipt('output/clean.json',
                                                                                      clean_hash), native=None)))

    def test_classification_reason_strings_match_the_operator_contract(self):
        self.assertEqual(export_repair.HASH_MISMATCH, 'Recorded export evidence hash mismatch')
        self.assertEqual(export_repair.NONE_PERFORMED, 'Recorded export evidence says none-performed')
        self.assertEqual(export_repair.UNAVAILABLE, 'Recorded export evidence unavailable')

    def test_debt_rows_match_the_compact_operator_exactly(self):
        report = operator_report()
        if report is None:
            self.skipTest('compact operator not present on this lane base')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            none_hash = self.write(root, 'output/none.json', json.dumps({'action': 'none-performed'}))
            clean_hash = self.write(root, 'output/clean.json', 'real export')
            state = dict(
                lanes={
                    'old-a': lane('old-a', 10, receipt('output/none.json', none_hash)),
                    'old-b': lane('old-b', 11, receipt('output/clean.json', 'f' * 64)),
                    'old-c': lane('old-c', 12, receipt('output/gone.json', '0' * 64)),
                    'fine': lane('fine', 13, receipt('output/clean.json', clean_hash)),
                    'tooling': lane('tooling', 14, receipt('output/gone.json', '0' * 64), native=None),
                },
                throughput=dict(workstreams={}, batches={}), throughput_runtime={},
                admission_reconciliation={})
            operator_rows = report(state, 50, root)['export_repairs']
            own_rows = export_repair.debt_rows(root, state)
            self.assertEqual([(r['lane'], r['reason']) for r in own_rows],
                             [(r['lane'], r['reason']) for r in operator_rows])
            self.assertEqual([r['lane'] for r in own_rows], ['old-a', 'old-b', 'old-c'])
            self.assertEqual(own_rows[1]['observed_sha256'], clean_hash)
            self.assertEqual(own_rows[1]['recorded_sha256'], 'f' * 64)

    def test_manifest_groups_receipts_hashes_and_owner_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            none_hash = self.write(root, 'output/none.json', json.dumps({'action': 'none-performed'}))
            state = dict(lanes={
                'old-a': lane('old-a', 10, receipt('output/none.json', none_hash)),
                'old-b': lane('old-b', 11, receipt('output/gone.json', '0' * 64)),
            })
            before = copy.deepcopy(state)
            data = export_repair.manifest(root, state, now=7.0)
            self.assertEqual(state, before)
            self.assertEqual(data['at'], 7.0)
            self.assertEqual(data['debt_count'], 2)
            self.assertEqual(data['breakdown'], {export_repair.NONE_PERFORMED: 1,
                                                 export_repair.UNAVAILABLE: 1})
            self.assertEqual(data['lanes'], ['old-a', 'old-b'])
            self.assertEqual(data['receipts']['old-a'], state['lanes']['old-a']['integration'])
            self.assertEqual(data['recorded_hashes']['old-a']['export_sha256'], none_hash)
            self.assertEqual(data['recorded_hashes']['old-b']['observed_sha256'], None)
            self.assertIn('debt_fingerprints', data)
            self.assertEqual(data['maintained_export']['command'],
                             'py -3.12 scripts/export_native_source.py')
            self.assertEqual([row['lane'] for row in data['reconciliation']], ['old-a', 'old-b'])
            self.assertIn('--lane old-a', data['reconciliation'][0]['inspect_command'])
            self.assertTrue(all(row['preserve_receipt'] for row in data['reconciliation']))

    def test_baseline_fails_closed_on_changed_receipt_or_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            none_hash = self.write(root, 'output/none.json', json.dumps({'action': 'none-performed'}))
            state = dict(lanes={'old-a': lane('old-a', 10, receipt('output/none.json', none_hash))})
            baseline = export_repair.manifest(root, state)
            self.assertEqual(export_repair.manifest(root, state, baseline=baseline)['debt_count'], 1)
            rewritten = copy.deepcopy(state)
            rewritten['lanes']['old-a']['integration']['export_sha256'] = '9' * 64
            with self.assertRaises(Rejected):
                export_repair.manifest(root, rewritten, baseline=baseline)
            Path(root, 'output/none.json').write_text('changed after baseline', encoding='utf-8')
            with self.assertRaises(Rejected):
                export_repair.manifest(root, state, baseline=baseline)

    def test_prepare_writes_hashed_manifest_and_fails_closed_on_race(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            none_hash = self.write(root, 'output/none.json', json.dumps({'action': 'none-performed'}))
            state = dict(lanes={'old-a': lane('old-a', 10, receipt('output/none.json', none_hash))})
            prepared = export_repair.prepare(reg_for(root, state), state=state)
            manifest_path = root / 'output/workflow/export-repair/repair-manifest.json'
            self.assertTrue(manifest_path.is_file())
            self.assertEqual(prepared['manifest_sha256'], digest(manifest_path))
            written = json.loads(manifest_path.read_text(encoding='utf-8'))
            self.assertEqual(written['debt_count'], 1)
            with self.assertRaises(Rejected):
                export_repair.prepare(reg_for(root, state), out_dir='docs/export-repair', state=state)
            changed = copy.deepcopy(state)
            changed['lanes']['old-a']['integration']['export_sha256'] = '9' * 64
            racing = reg_for(root, state)
            racing.snapshot = lambda: changed
            with self.assertRaises(Rejected):
                export_repair.prepare(racing, out_dir='output/workflow/race', state=state)
            self.assertFalse((root / 'output/workflow/race').exists())


if __name__ == '__main__':
    unittest.main()
