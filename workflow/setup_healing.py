"""Bounded controller maintenance; never replaces a live lane or coordinator."""
import copy
import json
from .handoff import digest, Rejected
from .control import fingerprint


def dispose_claims(controller):
    from .planner_claims import release
    from .runner import write
    reg=controller.reg
    settings=controller.config.get('throughput', {}).get('autofill', {})
    from .autofill import _private
    manifest=json.loads(_private(reg, settings['manifest']).read_text(encoding='utf-8-sig'))
    published={x['id']:x for x in manifest['items']}
    with reg.transaction() as state:
        claims=copy.deepcopy(state.get('planning_claims', {}))
        decisions=copy.deepcopy(state.get('proposal_feedback', {}))
        lanes=copy.deepcopy(state['lanes'])
        identity=copy.deepcopy(state['control']['controller'])
    groups={}
    for key,claim in claims.items():groups.setdefault((claim['lane'],claim['generation']),[]).append(key)
    for (lane,generation),keys in groups.items():
        owner=lanes[lane]
        if owner['state'] not in ('done','review_ready'):continue
        if not lane.startswith('planning-shard-') or '-cycle-' not in lane:continue
        scope=lane[len('planning-shard-'):].rsplit('-cycle-',1)[0]
        inbox=reg.root/'output/workflow/autofill/planning-shards'/scope
        proposals=list(inbox.glob('proposals-*.json'))
        if not proposals:continue  # No-work claims still need coordinator adjudication.
        evidence=[]
        for path in proposals:
            sha=digest(path);decision=decisions.get(str(path))
            if decision and decision['sha256']==sha:
                reg.evidence(decision['evidence'])
                evidence.append(dict(path=str(path),sha256=sha,decision=decision));continue
            try:
                items=json.loads(path.read_text(encoding='utf-8-sig'))['items']
                if not items or not all(published.get(x.get('id'))==x for x in items):break
            except (ValueError,KeyError,TypeError,AttributeError):break
            evidence.append(dict(path=str(path),sha256=sha,decision='identical published specs'))
        else:
            report=reg.root/'output/workflow/controller/claim-dispositions'/f'{lane}-{generation}.json'
            report.parent.mkdir(parents=True,exist_ok=True)
            write(report,dict(lane=lane,generation=generation,proposals=evidence,
                              reason='All shard proposals published or explicitly dispositioned; release for repair/follow-up'))
            try:
                release(reg,lane,generation,keys,disposition=dict(path=str(report),sha256=digest(report)),coordinator=identity)
            except Rejected:pass  # Live/unknown owners, children or launches stay fenced.


def recover_setup(controller):
    reg=controller.reg
    with reg.transaction() as state:
        lanes=copy.deepcopy(state['lanes'])
    for key,lane in lanes.items():
        if lane['state']!='blocked' or lane.get('target_level')!='runtime':continue
        summary=lane.get('outcome',{}).get('summary','').lower()
        if not any(t in summary for t in ('native:null','no private native worktree','missing native worktree')):continue
        token=fingerprint([key,lane.get('root'),lane.get('native'),summary])
        with reg.transaction() as state:
            attempts=state.setdefault('setup_healing',{})
            if token in attempts:continue
            if not reg.recovery_safe(state,state['lanes'][key]):continue
        if key not in controller.config['lanes'] or not controller.available(key):continue
        instruction=('SETUP SELF-HEAL: resume this existing issue/owner and preserve all commits and dirty work. '
            'The prior blocked report describes missing native setup. Inspect CURRENT registry root/native records '
            'and actual private worktrees first; source may already have been provisioned since that report. '
            'If native is genuinely absent, create a new private native git worktree and codex/* branch under '
            'canonical output/ from the newest verified integration-approved native commit. Verify canonical native '
            'repository and pin; never edit shared native or research checkouts. Record source_record via your '
            'current-generation checkpoint before building, and update the assigned issue with pins and scope. '
            'Creating this private setup is authorized; missing worktree alone is not an external dependency. '
            'Use a private leased build directory and current aggregate heavy-build budget. Adopt mandatory '
            'starting-Pikmin overlay and 960x540 centred fixture, regenerate arena, record build hashes and '
            'ninja dry run. Continue original runtime acceptance; no invented PASS, ADMIT or shared-review bypass. '
            'If another concrete blocker exists, record its exact evidence. Do not recreate existing worktrees.')
        launch=reg.plan_launch(key,'setup-heal:'+token,instruction,controller.config['models'])
        with reg.transaction() as state:state.setdefault('setup_healing',{})[token]=dict(lane=key,launch=launch['id'],at=reg.clock())
        return


def tick(controller):
    if not controller.config.get('setup_healing',{}).get('enabled'):return
    for action in (dispose_claims,recover_setup):
        try:
            action(controller)
            with controller.reg.transaction() as state:
                state.setdefault('setup_healing_errors',{}).pop(action.__name__,None)
        except (Rejected,OSError,ValueError,KeyError,TypeError) as exc:
            with controller.reg.transaction() as state:
                state.setdefault('setup_healing_errors',{})[action.__name__]=str(exc)
