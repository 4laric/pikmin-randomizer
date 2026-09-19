"""Retire completed OpenCode turns whose service remains alive after exit-loop."""
import copy
import json
import os
import subprocess
from datetime import datetime
from .handoff import digest, Rejected
from .processes import identify
from .runner import write


def finished_loop(log, session, now, grace):
    lines=log.splitlines()
    exits=[i for i,line in enumerate(lines) if 'message="exiting loop"' in line and 'session.id='+session in line]
    if not exits:return False
    last=exits[-1]
    try: at=datetime.fromisoformat(lines[last].split('timestamp=',1)[1].split()[0].replace('Z','+00:00')).timestamp()
    except (ValueError,IndexError):return False
    # Anything other than routine service cleanup after completion is uncertain.
    return now-at>=grace and all('message=cleanup ' in line or not line.strip() for line in lines[last+1:])


def process_inventory():
    if os.name!='nt':return None
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',
        'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress'],
        capture_output=True,text=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:return None
    return json.loads(result.stdout)


def idle_tree(rows, runner, child):
    if not isinstance(rows,list):return False
    indexed={p['ProcessId']:p for p in rows}
    if child not in indexed or runner not in indexed:return False
    if indexed[child]['ParentProcessId']!=runner or indexed[child]['Name'].lower()!='opencode.exe':return False
    family={runner}
    while True:
        more={p['ProcessId'] for p in rows if p['ParentProcessId'] in family}
        if more<=family:break
        family |= more
    return all(indexed[p]['Name'].lower()=='conhost.exe' for p in family-{runner,child})


def terminate_exact(identity):
    # Query creation time and terminate through the SAME Windows handle.
    import ctypes
    from ctypes import wintypes
    if os.name!='nt' or identify(identity['pid'])!=identity:return False
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
    k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
    k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];k.CloseHandle.argtypes=[wintypes.HANDLE]
    h=k.OpenProcess(0x1001,False,identity['pid'])
    if not h:return False
    try:
        times=[wintypes.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(h,*(ctypes.byref(t) for t in times)):return False
        started=str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
        return started==identity['started'] and bool(k.TerminateProcess(h,15))
    finally:k.CloseHandle(h)


def tick(controller, inventory=process_inventory, terminate=terminate_exact):
    cfg=controller.config.get('terminal_cleanup',{})
    if not cfg.get('enabled'):return
    reg=controller.reg
    release_terminal_builds(reg)
    launches=reg.snapshot().get('control',{}).get('launches',{})
    for identity,launch in launches.items():
        if launch['status']!='running' or not launch.get('bound_generation'):continue
        out=controller.launch_directory(identity)
        try:
            child=json.loads((out/'child.json').read_text())
            log=(out/'stderr.log').read_text(encoding='utf-8',errors='replace')
            if not finished_loop(log,launch['session'],reg.clock(),max(30,cfg.get('grace_seconds',300))):continue
            rows=inventory()
            with reg.transaction() as s:
                current=s['control']['launches'][identity];lane=s['lanes'][launch['lane']]
                if current!=launch or lane['generation']!=launch['bound_generation']:continue
                if lane['state'] not in ('handoff_ready','review_ready','blocked'):continue
                if reg.probe(lane['process'])!='alive' or lane['process']!=launch['process']:continue
                if reg.probe(child)!='alive' or not idle_tree(rows,lane['process']['pid'],child['pid']):continue
                if any(v['lane']==lane['lane'] and v['process']!=lane['process'] and reg.probe(v['process'])!='dead'
                       for collection in ('leases','queue') for v in s[collection].values()):continue
                if lane['state']=='handoff_ready':
                    reg.check_handoff(lane)
                    evidence={k:lane['handoff'][k] for k in ('path','sha256')}
                elif lane['state']=='review_ready':
                    evidence=lane['review']['evidence']['review'];reg.evidence(evidence)
                else:
                    if (lane.get('outcome') or {}).get('outcome')!='blocked':continue
                    evidence=lane['outcome']['evidence'];reg.evidence(evidence)
                # Reject activity that appeared while inspecting the process tree.
                if (out/'stderr.log').read_text(encoding='utf-8',errors='replace')!=log:continue
                report=dict(at=reg.clock(),lane=lane['lane'],generation=lane['generation'],launch=identity,
                    child=child,evidence=evidence,log_sha256=digest(out/'stderr.log'),reason='Verified terminal turn lingering after exit-loop')
                write(out/'terminal-cleanup.json',report)
                if terminate(child):
                    s.setdefault('terminal_cleanup',{})[identity]=report
                    reg.event(s,'terminal_process_retired',lane['lane'],launch=identity)
        except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
            continue  # Unknown state never authorizes a stop.


def release_terminal_builds(reg):
    """Use the normal dead-owner release API; a TTL is not a minimum hold time."""
    state=reg.snapshot()
    leases=state['leases']
    for resource, lease in leases.items():
        if not resource.startswith('build:'): continue
        # Snapshot eligibility; the normal release API rechecks generation,
        # token ownership and confirmed process death under its own transaction.
        lane=state['lanes'].get(lease['lane'],{})
        eligible=(lane.get('state') in ('done','blocked','handoff_ready','review_ready')
                  and lane.get('generation') == lease.get('generation')
                  and reg.probe(lease['process']) == 'dead')
        if not eligible: continue
        try:
            reg.release(lease['lane'],lease['generation'],resource,lease['token'])
        except (Rejected,OSError,KeyError):
            continue  # Generation/token/identity changes stay protected.
