"""One-attempt floor3 terminal engineering supervisor; no player campaign launch."""
from copy import deepcopy
import json
from pathlib import Path

from experimental.pikmin2_beasts_exit_receiver import sha
from experimental.pikmin2_beasts_failure import receive_failure
from experimental.pikmin2_beasts_floor3_entry import entry_text
from experimental.pikmin2_beasts_floor3_failure_runtime import run
from experimental.pikmin2_surface_ledger import _unique
from randomizer.session import SessionLock,atomic_write


def _read(path):return json.loads(path.read_bytes(),object_pairs_hook=_unique)


def _receive(ledger,request):
    if (set(request)!={'schema','launch_state','stage','exe','survey_sha256','executable_sha256'}
            or type(request['schema']) is not int or request['schema']!=1):
        raise ValueError('Invalid floor3 supervisor intent')
    stage=Path(request['stage']);exe=Path(request['exe']);state=request['launch_state']
    ledger._validate(state)
    if (state['campaign']!=ledger.campaign or state['content']!=ledger.content or state['schema']!=2
            or state['phase']!='cave' or state['trip']['checkpoint']['floor']!=3
            or not stage.is_absolute() or not exe.is_absolute()):
        raise ValueError('Invalid original floor3 launch')
    if sha(stage/'survey.json')!=request['survey_sha256'] or sha(exe)!=request['executable_sha256']:
        raise ValueError('Floor3 launch inputs changed')
    if not (stage/'acceptance.json').exists():
        return dict(status='pending_or_uncertain',stage=str(stage),native_relaunched=False,state=ledger.read())
    evidence=_read(stage/'acceptance.json')
    if (evidence.get('exe')!=str(exe) or evidence.get('executable_sha256')!=request['executable_sha256']
            or evidence.get('input_sha256',{}).get('survey.json')!=request['survey_sha256']):
        raise ValueError('Failure evidence belongs to another launch')
    return dict(status='failed',stage=str(stage),native_relaunched=False,state=receive_failure(ledger,state,stage))


def supervise(ledger,*,stage=None,exe=None,timeout=90):
    """Prepare the bound terminal fixture separately; this API launches at most once.

    Reopen with just the ledger to receive an existing run. Missing acceptance is
    uncertain, never permission to launch again. This intentionally induces a
    fixture failure, not a natural-play or general floor3 launcher.
    """
    directory=ledger.directory/'beasts-supervisor'
    with SessionLock(directory):
        path=directory/'floor3-request.json'
        if path.exists():return _receive(ledger,_read(path))
        state=ledger.read()
        if (state['schema']!=2 or state['phase']!='cave' or state['trip']['checkpoint']['floor']!=3):
            raise ValueError('Supervisor requires active floor3')
        if stage is None or exe is None or type(timeout) is not int or timeout<=0:
            raise ValueError('First launch needs stage/executable and positive timeout')
        stage=Path(stage).resolve();exe=Path(exe).resolve()
        if any((stage/name).exists() for name in ('native.log','acceptance.json','p2-cave-transfer.txt','p2-cave-transfer.tmp')):
            raise ValueError('Floor3 stage must be unused')
        report=_read(stage/'survey.json');cp=state['trip']['checkpoint'];token=state['trip']['token']
        if (_read(stage/'checkpoint.json')!=cp or report.get('boundary_token')!=token
                or report.get('policy')!='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1'
                or report.get('terminal_fixture_reason') not in ('extinction','knockout')
                or (stage/'p2-cave-entry.txt').read_text()!=entry_text(dict(health=cp['health'],squad=cp['squad']),token)):
            raise ValueError('Floor3 stage does not match current checkpoint')
        request=dict(schema=1,launch_state=deepcopy(state),stage=str(stage),exe=str(exe),
                     survey_sha256=sha(stage/'survey.json'),executable_sha256=sha(exe))
        atomic_write(path,json.dumps(request,indent=2,allow_nan=False)+'\n')
        run(exe,stage,timeout)
        return _receive(ledger,request)
