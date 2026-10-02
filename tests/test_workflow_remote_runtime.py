"""Delivery checks with optional actual, locally collected White golden packet.

Set PIKMIN_REMOTE_HANDOFF_GOLDEN and PIKMIN_REMOTE_HANDOFF_ROOT for the recorded
consumer check. No runtime is launched and no acceptance gates are fabricated.
"""
import copy
import hashlib
import json
import os
import subprocess
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

    def test_pinned_git_attributes_keep_non_text_binary_exact(self):
        from workflow.remote_runtime import committed_manifest, checkout_digest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def git(*args):
                return subprocess.check_output(['git','-C',tmp,*args])
            git('init','-q')
            (root/'.gitattributes').write_text('payload.bin -text\nauto.bin text=auto\nscript.bat text eol=crlf\n')
            payload=b'\xff\x01binary\r\nbytes\r\n'
            (root/'payload.bin').write_bytes(payload)
            # Git's binary heuristic also refuses conversion of this NUL-free auto blob.
            auto=b'\x01\x02\x03\x04\x05\x06\x07\r\n'
            (root/'auto.bin').write_bytes(auto)
            (root/'script.bat').write_bytes(b'echo hello\n')
            git('add','.')
            git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','attributes fixture')
            head=git('rev-parse','HEAD').decode().strip()
            manifests=committed_manifest(tmp,head)
            self.assertEqual(manifests['payload.bin'],{hashlib.sha256(payload).hexdigest()})
            self.assertEqual(checkout_digest(tmp,head,'payload.bin'),hashlib.sha256(payload).hexdigest())
            self.assertNotEqual(checkout_digest(tmp,head,'payload.bin'),hashlib.sha256(payload.replace(b'\r\n',b'\n')).hexdigest())
            self.assertEqual(checkout_digest(tmp,head,'auto.bin'),hashlib.sha256(auto).hexdigest())
            self.assertEqual(checkout_digest(tmp,head,'script.bat'),hashlib.sha256(b'echo hello\r\n').hexdigest())
            # Working-tree attributes do not supersede the immutable committed policy.
            (root/'.gitattributes').write_text('payload.bin text eol=lf\n')
            checkout_digest.cache_clear()
            self.assertEqual(checkout_digest(tmp,head,'payload.bin'),hashlib.sha256(payload).hexdigest())


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

    def test_full_raw_freeze_keeps_remote_descriptors(self):
        from workflow.delivery import DeliveryMixin
        from workflow.handoff import local_path, digest
        data=copy.deepcopy(self.golden)
        class Consumer(DeliveryMixin):
            root=self.root
            def evidence(inner,item):
                path=local_path(inner.root,item['path'])
                self.assertEqual(digest(path),item['sha256'])
                return path
        consumer=Consumer()
        frozen=consumer._delivery_freeze({},data)
        payload=json.loads(Path(frozen['handoff']['path']).read_text())
        self.assertEqual(payload['build'],data['build'])
        self.assertEqual(len(payload['build']['remote']['raw']),58)
        result=validate_handoff(self.root,payload)
        self.assertFalse(result['gameplay_accepted'])
        self.assertTrue(result['slice_passed'])

    def test_temporary_registry_real_submit_and_freeze(self):
        from workflow.registry import Registry
        from workflow.handoff import digest
        data=copy.deepcopy(self.golden)
        with tempfile.TemporaryDirectory(dir=self.root/'output') as tmp:
            registry=Registry(Path(tmp)/'registry.sqlite3',self.root)
            registry.init()
            # Same isolated fixture setup as existing delivery tests; no canonical mutation.
            with registry.transaction() as state:
                state['settings']['freeze_handoffs_on_submit']=True
            source=Registry(self.root/'output/workflow/registry.sqlite3',self.root).snapshot()['lanes'][data['lane']]
            fields=['lane','owner','worker_id','task_id','issue','scope','target_level',
                    'next_action','milestone','owned_files','acceptance','root','native']
            claim={k:copy.deepcopy(source[k]) for k in fields}
            claim['pid']=source['process']['pid']
            lane=registry.register(claim)
            self.assertEqual(lane['process'],source['process'])
            lane=registry.checkpoint(lane['lane'],lane['generation'],lane['revision'],dict(state='running'))
            path=Path(tmp)/'handoff.json';path.write_text(json.dumps(data))
            submitted=registry.submit_handoff(lane['lane'],lane['generation'],lane['revision'],str(path))
            self.assertEqual(submitted['state'],'handoff_ready')
            self.assertNotEqual(submitted['handoff']['path'],str(path))
            result=registry.check_handoff(submitted)
            self.assertTrue(result['slice_passed'])
            self.assertFalse(result['gameplay_accepted'])
            frozen=json.loads(Path(submitted['handoff']['path']).read_text())
            self.assertEqual(frozen['build'],data['build'])
            self.assertEqual(len(frozen['build']['remote']['raw']),58)
            self.assertEqual(digest(Path(submitted['handoff']['path'])),submitted['handoff']['sha256'])

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
