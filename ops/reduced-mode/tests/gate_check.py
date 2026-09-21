"""TEST ONLY (scratch registry): run every wake gate once and list the launch intents it plans.
Usage: py -3.12 gate_check.py <scratch root> [--keep-from reduced-lanes.patch.json]"""
import json, sys, traceback
from pathlib import Path
RELEASE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RELEASE))
from workflow.registry import Registry
from workflow.controller import Controller

root = Path(sys.argv[1]).resolve()
keep = set(json.loads((Path(__file__).resolve().parents[1] / 'reduced-lanes.patch.json').read_text())['lanes'])
reg = Registry(root / 'output/workflow/registry.sqlite3', root)
config = json.loads((root / 'output/workflow/controller/config.json').read_text(encoding='utf-8-sig'))
stops = []
def no_spawn(d): raise RuntimeError('spawn blocked in test')
c = Controller(reg, config, spawn=no_spawn)
c.config['lanes'].update(reg.snapshot(sections=[('throughput_runtime', 'launch_specs')]).get('throughput_runtime', {}).get('launch_specs', {}))
print('configured lanes:', len(c.config['lanes']))
before = set(reg.control_status()['launches'])
state = reg.snapshot()
from workflow import consumer_wakeup
verdicts = {}
links = consumer_wakeup.linked(reg, state)
launches = state.get('control', {}).get('launches', {}).values()
for k, l in state['lanes'].items():
    if l['state'] == 'blocked' and k not in keep:
        g = consumer_wakeup.gate(reg, state, k, configured=c.config['lanes'], available=lambda key: True, links=links,
                                 launches=launches, umbrella=set(consumer_wakeup.UMBRELLA_ISSUES), debounce=consumer_wakeup.DEBOUNCE_SECONDS)
        verdicts[g['gate']] = verdicts.get(g['gate'], 0) + 1
print('consumer_wakeup.gate verdicts for blocked non-reduced lanes:', verdicts)
from workflow import (integration_wakeup, approvals, outcome_recovery, provider_recovery, resource_wakeup, action_routing,
                      handoff_representation, integration_repair, shared_decisions, blocked_followup, setup_healing)
gates = [('Controller.dependencies', c.dependencies), ('consumer_wakeup', lambda: consumer_wakeup.tick(c)),
         ('integration_wakeup', lambda: integration_wakeup.tick(c)), ('approvals', lambda: approvals.tick(c)),
         ('outcome_recovery', lambda: outcome_recovery.tick(c)),
         ('provider_recovery', lambda: provider_recovery.recover(c, stop=lambda *a, **k: stops.append(a))),
         ('resource_wakeup', lambda: resource_wakeup.tick(c)), ('action_routing', lambda: action_routing.tick(c)),
         ('handoff_representation', lambda: handoff_representation.tick(c)), ('integration_repair', lambda: integration_repair.tick(c)),
         ('shared_decisions', lambda: shared_decisions.tick(c)), ('blocked_followup', lambda: blocked_followup.tick(c)),
         ('setup_healing', lambda: setup_healing.tick(c))]
for name, fn in gates:
    try:
        fn(); print(f'{name}: ran')
    except Exception as e:
        print(f'{name}: EXCEPTION {type(e).__name__}: {e}')
after = reg.control_status()['launches']
new = {i: after[i] for i in set(after) - before}
old = sorted({v['lane'] for v in new.values() if v['lane'] not in keep})
print('new intents:', len(new), 'for non-reduced lanes:', old)
print('reduced-lane intents:', sorted({v['lane'] for v in new.values() if v['lane'] in keep}))
print('pending intents/spawned of non-reduced lanes:', [(v['lane'], v['status']) for v in after.values()
      if v['status'] in ('intent', 'spawned') and v['lane'] not in keep])
print('process stops requested:', stops)
sys.exit(1 if old else 0)
