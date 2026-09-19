"""Bounded independent preparation; each completed job enqueues immediately."""
from concurrent.futures import ThreadPoolExecutor
import time
from .handoff import Rejected


def prepare_batch(controller, work, issue_reader, config, prepare):
    reg=controller.reg
    def one(entry):
        scope,spec=entry
        started=time.monotonic()
        error=None
        try:
            if not controller.capacity() or not 0<=controller.memory()<controller.config.get('ram_high',90):
                return False
            result=prepare(controller,spec,issue_reader)
            return result
        except (Rejected,OSError,ValueError,KeyError) as exc:
            error=str(exc)
            return False
        finally:
            with reg.transaction() as state:
                row=state['throughput_runtime']['autofill']['planner_pool']['scopes'].get(scope,{})
                if row.get('spec',{}).get('id')==spec['id']:
                    row['preparation']=dict(at=reg.clock(),elapsed_seconds=time.monotonic()-started)
                    if error:row['error']=error
                    else:row.pop('error',None)
    if not work:return []
    concurrency=min(4,max(1,int(config.get('preparation_concurrency',4))),len(work))
    with ThreadPoolExecutor(max_workers=concurrency,thread_name_prefix='helper-prepare') as executor:
        return list(executor.map(one,work))


def refresh_reservations(reg):
    """Fast current occupancy, without recomputing demand or waiting for refill."""
    with reg.transaction() as state:
        pool=state.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool')
        if pool is None:return
        counts=dict(running=0,queued=0,prepared=0,report_ready=0,recovery=0)
        support=0;recoveries=0
        for row in pool.get('scopes',{}).values():
            if 'completed_at' in row:continue
            lane=state['lanes'].get(row['spec']['lane']['lane'],{})
            status=lane.get('state')
            if status=='done':continue
            bucket={'running':'running','ready':'queued','review_ready':'report_ready',None:'prepared'}.get(status,'recovery')
            counts[bucket]+=1
            support+=bool(row.get('support_targets'))
            recoveries+=bool(row.get('prerequisite_recovery'))
        active=sum(counts.values());target=pool.get('target',0)
        pool.update(counts,active=active,integration_support_active=support,
                    discovery_active=active-support,recovery_active=recoveries,
                    draining=active>target,excess=max(0,active-target),counts_updated_at=reg.clock())
