"""Cancel proven abandoned sleep-only requests; never terminate their processes."""
import json
import re
from .processes import identify
from .terminal_cleanup import process_inventory, finished_loop, idle_tree
from .handoff import Rejected


def sleep_only(rows, identity):
    if not isinstance(rows,list):return False
    row=next((r for r in rows if r.get('ProcessId')==identity['pid']),None)
    if not row or any(r.get('ParentProcessId')==identity['pid'] for r in rows):return False
    if not re.fullmatch(r'python(?:\d+(?:\.\d+)*)?\.exe',row.get('Name',''),re.I):return False
    command=row.get('CommandLine') or ''
    return bool(re.fullmatch(r'(?:"[^"\r\n]*[\\/]python(?:\d+(?:\.\d+)*)?\.exe"|[^\s"]*[\\/]python(?:\d+(?:\.\d+)*)?\.exe)\s+-c\s+"import time;\s*time\.sleep\([1-9][0-9]*\)"\s*',command,re.I))


def tick(controller, inventory=process_inventory, identity_reader=identify):
    if not controller.config.get('terminal_cleanup',{}).get('enabled'):return
    reg=controller.reg;state=reg.snapshot()
    requests=[q for q in state['queue'].values() if q['resource'].startswith('build:') and
              state['lanes'].get(q['lane'],{}).get('state')=='blocked']
    if not requests:return
    rows=inventory()
    for request in requests:
        try:
            owner=request['process']
            if not sleep_only(rows,owner) or identity_reader(owner['pid'])!=owner:continue
            for launch in state.get('control',{}).get('launches',{}).values():
                if launch['lane']!=request['lane'] or launch['status']!='running':continue
                out=controller.launch_directory(launch['id'])
                log=(out/'stderr.log').read_text(encoding='utf-8',errors='replace')
                grace=max(30,controller.config['terminal_cleanup'].get('grace_seconds',300))
                if not finished_loop(log,launch['session'],reg.clock(),grace):continue
                child=json.loads((out/'child.json').read_text())
                with reg.transaction() as current:
                    lane=current['lanes'][request['lane']]
                    if current['queue'].get(request['id'])!=request:continue
                    if current['control']['launches'].get(launch['id'])!=launch:continue
                    if lane['state']!='blocked' or lane['generation']!=request['generation']:continue
                    if launch.get('bound_generation')!=lane['generation'] or launch.get('process')!=lane['process']:continue
                    if (lane.get('outcome') or {}).get('outcome')!='blocked':continue
                    if request['requested_at']>lane['progress_at']:continue
                    reg.evidence(lane['outcome']['evidence'])
                    if owner==lane['process'] or reg.probe(owner)!='alive':continue
                    if any(v['process']==owner for v in current['leases'].values()):continue
                    if not idle_tree(rows,lane['process']['pid'],child['pid']):continue
                    if reg.probe(lane['process'])!='alive' or reg.probe(child)!='alive':continue
                    if identity_reader(owner['pid'])!=owner or not sleep_only(inventory(),owner):continue
                    if (out/'stderr.log').read_text(encoding='utf-8',errors='replace')!=log:continue
                    del current['queue'][request['id']]
                    reg.event(current,'request_cancelled',lane['lane'],resource=request['resource'],
                        wait_seconds=reg.clock()-request['requested_at'],process=owner,
                        reason='Verified terminal producer abandoned a sleep-only build waiter; process left to exit naturally')
                break
        except (Rejected,OSError,ValueError,KeyError,TypeError):continue
