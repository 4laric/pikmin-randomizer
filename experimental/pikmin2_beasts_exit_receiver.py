"""Explicit receiver for immutable Beasts exit42 fixture evidence."""
import hashlib
import json
from pathlib import Path, PurePosixPath
from experimental.pikmin2_beasts_transfer import checkpoint_payload


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def receive_exit(ledger,launch_state,directory):
    """Retry with the same launch state/run after an uncertain commit.

    Evidence is correlated and hash-checked, not cryptographically attested.
    This API never launches the next floor or changes the suspended surface.
    """
    ledger._validate(launch_state)
    if (launch_state['campaign']!=ledger.campaign or launch_state['content']!=ledger.content
            or launch_state['schema']!=2 or launch_state['phase']!='cave'
            or launch_state['trip']['checkpoint']['floor']!=2):
        raise ValueError('Receiver requires the original active floor2 launch state')
    directory=Path(directory)
    evidence=json.loads((directory/'acceptance.json').read_text())
    if (evidence.get('passed') is not True or type(evidence.get('returncode')) is not int
            or evidence['returncode']!=42 or evidence.get('exit_handoff_fixture') is not True):
        raise ValueError('Native run did not complete an exit42 handoff')
    token=launch_state['trip']['token']
    if evidence.get('boundary_token')!=token:raise ValueError('Run belongs to another boundary')
    hashes=evidence.get('input_sha256')
    if not isinstance(hashes,dict):raise ValueError('Missing input hashes')
    readiness_raw=(directory/'readiness.json').read_bytes()
    readiness=json.loads(readiness_raw)
    required={'readiness.json','p2-purple.txt','p2-pod.txt','p2-cargo-free.txt','p2-beasts-floor2-fixture.txt',
              'p2-beasts-boundary.txt','p2-cave-entry.txt','p2-cave-transition.txt','p2-beasts-exit-fixture.txt'}
    required|={'assets/'+name for name in readiness['override_sha256']}
    if set(hashes)!=required:raise ValueError('Incomplete handoff input manifest')
    for name,digest in hashes.items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid handoff input path')
        raw=readiness_raw if name=='readiness.json' else (directory/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Handoff input changed: '+name)
    frozen={}
    for path,key in ((directory/'native.log','log_sha256'),(directory/'p2-cave-transfer.txt','transfer_sha256'),
                     (Path(evidence['executable']),'executable_sha256')):
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=evidence.get(key):raise ValueError('Handoff evidence changed: '+key)
        if key!='executable_sha256':frozen[key]=raw
    payload=checkpoint_payload(ledger.adapter,launch_state['trip']['checkpoint'],
        frozen['log_sha256'].decode('utf-8',errors='replace').replace('\r\n','\n'),readiness,
        frozen['transfer_sha256'].decode('utf-8').replace('\r\n','\n'))
    return ledger.apply_beasts_floor(launch_state['revision'],token,**payload)
