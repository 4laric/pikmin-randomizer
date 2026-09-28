"""Native failure fixture and evidence capture; host terminal ledger writer is separate."""
import json
import math
import os
from pathlib import Path
import re
import subprocess
from collections import Counter

from experimental.pikmin2_beasts_floor3_runtime import fixture as walking_fixture, sha
from experimental.pikmin2_beasts_party_restore import restore_party
from experimental.pikmin2_beasts_party_snapshot import party_snapshot


def fixture(source,output):
    walking_fixture(source,output)
    raw=output.read_text();marker='class RoomApp : public PlugPikiApp {'
    helper=Path(__file__).with_name('pikmin2_beasts_floor3_failure_survey.inc').read_text()
    if raw.count(marker)!=1 or raw.count('floorThreeSurvey(n);')!=1:raise ValueError('Survey fixture anchors changed')
    output.write_text(raw.replace(marker,helper+'\n'+marker).replace('floorThreeSurvey(n);','floorThreeFailureSurvey(n);'))
    return output


def arm(directory,reason):
    if reason not in ('extinction','knockout'):raise ValueError('Unknown terminal fixture reason')
    if (directory/'native.log').exists() or (directory/'p2-floor3-failure-fixture.txt').exists():raise ValueError('Terminal fixture must be fresh')
    report=json.loads((directory/'survey.json').read_bytes())
    if report['policy']!='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1' or report.get('party_restore_protocol_floor')!=3:
        raise ValueError('Terminal fixture requires bound floor3 entry')
    data=f'P2_FLOOR3_FAILURE_FIXTURE_1\n{reason}\n'.encode()
    (directory/'p2-floor3-failure-fixture.txt').write_bytes(data)
    report['input_sha256']['p2-floor3-failure-fixture.txt']=sha(data)
    report['terminal_fixture_reason']=reason
    (directory/'survey.json').write_text(json.dumps(report,indent=2)+'\n')


def validate(log,transfer,token,reason,party):
    party=restore_party(party)
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token) or reason not in ('extinction','knockout'):
        raise ValueError('Invalid expected terminal identity')
    expected=f'P2_BEASTS_FAILURE_1\n{token}\n3 0 0 0\n{reason}\n'.encode()
    if transfer!=expected:raise ValueError('Native failure transfer differs')
    if any(s in log for s in ('FAIL ','P2_POD_RECEIPT','P2_TREASURE_DELIVERED','P2_VIOLET_','P2_CAVE_TRANSFER')):
        raise ValueError('Unexpected failure or success/reward action')
    entry=f'P2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled'
    armed=f'P2_FLOOR3_FAILURE_ARMED token={token} reason={reason} active_descent_rejected=1'
    injected=f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0'
    failure=f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0'
    markers=[entry,armed,injected,failure]
    for prefix,expected_line in zip(('P2_BEASTS_ENTRY_READY','P2_FLOOR3_FAILURE_ARMED','P2_FLOOR3_FAILURE_INJECTED','P2_BEASTS_FAILURE'),markers):
        if [l for l in log.splitlines() if l.startswith(prefix)]!=[expected_line]:raise ValueError('Missing or conflicting native terminal marker')
    if [log.index(x) for x in markers]!=sorted(log.index(x) for x in markers):raise ValueError('Native terminal phases out of order')
    if log.count('P2_ROOM_CARGO_FREE_READY cargo=0')!=1 or re.findall(r'^P2_CAVE_READY floor=(\d+) ',log,re.M)!=['3']:
        raise ValueError('Missing terminal native readiness')
    counts=Counter(p['species'] for p in party['squad'])
    mapped=log.replace(armed,f'P2_BEASTS_READY reds={counts["red"]} flowers=0 cargo=0').replace(injected,'PASS P2_BEASTS_FAILURE_INJECTION')
    observed=party_snapshot(mapped,dict(red=counts['red'],purple=counts['purple'],sprouts=0),restored=True)
    if observed['squad']!=party['squad'] or not math.isclose(observed['health'],party['health'],rel_tol=1e-6):
        raise ValueError('Party differed before terminal injection')
    return dict(reason=reason,source_floor=3,destination=0,health=0,squad=[])


def run(exe,directory,timeout=90):
    if (directory/'native.log').exists() or (directory/'acceptance.json').exists():raise ValueError('Terminal run must be fresh')
    report=json.loads((directory/'survey.json').read_bytes());reason=report['terminal_fixture_reason'];token=report['boundary_token']
    inputs=dict(report['input_sha256']);inputs['survey.json']=sha((directory/'survey.json').read_bytes())
    for name,digest in inputs.items():
        if sha((directory/name).read_bytes())!=digest:raise ValueError('Terminal stage changed before launch')
    evidence=dict(schema=1,issue=324,policy='P2_BEASTS_FAILURE_1',reason=reason,token=token,passed=False,
        exe=str(exe),executable_sha256=sha(exe.read_bytes()),input_sha256=inputs)
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (directory/'native.log').open('w') as log:
        try:evidence['returncode']=subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:evidence['timeout']=True
    evidence['log_sha256']=sha((directory/'native.log').read_bytes())
    try:
        if evidence.get('returncode')!=42:raise ValueError('Native terminal process did not exit42')
        transfer=(directory/'p2-cave-transfer.txt').read_bytes();evidence['transfer_sha256']=sha(transfer)
        if (directory/'p2-cave-transfer.tmp').exists():raise ValueError('Native transfer temporary file remains')
        evidence['terminal']=validate((directory/'native.log').read_text(errors='replace'),transfer,token,reason,report['party'])
        if any(sha((directory/name).read_bytes())!=digest for name,digest in inputs.items()) or sha(exe.read_bytes())!=evidence['executable_sha256']:
            raise ValueError('Native terminal inputs/executable changed')
        evidence['passed']=True
    except (ValueError,OSError) as error:evidence['error']=str(error)
    from randomizer.session import atomic_write
    atomic_write(directory/'acceptance.json',json.dumps(evidence,indent=2)+'\n')
    if not evidence['passed']:raise ValueError(evidence['error'])
    return evidence
