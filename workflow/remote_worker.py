"""Portable one-job OpenCode worker. No direct access to the coordinator database."""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .handoff import require
from .runner import write


class Client:
    def __init__(self, credential):
        self.credential=credential
        url=urllib.parse.urlsplit(credential['url'])
        require(url.scheme=='http' and url.hostname=='127.0.0.1' and not url.username
                and not url.password and url.path in ('','/') and not url.query and not url.fragment,
                'Use a localhost SSH tunnel URL')

    def call(self,route,**data):
        request=urllib.request.Request(self.credential['url'].rstrip('/')+'/v1/'+route,
            data=json.dumps(data).encode(),headers={'Content-Type':'application/json',
            'Authorization':'Bearer '+self.credential['token']},method='POST')
        # Ignore proxy environment variables for credential-bearing loopback traffic.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):
                raise OSError('Coordinator redirects are not allowed')
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with opener.open(request,timeout=20) as response:return json.load(response)


def doctor():
    report=dict(platform=platform.system(),architecture=platform.machine(),python=platform.python_version(),
        git=shutil.which('git'),opencode=shutil.which('opencode'),ram_percent=None)
    try:
        import psutil
        report['ram_percent']=psutil.virtual_memory().percent
    except ImportError:
        report['missing']='Install requirements-worker.txt for portable memory measurements'
    report['ready']=bool(sys.version_info>=(3,12) and report['git'] and report['opencode'] and report['ram_percent'] is not None)
    return report


def git(tree,*args):
    return subprocess.check_output(['git','-C',str(tree),*args],text=True,encoding='utf-8',stderr=subprocess.STDOUT).strip()


def prepare_sources(job,directory):
    from .remote import REPOSITORIES,identifier
    import re
    identifier(job['id']);identifier(job['attempt'])
    branch='codex/remote-'+job['id']+'-'+str(job['generation'])
    root=directory/'root';trees={}
    for name in ('root','native'):
        if name not in job['sources']:continue
        source=job['sources'][name]
        require(source['url']==REPOSITORIES[name] and re.fullmatch('[0-9a-f]{40}',source['commit']), 'Invalid source specification')
        tree=root if name=='root' else root/'native'
        require(not tree.exists(), 'Attempt worktree already exists; reconcile instead of overwriting')
        tree.mkdir(parents=True)
        git(tree,'init');git(tree,'remote','add','origin',source['url'])
        git(tree,'fetch','--depth=1','origin',source['commit'])
        git(tree,'checkout','-b',branch,'FETCH_HEAD')
        require(git(tree,'rev-parse','HEAD')==source['commit'],'Fetched commit mismatch')
        trees[name]=tree
    return trees,branch


