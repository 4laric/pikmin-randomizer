"""Restartable engineering floor2 launcher. Floor3 remains a durable stop."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from experimental.pikmin2_beasts_exit_receiver import receive_exit
from experimental.pikmin2_beasts_floor2_runtime import run
from experimental.pikmin2_surface_ledger import _unique
from randomizer.session import SessionLock, atomic_write


def _save(path, request):
    atomic_write(path, json.dumps(request, indent=2, allow_nan=False)+'\n')


def _launchable(ledger, state):
    ledger._validate(state)
    if (state['campaign'] != ledger.campaign or state['content'] != ledger.content
            or state['schema'] != 2 or state['phase'] != 'cave'
            or state['trip']['checkpoint']['floor'] != 2):
        raise ValueError('Supervisor requires an active floor2 checkpoint')
    cp = state['trip']['checkpoint']
    flowers = [f'forest_1:floor2:BlackPom:{i}' for i in range(2)]
    if (cp['health'] != 1 or cp['squad'] != [dict(species='red', maturity=0)]*20
            or cp['context']['global_plus_cave_purple'] >= 20
            or set(cp['context']['spawned_flowers']) != set(flowers)):
        raise ValueError('Engineering fixture requires healthy twenty leaf Reds and both flowers')


def _receive(ledger, request):
    _launchable(ledger, request['launch_state'])
    stage = request['stage']
    if stage is None or not (Path(stage)/'acceptance.json').exists():
        return dict(status='pending_or_uncertain', native_relaunched=False,
                    stage=stage, state=ledger.read())
    state = receive_exit(ledger, request['launch_state'], stage)
    return dict(status='failed' if state['phase']=='failed' else 'floor3_stopped', native_relaunched=False,
                stage=stage, state=state, native_floor3_ready=False)


def supervise(ledger, *, root=None, assets=None, exe=None, output=None, timeout=240):
    """Start once, or receive the existing attempt. Reopen using just the ledger.

    The intent is diagnostic recovery metadata, never an authoritative save.
    Missing/failed evidence is not permission to launch again. An interrupted
    attempt needs investigation; this API deliberately has no reset/retry-launch.
    All users of this supervisor for a ledger share its fixed OS lock/intent.
    Other ledger writers still use revision/token validation at receive time.
    """
    directory = ledger.directory/'beasts-supervisor'
    with SessionLock(directory):
        path = directory/'request.json'
        if path.exists():
            request = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique)
            if (set(request) != {'schema', 'launch_state', 'stage'} or type(request['schema']) is not int
                    or request['schema'] != 1 or (request['stage'] is not None
                    and (not isinstance(request['stage'], str) or not Path(request['stage']).is_absolute()))):
                raise ValueError('Invalid supervisor request')
            return _receive(ledger, request)
        state = ledger.read()
        _launchable(ledger, state)
        if any(p is None for p in (root, assets, exe, output)):
            raise ValueError('First launch needs explicit root/assets/exe/output paths')
        if type(timeout) is not int or timeout <= 0:
            raise ValueError('Invalid native timeout')
        args = SimpleNamespace(root=Path(root), assets=Path(assets), exe=Path(exe), output=Path(output),
            timeout=timeout, global_purple_count=state['trip']['checkpoint']['context']['global_plus_cave_purple'],
            boundary_token=state['trip']['token'], exit_handoff=True, refund=False, restore_party=None)
        request = dict(schema=1, launch_state=deepcopy(state), stage=None)
        _save(path, request)

        def prepared(stage):
            if request['stage'] is not None:
                raise ValueError('Native stage already recorded')
            request['stage'] = str(Path(stage).resolve())
            _save(path, request)

        run(args, prepared=prepared)
        return _receive(ledger, request)
