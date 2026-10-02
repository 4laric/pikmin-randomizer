"""Delivery checks with optional actual, locally collected White golden packet.

Set PIKMIN_REMOTE_HANDOFF_GOLDEN and PIKMIN_REMOTE_HANDOFF_ROOT for the recorded
consumer check. No runtime is launched and no acceptance gates are fabricated.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from workflow.handoff import Rejected, validate_handoff
from workflow.remote_runtime import descriptor


class RemoteDescriptorTests(unittest.TestCase):
    def test_descriptor_is_inert(self):
        self.assertEqual(descriptor('/srv/game-ci/jobs/fixture-1-1/build', '/srv/game-ci/jobs'),
                         '/srv/game-ci/jobs/fixture-1-1/build')

    def test_escapes_and_windows_paths_refused(self):
        for value in ['/srv/game-ci/jobs/../secrets', '/srv/game-ci/jobs//x',
                      'C:/srv/game-ci/jobs/x', '/srv/game-ci/jobs/x\\y',
                      '/srv/game-ci/jobs2/x', '/srv/game-ci/jobs/x\x00y',
                      '/srv/game-ci/jobs/./x', '//srv/game-ci/jobs/x']:
            with self.subTest(value=value), self.assertRaises(Rejected):
                descriptor(value, '/srv/game-ci/jobs')


@unittest.skipUnless(os.environ.get('PIKMIN_REMOTE_HANDOFF_GOLDEN'), 'Actual golden collection not configured')
class ActualRemoteConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ['PIKMIN_REMOTE_HANDOFF_ROOT'])
        cls.golden = json.loads(Path(os.environ['PIKMIN_REMOTE_HANDOFF_GOLDEN']).read_text(encoding='utf-8'))

    def test_actual_packet_retains_scope(self):
        result = validate_handoff(self.root, copy.deepcopy(self.golden))
        self.assertTrue(result['reviewable'])
        self.assertTrue(result['slice_passed'])
        self.assertFalse(result['gameplay_accepted'])
        self.assertEqual(result['outstanding_gates'], ['attacks_receivers', 'death_corpse', 'cleanup_reentry'])

    def test_original_local_schema_refusal(self):
        data = copy.deepcopy(self.golden)
        del data['build']['delivery']
        with self.assertRaisesRegex(Rejected, 'Path escapes workspace'):
            validate_handoff(self.root, data)

    def test_remote_identity_pin_and_path_mutations(self):
        cases = [(['build','remote','run_id'],36989763314),
                 (['build','remote','attempt'],2),
                 (['build','remote','request_id'],'0'*32),
                 (['build','remote','root_tree'],'0'*40),
                 (['build','remote','native_tree'],'0'*40),
                 (['build','remote','controller_head'],'0'*40),
                 (['build','remote','native_deadline'],61),
                 (['build','remote','outer_deadline'],301),
                 (['build','remote','repository'],'someone/else'),
                 (['build','directory'],'/srv/game-ci/jobs/../secret'),
                 (['build','executable','path'],'C:/fake.exe'),
                 (['build','executable','sha256'],'0'*64)]
        for keys,value in cases:
            data=copy.deepcopy(self.golden); parent=data
            for key in keys[:-1]: parent=parent[key]
            parent[keys[-1]]=value
            with self.subTest(keys=keys), self.assertRaises(Rejected):
                validate_handoff(self.root,data)

    def test_missing_raw_is_refused(self):
        data=copy.deepcopy(self.golden)
        del data['build']['remote']['raw']['broker-cleanup.json']
        with self.assertRaises(Rejected): validate_handoff(self.root,data)

    def test_tampered_local_file_is_refused(self):
        data=copy.deepcopy(self.golden)
        key=data['build']['remote']['raw']['job--build.log']
        data['evidence'][key]['sha256']='0'*64
        with self.assertRaisesRegex(Rejected,'Evidence hash mismatch'):
            validate_handoff(self.root,data)

    def test_rehashed_receipt_cannot_weaken_phase_or_profile(self):
        mutations=[lambda r:r['white_carry_runtime']['phases'].pop(),
                   lambda r:r['white_carry_runtime']['phases'][0].update(native_exit=86),
                   lambda r:r['white_carry_runtime']['phases'][-1]['cleanup_probe'].update(outcome='alive'),
                   lambda r:r['configuration'].update(netplay='ON'),
                   lambda r:r['selected_source'].update(sha256='0'*64),
                   lambda r:r['admission_proof']['pins'].update(NATIVE_SHA='0'*40),
                   lambda r:r['white_carry_runtime'].update(human_launched=True),
                   lambda r:r['white_carry_runtime']['phases'][-1]['oracle'].update(full_campaign=True)]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory(dir=self.root/'output') as tmp:
                data=copy.deepcopy(self.golden); remote=data['build']['remote']; receipt_key=remote['receipt']
                original=self.root/data['evidence'][receipt_key]['path']
                receipt=json.loads(original.read_text());mutate(receipt)
                path=Path(tmp)/'receipt.json';path.write_text(json.dumps(receipt))
                ref=dict(path=str(path.relative_to(self.root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                data['evidence'][receipt_key]=ref
                raw_key=remote['raw']['job--result.json'];data['evidence'][raw_key]=ref
                manifest=json.loads((self.root/data['evidence'][remote['manifest']]['path']).read_text())
                for entry in manifest['files']:
                    if entry['name']=='job--result.json':entry.update(sha256=ref['sha256'],bytes=path.stat().st_size)
                mpath=Path(tmp)/'manifest.json';mpath.write_text(json.dumps(manifest))
                data['evidence'][remote['manifest']]=dict(path=str(mpath.relative_to(self.root)),sha256=hashlib.sha256(mpath.read_bytes()).hexdigest())
                with self.assertRaises(Rejected):validate_handoff(self.root,data)


if __name__ == '__main__':
    unittest.main()
