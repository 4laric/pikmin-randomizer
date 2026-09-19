"""One artifact-preserving reconciliation attempt per unchanged source pair."""
import copy
from .control import fingerprint
from .handoff import Rejected


def tick(controller):
    reg = controller.reg
    with reg.transaction() as state: state = copy.deepcopy(state)
    launches = list(state.get('control', {}).get('launches', {}).values())
    for key, lane in state['lanes'].items():
        if lane['state'] != 'reconciling' or key not in controller.config['lanes']: continue
        if lane.get('outcome', {}).get('summary') != 'Worker exited without terminal outcome; inspect existing artifacts before another attempt': continue
        token = 'outcome-reconcile:' + fingerprint([key, lane.get('root', {}).get('head'),
                                                   (lane.get('native') or {}).get('head')])
        if any(x['lane'] == key and (x['reason'] == token or x['status'] in ('intent','spawned','running','exiting')) for x in launches): continue
        if not reg.recovery_safe(state, lane) or not controller.available(key): continue
        try:
            reg.evidence(lane['outcome']['evidence'])
            reg.plan_launch(key, token,
                'OUTCOME RECONCILIATION: the previous runner exited without a terminal checkpoint. '
                'Inspect preserved private worktrees, uncommitted changes, logs and handoff artifacts first. '
                'Do not reset or duplicate them, rerun completed expensive work, or infer acceptance from exit. '
                'Repair any incomplete metadata using verified evidence and current generation. Continue '
                'the original owned slice only where needed. Submit a validated handoff if complete; '
                'otherwise checkpoint the exact remaining blocker and its producer. Preserve all review, '
                'build-lease and runtime gates. This automatic attempt is bounded for unchanged source pins.',
                controller.config['models'])
        except (Rejected, OSError, ValueError) as exc:
            reg.notice(key, 'outcome_recovery_blocked', {'error':str(exc)})
