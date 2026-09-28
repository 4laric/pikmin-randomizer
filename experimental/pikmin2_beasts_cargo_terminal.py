"""Opt-in pre-receipt cargo terminal probes; never a campaign failure receiver."""
import json
import os
from pathlib import Path
import re
import subprocess
from experimental.pikmin2_beasts_floor3_failure_runtime import fixture as failure_fixture
from experimental.pikmin2_beasts_floor3_runtime import sha
from experimental.pikmin2_beasts_party_snapshot import party_snapshot

POLICY='P2_BEASTS_CARGO_FAILURE_DIAGNOSTIC_1'
EMPTY=b'P2_ECONOMY_1\n'


def enable(directory,reason=None,*,empty_ledger=False):
    if reason not in (None,'extinction','knockout'):raise ValueError('Unknown terminal reason')
    if any((directory/n).exists() for n in ('native.log','acceptance.json','p2-economy.txt','treasure-receipt.txt','p2-beasts-cargo-terminal.txt')):raise ValueError('Fresh pre-receipt stage required')
    path=directory/'survey.json';report=json.loads(path.read_bytes())
    if report['policy']!='P2_BEASTS_FLOOR3_HAUL_SURVEY_1' or report['replay'] or report['floor']!=3:raise ValueError('Expected fresh floor3 cargo haul stage')
    token=report['boundary_token']
    if not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Invalid native boundary token')
    overrides={'p2-beasts-cargo-terminal.txt':f'P2_BEASTS_CARGO_TERMINAL_1\n{token}\n'.encode()}
    if reason is not None:overrides['p2-floor3-failure-fixture.txt']=f'P2_FLOOR3_FAILURE_FIXTURE_1\n{reason}\n'.encode()
    if empty_ledger:overrides['p2-economy.txt']=EMPTY
    for name,raw in overrides.items():(directory/name).write_bytes(raw)
    report['input_sha256'].update({name:sha(raw) for name,raw in overrides.items()})
    report.update(cargo_terminal_enabled=True,pre_receipt_only=True,terminal_fixture_reason=reason)
    if reason is not None:report['policy']=POLICY
    report['limitations'].append('Only explicit pre-receipt floor3 cargo terminal readiness; no campaign authorization or successful descent.')
    path.write_text(json.dumps(report,indent=2)+'\n')


def fixture(source,output):
    failure_fixture(source,output);raw=output.read_text()
    gate='if(pc_p2_preview_cargo_free_ready())'
    cargo='require(pc_p2_preview_pokos()==0 && !pc_p2_preview_treasure(),"unexpected terminal reward/cargo");'
    if raw.count(gate)!=1 or raw.count(cargo)!=1:raise ValueError('Cargo terminal fixture anchors changed')
    replacement='''require(pc_p2_preview_ready() && pc_p2_preview_goal() && pc_p2_preview_cargo_count()==1 && pc_p2_preview_pokos()==0,"cargo terminal readiness");
    Pellet* treasure=pc_p2_preview_treasure();require(treasure && treasure->mGenerator && treasure->mGenerator->_70==63000,"cargo terminal source identity");
    require(treasure->mConfig->mCarryMinPikis()==12 && treasure->mConfig->mCarryMaxPikis()==20,"cargo terminal source settings");
    std::puts("P2_CARGO_FAILURE_OBSERVED generator=63000 value=150 weight=12 slots=20 pre_receipt=1");'''
    output.write_text(raw.replace(gate,'if(pc_p2_preview_ready())').replace(cargo,replacement));return output


def haul_fixture(source,output):
    from experimental.pikmin2_beasts_floor3_haul_runtime import fixture as prepare
    prepare(source,output);raw=output.read_text();marker='capture("floor3-haul-final.ppm");'
    if raw.count(marker)!=1:raise ValueError('Postreceipt fixture anchor changed')
    proof='''require(!gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && !playerState->mInDayEnd && (!gameflow.mMoviePlayer || !gameflow.mMoviePlayer->mIsActive),"postreceipt checkpoint timing blocked");
        const float savedHealth=n->mHealth;n->mHealth=0;
        require(!pc_p2_cave_checkpoint(false) && !pc_p2_cave_exit_after_checkpoint(),"postreceipt terminal lifecycle enabled");n->mHealth=savedHealth;
        std::puts("P2_CARGO_TERMINAL_POSTRECEIPT knockout_checkpoint_rejected=1 health_restored=1 pokos=150");
        '''
    output.write_text(raw.replace(marker,proof+marker));return output


