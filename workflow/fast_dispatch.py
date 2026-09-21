"""Single dispatch owner, independent of slow planning and reporting."""
import threading
import time
from .runner import write


def model_choices(controller, item):
    allowed = controller.config['models']
    control = controller.reg.control_status()
    launches = control['launches']
    current = item
    seen = set()
    while current['id'] not in seen:
        seen.add(current['id'])
        reason = current.get('reason', '')
        if reason.startswith('provider-stall:'):
            journal = control.get('provider_recoveries', {}).get(reason.split(':', 1)[1], {})
            previous = launches.get(journal.get('launch'))
        elif reason.startswith(('provider fallback:', 'provider-error:')):
            previous = launches.get(reason.split(':', 1)[1])
        else:
            break
        if not previous:
            break
        target = controller.config.get('provider_fallbacks', {}).get(previous.get('model'))
        if target:
            return [target] if target in allowed else []
        current = previous
    return list(dict.fromkeys([m for m in item['models'] if m in allowed] + allowed))


def run_cycle(controller, group='all'):
    from .abandoned_waiter import tick as cancel_waiters
    from .terminal_cleanup import tick as cleanup
    from .provider_recovery import recover_terminal
    from .throughput_controller import assign_pending, complete_pool_assignments
    from .review_decisions import tick as reviews
    from .resource_wakeup import tick as resources
    from .integration_repair import tick as repairs
    from .integration_wakeup import tick as integration
    from .helper_preparation import refresh_reservations
    from .worker_capacity import park_blocked
    steps=[('completion',controller.complete_runs),
           ('waiters',lambda:cancel_waiters(controller)),
           ('cleanup',lambda:cleanup(controller)),
           ('provider_recovery',lambda:recover_terminal(controller)),
           ('pool_completion',lambda:complete_pool_assignments(controller)),
           ('park_blocked',lambda:park_blocked(controller.reg)),
           ('helper_counts',lambda:refresh_reservations(controller.reg)),
           ('reviews',lambda:reviews(controller)),('resources',lambda:resources(controller)),
           ('handoff_repair',lambda:repairs(controller)),('integration',lambda:integration(controller)),
           ('assignment',lambda:assign_pending(controller)),
           ('dispatch',lambda:controller.dispatch_pending(min(4,max(1,int(controller.config.get('launches_per_tick',1))))))]
    if group!='all':
        steps=[(name,action) for name,action in steps if
               ('assignment' if name in ('helper_counts','park_blocked') else name if name in ('assignment','dispatch') else 'maintenance')==group]
    attribute='_dispatch_stage_health' if group=='all' else '_'+group+'_stage_health'
    target=controller.base/('dispatch-stage-health.json' if group in ('all','maintenance') else
                            'launcher-stage-health.json' if group=='dispatch' else 'assignment-stage-health.json')
    health=getattr(controller,attribute,{})
    for name,action in steps:
        before=time.monotonic();prior=health.get(name,{})
        health[name]=dict(prior,status='running',started_at=controller.reg.clock())
        write(target,dict(at=controller.reg.clock(),current_stage=name,stages=health),durable=False)
        try:
            action()
            health[name]=dict(status='ok',last_success=controller.reg.clock(),failures=0)
        except Exception as exc:
            health[name]=dict(status='error',last_success=prior.get('last_success'),
                failures=prior.get('failures',0)+1,error=str(exc),type=type(exc).__name__)
        health[name]['elapsed_seconds']=time.monotonic()-before
    setattr(controller,attribute,health)
    write(target,dict(at=controller.reg.clock(),stages=health),durable=False)


def start_monitor(controller):
    existing = getattr(controller, '_dispatch_monitor', None)
    if existing is not None:
        return existing
    stop = threading.Event()
    controller._dispatch_monitor = stop
    def monitor(group):
        from contextlib import nullcontext
        while not stop.is_set():
            started = time.monotonic()
            try:
                # Maintenance retains its lifecycle lock; the sole launcher and
                # assigner use durable transactional fences without waiting on it.
                with controller.lifecycle_lock if group=='maintenance' else nullcontext():
                    run_cycle(controller,group)
            except Exception as exc:
                write(controller.base / (group+'-monitor-error.json'),
                      dict(at=controller.reg.clock(), error=str(exc), type=type(exc).__name__))
            stop.wait(max(1, 5 - (time.monotonic() - started)))
    controller._dispatch_threads=[]
    for group in ('maintenance','assignment','dispatch'):
        thread=threading.Thread(target=monitor,args=(group,),name='worker-'+group,daemon=True)
        controller._dispatch_threads.append(thread)
        thread.start()
    return stop
