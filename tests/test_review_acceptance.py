import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from workflow.handoff import Rejected, digest
from workflow.review_acceptance import prepare, rows


OWNER = 'Codex through shared account 4laric'


def reg_for(root, state, at=1234.5):
    return SimpleNamespace(root=Path(root), snapshot=lambda: state, clock=lambda: at)


def review_lane(proof_path, proof_bytes, **overrides):
    lane = dict(lane='review-lane', owner=OWNER, task_id='opencode:ses_test', issue=134,
                generation=4, revision=9, state='review_ready', native=None,
                next_action='Decision A proved; no runtime claim',
                review=dict(schema=1, kind='review', fresh_runtime=False,
                    conclusion='Decision A proved', lane='review-lane', owner=OWNER,
                    task_id='opencode:ses_test', issue=134, generation=4,
                    evidence={'review': {'path': proof_path,
                                         'sha256': hashlib.sha256(proof_bytes).hexdigest()}}))
    lane.update(overrides)
    return lane


class ReviewAcceptanceTests(unittest.TestCase):
    def test_plan_is_ready_and_does_not_mutate_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / 'output' / 'proof.md'
            proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted')}}
            before = copy.deepcopy(state)
            planned = rows(reg_for(root, state))
            self.assertEqual(state, before)
        self.assertEqual(len(planned), 1)
        row = planned[0]
        self.assertTrue(row['disposition_ready'])
        self.assertEqual(row['errors'], [])
        self.assertEqual(row['request']['key'], 'review-lane')
        self.assertEqual(row['request']['generation'], 4)
        self.assertEqual(row['request']['evidence'],
                         {'path': 'output/proof.md',
                          'sha256': hashlib.sha256(b'submitted').hexdigest()})

    def test_rows_flag_orphaned_review_outside_any_workstream(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / 'output' / 'proof.md'
            proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted')},
                     'throughput': {'workstreams': {'species': {'lanes': []}}}}
            planned = rows(reg_for(root, state))
            self.assertTrue(planned[0]['orphaned'])
            state['throughput'] = {'workstreams': {'species': {'lanes': ['review-lane']}}}
            planned = rows(reg_for(root, state))
            self.assertFalse(planned[0]['orphaned'])

    def test_prepare_writes_requests_and_hashed_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / 'output' / 'proof.md'
            proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted')}}
            manifest = prepare(reg_for(root, state))
            request_path = root / 'output/workflow/review-acceptance/review-lane.accept-review.json'
            self.assertTrue(Path(manifest['manifest_path']).is_file())
            self.assertEqual(manifest['manifest_sha256'], digest(Path(manifest['manifest_path'])))
            entry = manifest['lanes'][0]
            self.assertEqual(entry['request_sha256'], digest(request_path))
            written = json.loads(request_path.read_text(encoding='utf-8'))
        self.assertEqual(written['key'], 'review-lane')
        self.assertEqual(written['summary'], 'Sole-integrator accept-review of review-ready outcome: '
                                             'Decision A proved; no runtime claim')

    def test_changed_evidence_is_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / 'output' / 'proof.md'
            proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted')}}
            proof.write_text('changed after review')
            planned = rows(reg_for(root, state))
            self.assertFalse(planned[0]['disposition_ready'])
            self.assertTrue(planned[0]['errors'])
            with self.assertRaises(Rejected):
                prepare(reg_for(root, state))
            self.assertFalse((root / 'output/workflow/review-acceptance').exists())

    def test_output_must_stay_under_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / 'output' / 'proof.md'
            proof.parent.mkdir(parents=True)
            proof.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted')}}
            with self.assertRaises(Rejected):
                prepare(reg_for(root, state), out_dir='docs/review-acceptance')

    def test_stale_git_source_pin_blocks_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tree = root / 'source'
            tree.mkdir()
            subprocess.run(['git', 'init'], cwd=tree, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@example.invalid'], cwd=tree, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Workflow Test'], cwd=tree, check=True)
            proof = tree / 'proof.txt'
            proof.write_text('base')
            subprocess.run(['git', 'add', 'proof.txt'], cwd=tree, check=True)
            subprocess.run(['git', 'commit', '-m', 'base'], cwd=tree, check=True, capture_output=True)
            base = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tree, check=True,
                                  capture_output=True, text=True).stdout.strip()
            proof.write_text('reviewed')
            subprocess.run(['git', 'commit', '-am', 'reviewed'], cwd=tree, check=True, capture_output=True)
            art = root / 'output' / 'proof.md'
            art.parent.mkdir(parents=True)
            art.write_text('submitted')
            state = {'lanes': {'review-lane': review_lane('output/proof.md', b'submitted',
                root=dict(base=base, head=base, commits=[], dirty='', worktree=str(tree)))}}
            planned = rows(reg_for(root, state))
            self.assertFalse(planned[0]['disposition_ready'])
            self.assertTrue(planned[0]['errors'])
            with self.assertRaises(Rejected):
                prepare(reg_for(root, state))


if __name__ == '__main__':
    unittest.main()