def validate(log,transfer,token,reason,party):
    if not re.fullmatch('[0-9a-f]{64}',token) or reason not in ('extinction','knockout'):raise ValueError('Wrong terminal identity')
    if transfer!=f'P2_BEASTS_FAILURE_1\n{token}\n3 0 0 0\n{reason}\n'.encode():raise ValueError('Cargo failure transfer differs')
    if any(x in log for x in ('FAIL ','P2_POD_RECEIPT','P2_TREASURE_DELIVERED','P2_VIOLET_','P2_CAVE_TRANSFER','P2_ROOM_CARGO_FREE_READY')):raise ValueError('Unexpected reward/profile/failure')
    armed=f'P2_FLOOR3_FAILURE_ARMED token={token} reason={reason} active_descent_rejected=1'
    injected=f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0'
    markers=[f'P2_BEASTS_CARGO_TERMINAL_READY floor=3 token={token} cargo=1 pokos=0 diagnostic=1',
        f'P2_BEASTS_ENTRY_READY floor=3 token={token} descent=disabled',
        'P2_CARGO_FAILURE_OBSERVED generator=63000 value=150 weight=12 slots=20 pre_receipt=1',armed,injected,
        f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0']
    for line in markers:
        prefix=line.split(' ')[0]
        if [x for x in log.splitlines() if x.startswith(prefix)]!=[line]:raise ValueError('Missing or conflicting cargo failure phase')
    if [log.index(x) for x in markers]!=sorted(log.index(x) for x in markers):raise ValueError('Cargo failure phases reordered')
    if [x for x in log.splitlines() if x.startswith('P2_CAVE_READY ')]!=['P2_CAVE_READY floor=3 survivors=20 health=1']:raise ValueError('Wrong native restored party')
    mapped=log.replace(armed,'P2_BEASTS_READY reds=20 flowers=0 cargo=1').replace(injected,'PASS P2_BEASTS_FAILURE_INJECTION')
    observed=party_snapshot(mapped,dict(red=20,purple=0,sprouts=0),restored=True)
    if observed!=party:raise ValueError('Pre-injection party differs')
    return dict(reason=reason,source_floor=3,destination=0,health=0,squad=[],diagnostic_only=True)


def run(exe,directory,timeout=90):
    if any((directory/n).exists() for n in ('native.log','acceptance.json','treasure-receipt.txt')):raise ValueError('Fresh terminal stage required')
    report=json.loads((directory/'survey.json').read_bytes())
    if report['policy']!=POLICY or not report.get('pre_receipt_only'):raise ValueError('Wrong cargo failure policy')
    inputs=dict(report['input_sha256']);inputs['survey.json']=sha((directory/'survey.json').read_bytes())
    economy=directory/'p2-economy.txt';before=economy.read_bytes() if economy.exists() else None
    if before not in (None,EMPTY):raise ValueError('Pre-receipt economy required')
    if any(sha((directory/n).read_bytes())!=h for n,h in inputs.items()):raise ValueError('Cargo terminal stage changed')
    result=dict(issue=356,policy=POLICY,passed=False,reason=report['terminal_fixture_reason'],token=report['boundary_token'],
        input_sha256=inputs,executable_sha256=sha(exe.read_bytes()),initial_economy_sha256=sha(before) if before is not None else None)
    env=dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (directory/'native.log').open('w') as log:
        try:result['returncode']=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:result['timeout']=True
    result['log_sha256']=sha((directory/'native.log').read_bytes())
    try:
        if result.get('returncode')!=42:raise ValueError('Native cargo failure did not exit42')
        transfer=(directory/'p2-cave-transfer.txt').read_bytes();result['transfer_sha256']=sha(transfer)
        result['terminal']=validate((directory/'native.log').read_text(errors='replace'),transfer,result['token'],result['reason'],report['party'])
        if (economy.read_bytes() if economy.exists() else None)!=before or (directory/'treasure-receipt.txt').exists():raise ValueError('Cargo failure changed economy/receipt')
        if any((directory/n).exists() for n in ('p2-cave-transfer.tmp','p2-economy.txt.tmp')):raise ValueError('Unexpected temporary state')
        if any(sha((directory/n).read_bytes())!=h for n,h in inputs.items()) or sha(exe.read_bytes())!=result['executable_sha256']:raise ValueError('Cargo terminal inputs/executable changed')
        result['passed']=True
    except (ValueError,OSError) as error:result['error']=str(error)
    (directory/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['passed']:raise ValueError(result['error'])
    return result