def run_one(client,state,instance,model):
    report=doctor();require(report['ready'],'Worker doctor checks failed: '+json.dumps(report))
    # Durable claim request survives a response loss. Successful delivery archives it.
    request_path=state/'claim.json'
    if request_path.exists():request=json.loads(request_path.read_text())['request']
    else:
        request=uuid.uuid4().hex;write(request_path,{'request':request})
    job=client.call('claim',instance=instance,request=request,ram_percent=report['ram_percent'])
    if job is None:
        request_path.unlink();print('No compatible queued job (or RAM is at the limit).');return
    directory=state/'attempts'/job['id']/job['attempt'];directory.mkdir(parents=True,exist_ok=True)
    write(directory/'job.json',job)
    # A stale lock is deliberately not auto-cleared: a prior process may still own children.
    with (directory/'launch.claim').open('x') as f:f.write(str(os.getpid()))
    request_path.unlink()
    identity=dict(instance=instance,job=job['id'],attempt=job['attempt'])
    finished=threading.Event();lost=threading.Event();deadline=[time.monotonic()+180]
    def heartbeat():
        while not finished.wait(20):
            try:
                response=client.call('heartbeat',**identity)
                deadline[0]=time.monotonic()+response['lease_seconds']
            except (OSError,ValueError):
                if time.monotonic()>=deadline[0]:
                    lost.set();return
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    write(directory/'status.json',{'state':'preparing','identity':identity})
    try:
        trees,branch=prepare_sources(job,directory)
        require(not lost.is_set() and time.monotonic()<deadline[0],'Authorization expired during checkout; retain private work')
        prompt=(f"You are the optional remote contributor for job {job['id']}, assigned issue #{job['issue']}. "
            "Implementation owner: Codex through shared account 4laric. Read AGENTS.md and "
            "docs/PIKMIN2_IMPLEMENTATION_FANOUT.md before work. This remote-job brief authorizes only the reserved scope. "
            "The coordinator owns the registry: do not run local lane registration, claims, receipt, integration, or ADMIT commands. "
            "Do not spawn agents. Work only in this private checkout and its native subcheckout when supplied. "
            "Do not run Windows-only commands on macOS. Native builds/runtime acceptance require Windows review later. "
            "Preserve files outside the reserved scope. Use private output/ for logs/tests and report limitations honestly. "
            f"Commit and push completed changes only on branch {branch} to the configured origin; no default/integration "
            "branch, tags or force pushes. Write a concise outcome to output/remote-result.json containing "
            '{"outcome":"candidate|review|blocked","summary":"what changed, tests, remaining work"}. '
            "A candidate is a proposal for Windows validation, not gameplay acceptance. "
            'Job: '+json.dumps({k:job[k] for k in ('issue','owned_files','acceptance','instruction','requirements','sources')}))
        write(directory/'prompt.json',{'prompt':prompt,'model':model})
        command=[report['opencode'],'run','--dir',str(trees['root']),'-m',model,'--auto','--format','json',prompt]
        with (directory/'events.jsonl').open('wb') as output,(directory/'stderr.log').open('wb') as errors:
            process=subprocess.Popen(command,cwd=trees['root'],stdout=output,stderr=errors,
                **({'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}))
            write(directory/'status.json',{'state':'running','pid':process.pid,'identity':identity})
            code=process.wait()
        # Disconnected work can finish privately, but cannot publish an authoritative result.
        require(not lost.is_set() and time.monotonic()<deadline[0], 'Lease lost; keep private output for integrator reconciliation')
        client.call('heartbeat',**identity)
        result_path=trees['root']/'output/remote-result.json'
        result=json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else dict(outcome='blocked',summary='OpenCode exited without an outcome report; inspect preserved attempt logs.')
        require(result.get('outcome') in ('candidate','blocked','review') and isinstance(result.get('summary'),str),'Invalid contributor result')
        commits={k:git(tree,'rev-parse','HEAD') for k,tree in trees.items()}
        dirty={k:git(tree,'status','--porcelain') for k,tree in trees.items()}
        if code or any(dirty.values()):
            result=dict(outcome='blocked',summary=result['summary']+'\nUncommitted files or nonzero OpenCode exit require reconciliation.')
        evidence=json.dumps(dict(job=job['id'],attempt=job['attempt'],worker=client.credential['worker'],platform=report,
            source_pins=job['sources'],commits=commits,branch=branch,dirty=dirty,exit_code=code,
            result=result,events_tail=(directory/'events.jsonl').read_bytes()[-100000:].decode('utf-8',errors='replace'))).encode()
        sha=hashlib.sha256(evidence).hexdigest()
        write(directory/'submission.json',dict(identity=identity,result=dict(outcome=result['outcome'],summary=result['summary'],commits=commits,evidence=[sha])))
        (directory/'evidence.json').write_bytes(evidence)
        client.call('artifact',**identity,sha256=sha,content=base64.b64encode(evidence).decode())
        response=client.call('result',**identity,result=json.loads((directory/'submission.json').read_text())['result'])
        write(directory/'status.json',dict(state='submitted',response=response))
        print(json.dumps(response))
    except BaseException as exc:
        write(directory/'status.json',dict(state='needs_reconciliation',identity=identity,error=str(exc),
            note='Private work is preserved; inspect any surviving child before retrying.'))
        raise
    finally:
        finished.set();thread.join(timeout=22)


def retry_submission(client,directory):
    """Retry identical result after a lost response; never start another process."""
    saved=json.loads((directory/'submission.json').read_text())
    # The result endpoint itself recognizes already-accepted identical submissions.
    try:
        return client.call('result',**saved['identity'],result=saved['result'])
    except urllib.error.HTTPError as exc:
        if exc.code != 409:raise
        message=json.loads(exc.read()).get('error','')
        if message not in ('Upload evidence before submitting result','Evidence must belong to this attempt'):raise
        evidence=(directory/'evidence.json').read_bytes();sha=hashlib.sha256(evidence).hexdigest()
        require(sha in saved['result']['evidence'],'Saved evidence hash changed')
        client.call('artifact',**saved['identity'],sha256=sha,content=base64.b64encode(evidence).decode())
        return client.call('result',**saved['identity'],result=saved['result'])
