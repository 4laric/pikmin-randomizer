"""Bounded independent preparation; each completed job enqueues immediately."""
from concurrent.futures import ThreadPoolExecutor
import time
from .handoff import Rejected


def prepare_batch(controller, work, issue_reader, config, prepare):
    """Only an attempt that ran records a preparation and clears the scope's error; a skipped one
    records why and keeps the error. Every exception is recorded; non-domain ones re-raise, and a
    failed bookkeeping write never replaces the attempt's own exception."""
    reg=controller.reg
    def record(scope,spec,started,**fields):
        try:
            with reg.transaction(sections=()) as state:  # planner_pool lives in the meta row.
                row=state['throughput_runtime']['autofill']['planner_pool']['scopes'].get(scope,{})
                if row.get('spec',{}).get('id')!=spec['id']:return
                if 'skipped' in fields:
                    row['preparation_skipped']=dict(at=reg.clock(),reason=fields['skipped']);return
                row['preparation']=dict(at=reg.clock(),elapsed_seconds=time.monotonic()-started)
                row.pop('preparation_skipped',None)
                if fields.get('error'):row['error']=fields['error']
                else:row.pop('error',None)
        except Exception as exc:  # Bookkeeping only: log it beside the refill error file.
            from .runner import write
            write(controller.base/'helper-preparation-record-error.json',
                  dict(at=reg.clock(),scope=scope,error=str(exc),type=type(exc).__name__))
    def one(entry):
        scope,spec=entry
        started=time.monotonic()
        if not controller.capacity():
            record(scope,spec,started,skipped='capacity');return False
        if not 0<=controller.memory()<controller.config.get('ram_high',90):
            record(scope,spec,started,skipped='memory');return False
        try:
            result=prepare(controller,spec,issue_reader)
        except (Rejected,OSError,ValueError,KeyError) as exc:
            record(scope,spec,started,error=str(exc));return False
        except Exception as exc:
            record(scope,spec,started,error=type(exc).__name__+': '+str(exc));raise
        record(scope,spec,started)
        return result
    if not work:return []
    concurrency=min(4,max(1,int(config.get('preparation_concurrency',4))),len(work))
    with ThreadPoolExecutor(max_workers=concurrency,thread_name_prefix='helper-prepare') as executor:
        return list(executor.map(one,work))


def occupancy(pool, lanes):
    counts=dict(running=0,queued=0,prepared=0,report_ready=0,recovery=0)
    support=0;recoveries=0
    for row in pool.get('scopes',{}).values():
        if 'completed_at' in row:continue
        lane=lanes.get(row['spec']['lane']['lane']) or {}
        status=lane.get('state')
        if status=='done':continue
        bucket={'running':'running','ready':'queued','review_ready':'report_ready',None:'prepared'}.get(status,'recovery')
        counts[bucket]+=1
        support+=bool(row.get('support_targets'))
        recoveries+=bool(row.get('prerequisite_recovery'))
    active=sum(counts.values());target=pool.get('target',0)
    return dict(counts,active=active,integration_support_active=support,
                discovery_active=active-support,recovery_active=recoveries,
                draining=active>target,excess=max(0,active-target))


def refresh_reservations(reg):
    """Fast current occupancy, without recomputing demand or waiting for refill.

    Counted from a committed read; written (meta row plus the scopes' lanes) only when they change."""
    from .storage import selected
    seen=reg.snapshot(sections=[('lanes',)])
    pool=seen.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool')
    if pool is None:return
    values=occupancy(pool,seen['lanes'])
    if all(pool.get(k)==v for k,v in values.items()):return
    keys=sorted({row['spec']['lane']['lane'] for row in pool.get('scopes',{}).values() if 'completed_at' not in row})
    with selected(reg,[((),'')]+[(('lanes',),k) for k in keys]) as rows:
        pool=rows[((),'')].get('throughput_runtime',{}).get('autofill',{}).get('planner_pool')
        if pool is None:return
        if any(row['spec']['lane']['lane'] not in keys for row in pool.get('scopes',{}).values()
               if 'completed_at' not in row):return  # Scopes changed since the read; the next pass recounts.
        pool.update(occupancy(pool,{k:rows[(('lanes',),k)] for k in keys}),counts_updated_at=reg.clock())
