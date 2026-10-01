"""Strict terminal transfer parsing; no successful descent or reward acceptance."""
import re
import hashlib
import json
from pathlib import Path,PurePosixPath
from experimental.pikmin2_beasts_checkpoint_reference import digest
from experimental.pikmin2_surface_ledger import _unique
from experimental.pikmin2_campaign import SPECIES


def failure_reason(text,token):
    if not isinstance(token,str) or re.fullmatch('[0-9a-f]{64}',token) is None:
        raise ValueError('Invalid failure boundary token')
    if not isinstance(text,str):raise ValueError('Invalid failure transfer')
    lines=text.splitlines()
    if (len(lines)!=4 or lines[0]!='P2_BEASTS_FAILURE_1' or lines[1]!=token
            or lines[2]!='3 0 0 0' or lines[3] not in ('extinction','knockout')):
        raise ValueError('Invalid floor3 failure transfer')
    return lines[3]


def apply_failure(ledger,launch_state,text):
    """Apply already-verified transfer bytes; callers own evidence validation."""
    ledger._validate(launch_state)
    if (launch_state['content']!=ledger.content or launch_state['campaign']!=ledger.campaign
            or launch_state['schema']!=2 or launch_state['phase']!='cave'
            or launch_state['trip']['checkpoint']['floor']!=3):
        raise ValueError('Failure requires original active floor3 launch state')
    token=launch_state['trip']['token']
    return ledger.fail_beasts_floor3(launch_state['revision'],token,failure_reason(text,token))


def receive_failure(ledger,launch_state,directory):
    """Hash-correlated fixture receiver; unsigned evidence is not attestation."""
    directory=Path(directory)
    def decode(raw):return json.loads(raw,object_pairs_hook=_unique)
    def hashed(raw,expected):
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Failure evidence changed')
        return raw
    evidence=decode((directory/'acceptance.json').read_bytes())
    token=launch_state['trip']['token']
    if (evidence.get('policy')!='P2_BEASTS_FAILURE_1' or evidence.get('passed') is not True
            or type(evidence.get('returncode')) is not int or evidence['returncode']!=42
            or evidence.get('token')!=token or evidence.get('reason') not in ('extinction','knockout')):
        raise ValueError('Missing successful native failure handoff')
    hashes=evidence.get('input_sha256')
    if not isinstance(hashes,dict):raise ValueError('Missing failure input manifest')
    frozen={}
    for name,expected in hashes.items():
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid failure input path')
        frozen[name]=hashed((directory/name).read_bytes(),expected)
    required={'survey.json','checkpoint.json','p2-floor3-boundary.txt','p2-cave-entry.txt',
              'p2-floor3-failure-fixture.txt','p2-cargo-free.txt','p2-pod.txt','p2-purple.txt'}
    if not required<=frozen.keys() or any(name not in required and not name.startswith('assets/') for name in frozen):
        raise ValueError('Incomplete or unexpected failure inputs')
    survey=decode(frozen['survey.json'])
    if (set(hashes)!={'survey.json'}|set(survey['input_sha256'])
            or any(hashes[name]!=expected for name,expected in survey['input_sha256'].items())):
        raise ValueError('Failure input manifests disagree')
    checkpoint=decode(frozen['checkpoint.json'])
    ledger._validate(launch_state)
    if checkpoint!=launch_state['trip']['checkpoint']:
        raise ValueError('Failure checkpoint differs from launch')
    if (survey.get('policy')!='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1' or survey.get('floor')!=3
            or survey.get('native_profile')!='forest_1' or survey.get('boundary_token')!=token
            or survey.get('checkpoint_identity')!=digest(checkpoint) or survey.get('checkpoint_profile')!=ledger.adapter.identity
            or survey.get('party_restore_protocol_floor')!=3
            or survey.get('party')!=dict(health=checkpoint['health'],squad=checkpoint['squad'])):
        raise ValueError('Failure stage is not bound to this checkpoint')
    reason=evidence['reason']
    entry=['P2_BEASTS_FLOOR3_ENTRY_1',token,f'3 {checkpoint["health"]:.9g} {len(checkpoint["squad"])}']
    entry += [f'{SPECIES.index(p["species"])} {p["maturity"]}' for p in checkpoint['squad']]
    if frozen['p2-cave-entry.txt'].decode().splitlines()!=entry:
        raise ValueError('Native entry party differs from checkpoint')
    if (frozen['p2-floor3-boundary.txt'].decode().strip()!=token
            or frozen['p2-floor3-failure-fixture.txt'].decode().splitlines()!=['P2_FLOOR3_FAILURE_FIXTURE_1',reason]):
        raise ValueError('Failure mode/boundary differs')
    log=hashed((directory/'native.log').read_bytes(),evidence.get('log_sha256')).decode('utf-8').replace('\r\n','\n')
    transfer=hashed((directory/'p2-cave-transfer.txt').read_bytes(),evidence.get('transfer_sha256')).decode('utf-8')
    hashed(Path(evidence['exe']).read_bytes(),evidence.get('executable_sha256'))
    if failure_reason(transfer,token)!=reason:raise ValueError('Failure reason differs')
    markers=[f'P2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled',
        f'P2_FLOOR3_FAILURE_ARMED token={token} reason={reason} active_descent_rejected=1',
        f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0',
        f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0']
    lines=log.splitlines()
    if (any(lines.count(m)!=1 for m in markers) or [lines.index(m) for m in markers]!=sorted(lines.index(m) for m in markers)
            or any(m in log for m in ('FAIL ','P2_POD_RECEIPT','P2_TREASURE_DELIVERED','P2_VIOLET_WITNESS'))):
        raise ValueError('Missing, unordered or conflicting native failure evidence')
    return apply_failure(ledger,launch_state,transfer)
