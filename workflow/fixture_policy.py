"""Durable active-lane adoption requests; never edit a running fixture's source."""
from pathlib import Path
from .handoff import local_path

POLICY = '''Captain safety adoption required before the next runtime acceptance run (#632).
Read canonical docs/PIKMIN2_IMPLEMENTATION_FANOUT.md, mandatory captain safety section.
Adopt scripts/p2_fixture_captain_guard.h (or tested equivalent) in your owned fixture;
check orimaDead, NaviDead and HP<=1 before pause/movie returns or observation ticks.
CAPTAIN_DOWN exits BLOCKED; no blanket invincibility. Park captain outside attack
reach only when captain damage is not the subject. Preserve commits and earlier
successful evidence; rebuild privately under leases and record guard/source/exe hashes.
Fresh runtime handoff fixture_adoption.captain_safety must contain policy
(unprotected or protected_observation) and evidence (keys in the hashed evidence map),
covering guarded source, negative guard test and fresh run. Protected observations
cannot claim attacks_receivers PASS. Current unguarded runs are diagnostic until
reviewed; do not claim retrofit adoption. Finish with honest outcome then exit.
'''

def tick(controller):
    if not controller.config.get('fixture_captain_safety',{}).get('enabled'):return
    reg=controller.reg
    with reg.transaction() as s:
        for key,lane in s['lanes'].items():
            if lane['state'] not in ('ready','running','blocked','reconciling','waiting_resource'):continue
            if not lane.get('native') and lane.get('target_level')!='runtime':continue
            if lane.get('target_level')=='integration ownership':continue
            if key not in controller.config['lanes']:continue
            lane['fixture_captain_guard_required']=True
            token=key+'-'+str(lane['generation'])
            ledger=s.setdefault('fixture_captain_policy',{})
            if token in ledger:continue
            path=local_path(reg.root,controller.config['lanes'][key]['output'])/'captain-safety-required.md'
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(POLICY,encoding='utf-8')
            inbox=local_path(reg.root,controller.config['integrator_inbox'])/('captain-safety-'+token+'.md')
            inbox.write_text('directive: NOTE\nLane '+key+' / issue #'+str(lane['issue'])+' / generation '+str(lane['generation'])+'\n'+POLICY+'\nIntegrator: require adoption evidence before fresh runtime acceptance; route incomplete adoption to the same owner.\n',encoding='utf-8')
            ledger[token]=dict(lane=key,generation=lane['generation'],at=reg.clock(),status='adoption_required',path=str(path))
