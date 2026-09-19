import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from workflow.handoff import Rejected
from workflow.registry import Registry
from workflow.controller import Controller
from workflow.remote import REPOSITORIES
from workflow.remote_http import make_server
from workflow.remote_worker import Client,run_one


class RemoteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.now=1000
        self.reg=Registry(self.root/'output/workflow/registry.sqlite3',self.root,clock=lambda:self.now)
        self.reg.init()
        self.provision('mac','secret')
        self.reg.remote_register('mac','instance','Darwin',['source-edit','review','python-tests'])

    def provision(self,name,token):
        self.reg.remote_provision(name,hashlib.sha256(token.encode()).hexdigest(),'Darwin',['source-edit','review','python-tests'])

    def job(self,name='job',**changes):
        data=dict(job=name,issue=512,owned_files=['experimental/remote_example.py'],acceptance=['Pure Python tests pass'],
            instruction='Implement only the issue scope',requirements=['source-edit'],sources={
                'root':dict(url=REPOSITORIES['root'],commit='a'*40,ref='refs/heads/codex/pilot')})
        data.update(changes)
        return self.reg.remote_enqueue(**data)

    def claim(self,request='request'):
        return self.reg.remote_claim('mac','instance',request,50)

    def upload(self,attempt):
        content=b'evidence, not acceptance';sha=hashlib.sha256(content).hexdigest()
        self.reg.remote_artifact('mac','instance','job',attempt,base64.b64encode(content).decode(),sha)
        return sha

    def result(self,attempt):
        return dict(summary='Source candidate; Windows validation pending',commits={'root':'b'*40},evidence=[self.upload(attempt)],outcome='candidate')

    def test_claim_retry_and_one_worker_limit(self):
        self.job();first=self.claim();self.assertEqual(first['attempt'],self.claim()['attempt'])
        with self.assertRaises(Rejected):self.claim('second')

    def test_mac_never_claims_windows_runtime(self):
        self.job(requirements=['windows-runtime']);self.assertIsNone(self.claim())
        with self.assertRaises(Rejected):self.reg.remote_register('mac','instance','Darwin',['windows-runtime'])

    def test_ram_limit_leaves_job_queued(self):
        self.job();self.assertIsNone(self.reg.remote_claim('mac','instance','request',75))

    def test_sleep_fences_result_and_new_attempt_uses_new_identity(self):
        self.job();old=self.claim();result=self.result(old['attempt']);self.now+=181
        with self.assertRaises(Rejected):self.reg.remote_result('mac','instance','job',old['attempt'],result)
        self.reg.remote_requeue('job')
        self.reg.remote_register('mac','instance','Darwin',['source-edit'])
        new=self.claim('new')
        self.assertNotEqual(new['attempt'],old['attempt']);self.assertEqual(new['generation'],2)
        with self.assertRaises(Rejected):self.reg.remote_heartbeat('mac','instance','job',old['attempt'])

    def test_worker_instance_takeover_requires_expiry(self):
        with self.assertRaises(Rejected):self.reg.remote_register('mac','replacement','Darwin',['review'])
        self.now+=181;self.reg.remote_register('mac','replacement','Darwin',['review'])
        with self.assertRaises(Rejected):self.claim()

    def test_heartbeat_extends_attempt_but_cannot_revive_expired_attempt(self):
        self.job();item=self.claim();self.now+=100
        self.assertEqual(self.reg.remote_heartbeat('mac','instance','job',item['attempt'])['expires'],1280)
        self.now=1281
        with self.assertRaises(Rejected):self.reg.remote_heartbeat('mac','instance','job',item['attempt'])

    def test_result_replay_and_no_admission(self):
        self.job();item=self.claim();result=self.result(item['attempt'])
        self.assertEqual(self.reg.remote_result('mac','instance','job',item['attempt'],result)['state'],'awaiting_windows_validation')
        self.now+=300
        self.assertEqual(self.reg.remote_result('mac','instance','job',item['attempt'],result)['state'],'awaiting_windows_validation')
        self.assertEqual(self.reg.status()['lanes'],{})
        self.assertEqual(len(self.reg.control_status()['decisions']),1)
        controller=Controller(self.reg,dict(output='output/controller',integrator_inbox='output/inbox'))
        controller.deliver_notifications();controller.deliver_notifications()
        self.assertEqual(len(list((self.root/'output/inbox').glob('*.md'))),1)

    def test_wrong_worker_and_bad_artifact(self):
        self.job();item=self.claim();self.provision('other','othersecret')
        self.reg.remote_register('other','instance2','Darwin',['review'])
        with self.assertRaises(Rejected):self.reg.remote_heartbeat('other','instance2','job',item['attempt'])
        with self.assertRaises(Rejected):self.reg.remote_artifact('mac','instance','job',item['attempt'],'YQ==','0'*64)

    def test_artifact_limits_and_attempt_ownership(self):
        self.job();item=self.claim()
        content=b'x'*(1024*1024+1)
        with self.assertRaises(Rejected):self.reg.remote_artifact('mac','instance','job',item['attempt'],base64.b64encode(content).decode(),hashlib.sha256(content).hexdigest())
        sha=self.upload(item['attempt'])
        self.now+=181;self.reg.remote_requeue('job');self.reg.remote_register('mac','instance','Darwin',['source-edit'])
        new=self.claim('new')
        with self.assertRaises(Rejected):self.reg.remote_result('mac','instance','job',new['attempt'],dict(summary='Old evidence',commits={'root':'b'*40},outcome='candidate',evidence=[sha]))

    def test_offline_does_not_automatically_release_scope(self):
        self.job();self.claim();self.now+=181
        with self.assertRaises(Rejected):self.job('other',issue=999)
        self.reg.remote_close('job','Cancelled after reviewing private attempt; no integration')
        self.job('other',issue=999)

    def lane(self):
        return dict(lane='local',owner='Codex',worker_id='local',task_id='opencode:local',issue=99,
            scope='test',target_level='candidate',next_action='work',milestone='pilot',owned_files=['experimental/remote_example.py'],
            acceptance=['tested'],pid=os.getpid(),root=dict(base='a'*40,head='a'*40,commits=[],dirty='',worktree=str(self.root)),native=None)

    def test_source_ownership_conflicts_both_directions(self):
        self.job()
        with self.assertRaises(Rejected):self.reg.register(self.lane())
        self.reg.remote_close('job','Cancelled before start')
        self.reg.register(self.lane())
        with self.assertRaises(Rejected):self.job('new')

    def test_local_source_paths_and_traversal_rejected(self):
        with self.assertRaises(Rejected):self.job(owned_files=['../escape'])
        with self.assertRaises(Rejected):self.job(sources={'root':dict(url='C:/local/repo',commit='a'*40,ref='refs/heads/main')})

    def test_revocation_blocks_auth_and_renewal(self):
        self.job();item=self.claim();self.reg.remote_revoke('mac')
        with self.assertRaises(PermissionError):self.reg.remote_auth('secret')
        with self.assertRaises(Rejected):self.reg.remote_heartbeat('mac','instance','job',item['attempt'])

    def serve(self):
        server=make_server(self.reg,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def close():server.shutdown();server.server_close();thread.join(timeout=2)
        self.addCleanup(close)
        return 'http://127.0.0.1:'+str(server.server_port)

    def test_real_http_auth_claim_upload_result_replay(self):
        self.job();url=self.serve();client=Client(dict(url=url,token='secret'))
        item=client.call('claim',instance='instance',request='request',ram_percent=50)
        identity=dict(instance='instance',job='job',attempt=item['attempt'])
        content=b'Windows validation pending';sha=hashlib.sha256(content).hexdigest()
        client.call('artifact',**identity,sha256=sha,content=base64.b64encode(content).decode())
        result=dict(summary='Review this source candidate',commits={'root':'b'*40},evidence=[sha],outcome='candidate')
        first=client.call('result',**identity,result=result)
        self.assertEqual(first,client.call('result',**identity,result=result))
        with self.assertRaises(urllib.error.HTTPError) as err:Client(dict(url=url,token='bad')).call('claim',instance='instance',request='bad',ram_percent=20)
        self.assertEqual(err.exception.code,401)
        with self.assertRaises(urllib.error.HTTPError) as err:client.call('enqueue',job='arbitrary')
        self.assertEqual(err.exception.code,404)

    def test_two_http_workers_cannot_claim_same_job(self):
        self.job();self.provision('other','other');self.reg.remote_register('other','second','Darwin',['source-edit'])
        url=self.serve()
        def claim(pair):
            token,instance=pair
            return Client(dict(url=url,token=token)).call('claim',instance=instance,request='request',ram_percent=20)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(claim,[('secret','instance'),('other','second')]))
        self.assertEqual(sum(r is not None for r in results),1)

    def test_client_rejects_nonlocal_transport(self):
        with self.assertRaises(Rejected):Client(dict(url='http://example.com:8791',token='secret'))

    def test_real_checkout_process_and_http_submission(self):
        source=self.root/'source';source.mkdir()
        def git(*args):return subprocess.check_output(['git','-C',str(source),*args],text=True).strip()
        git('init');git('config','user.email','test@example.invalid');git('config','user.name','Test')
        (source/'.gitignore').write_text('/output/\n');(source/'README.md').write_text('fixture source\n')
        git('add','.');git('commit','-m','fixture');sha=git('rev-parse','HEAD')
        stub=self.root/'fake_opencode.py'
        stub.write_text("import json,sys\nfrom pathlib import Path\nr=Path(sys.argv[sys.argv.index('--dir')+1]);(r/'output').mkdir()\n(r/'output/remote-result.json').write_text(json.dumps({'outcome':'review','summary':'Fixture review completed'}))\nprint(json.dumps({'type':'text','part':{'text':'review done'}}))\n")
        original=subprocess.Popen
        def popen(command,*args,**kwargs):
            if command[0]=='fake-opencode':command=[sys.executable,str(stub),*command[1:]]
            return original(command,*args,**kwargs)
        with patch.dict(REPOSITORIES,root=str(source)):
            self.job(sources={'root':dict(url=str(source),commit=sha,ref='refs/heads/pilot')})
            url=self.serve();client=Client(dict(url=url,token='secret',worker='mac'))
            state=self.root/'output/remote-worker';state.mkdir()
            with (patch('workflow.remote_worker.doctor',return_value=dict(ready=True,opencode='fake-opencode',ram_percent=30,platform='Darwin')),
                  patch('workflow.remote_worker.subprocess.Popen',side_effect=popen)):
                run_one(client,state,'instance','test/model')
            item=self.reg.remote_status()['jobs'][0]
            self.assertEqual(item['state'],'awaiting_review')
            self.assertEqual(item['result']['commits']['root'],sha)
            self.assertEqual(len(list((state/'attempts').rglob('launch.claim'))),1)


if __name__=='__main__':unittest.main()
