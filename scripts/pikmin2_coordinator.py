"""Local administration and optional loopback API for a Mac worker pilot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workflow.registry import Registry
from workflow.remote_http import make_server
from workflow.handoff import require


def verify_issue_sources(data):
    raw=subprocess.check_output(['gh','issue','view',str(data['issue']),'--repo','4laric/pikmin-randomizer',
        '--json','state,assignees,body'],text=True,encoding='utf-8')
    issue=json.loads(raw)
    require(issue['state']=='OPEN' and any(a['login']=='4laric' for a in issue['assignees']), 'Issue must be open and assigned to 4laric')
    require(all(criterion in issue['body'] for criterion in data['acceptance']), 'Acceptance criteria must already be written in the issue body')
    from workflow.remote import REPOSITORIES
    for name,source in data['sources'].items():
        require(source['url']==REPOSITORIES[name], 'Noncanonical source URL')
        require(source['ref'].startswith('refs/heads/'), 'Published branch required')
        refs=subprocess.check_output(['git','ls-remote','--refs',source['url'],source['ref']],text=True).splitlines()
        require(any(line.split()==[source['commit'],source['ref']] for line in refs), 'Source pin must be published at the specified branch tip before queueing')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--request',type=Path)
    p.add_argument('--port',type=int,default=8791)
    p.add_argument('command',choices=['serve','provision','enqueue','status','requeue','close','revoke'])
    args=p.parse_args();root=args.root.resolve();reg=Registry(root/'output/workflow/registry.sqlite3',root)
    data=json.loads(args.request.read_text(encoding='utf-8-sig')) if args.request else {}
    if args.command=='serve':
        server=make_server(reg,args.port)
        print('Coordinator listening only on 127.0.0.1:'+str(server.server_port),flush=True)
        server.serve_forever();return
    if args.command=='provision':
        token=secrets.token_urlsafe(32)
        from workflow.remote import identifier
        identifier(data['worker'])
        directory=root/'output/workflow/remote/credentials';directory.mkdir(parents=True,exist_ok=True)
        path=directory/(data['worker']+'.json')
        # Create exclusively: a repeated command must not replace a usable credential.
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(dict(worker=data['worker'],token=token,url='http://127.0.0.1:8791',
                platform=data['platform'],capabilities=data['capabilities']),f,indent=2)
        try:
            reg.remote_provision(**data,token_sha256=hashlib.sha256(token.encode()).hexdigest())
        except Exception:
            path.unlink();raise
        print(json.dumps({'credential_file':str(path),'note':'Transfer privately; never commit this file'}));return
    if args.command=='enqueue':verify_issue_sources(data)
    print(json.dumps(getattr(reg,'remote_'+args.command)(**data),indent=2))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(2)
