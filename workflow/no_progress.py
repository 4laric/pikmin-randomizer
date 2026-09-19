"""No-progress guard: park lanes whose wakes bring nothing new after stalled generations.

A terminal outcome records the lane's substantive signal (state, root/native head, normalized
dependencies, handoff sha, integrated flag). stall_streak counts consecutive generations whose
signal equals the previous generation's; bind never resets it. Registry.plan_launch consults
verdict() for wake-type reasons only: at streak >= 2 a wake is admitted only with an input not
already offered since the lane last progressed, or once wake_after (exponential backoff) has
passed. Parking suppresses relaunch only; it never clears a dependency or infers resolution."""
from .control import fingerprint
from .handoff import Rejected

WAKES = ('consumer-prerequisite:', 'blocked-producer-followup:', 'blocked-recovery', 'shared-preflight-decision:',
         'autofill-planner:', 'integration-demand:', 'build-resource-available:', 'outcome-reconcile:',
         'shared-hook-decision:', 'handoff-representation:')
BASE_SECONDS, CAP_SECONDS, STALL, ASSESSED = 900, 4 * 3600, 2, 256


class Parked(Rejected):
    """A wake refused by the no-progress guard; the lane is parked, not failed."""


def guarded(reason):
    """Wake-type reasons; recovery continuations and operator/user reasons never match."""
    return isinstance(reason, str) and reason.startswith(WAKES)


def normalize(text):
    from .planner_demand import GEN
    return ' '.join(GEN.sub('gen', str(text)).casefold().split()).rstrip('.;, ')


def signal(lane):
    from .planner_demand import signal as demand_signal
    return dict(demand_signal(lane), dependencies=sorted({normalize(d) for d in lane.get('dependencies') or []}))


def record(reg, state, lane, outcome=None):
    """Terminal outcome: compare this generation's signal with the previous generation's.

    Only generations bound by guard-aware code (bound()) count toward the streak, so outcomes recorded
    while an older controller still binds cannot park a lane on the first tick after deploy. A
    'reconcile' (no terminal outcome) is neither progress nor a stall: signal and streak stay put."""
    if outcome == 'reconcile':
        return
    value = fingerprint(signal(lane))
    last = lane.get('progress_signal') or {}
    again = last.get('generation') == lane['generation']  # A repeated finish in one generation counts once.
    base, streak = ((last.get('baseline'), last.get('base_streak', 0)) if again else
                    (last.get('signal'), lane.get('stall_streak') or 0))
    same = base is not None and value == base
    stalled = same and lane.get('guarded_generation') == lane['generation']
    lane['stall_streak'] = streak + 1 if stalled else streak if same else 0
    lane['progress_signal'] = dict(generation=lane['generation'], signal=value, baseline=base,
                                   base_streak=streak, stalled=stalled, at=reg.clock())
    if stalled and not (again and last.get('stalled')):
        reg.event(state, 'no_progress_generation', lane['lane'], generation=lane['generation'],
                  stall_streak=lane['stall_streak'])
    if not same:  # Progress, launched or not: the lane is no longer parked.
        lane.pop('wake_inputs', None)
        lane.pop('wake_after', None)
        if lane.pop('parked', None) is not None:
            reg.event(state, 'lane_unparked', lane['lane'], reason='progress')


def backoff(streak):
    return min(CAP_SECONDS, BASE_SECONDS * 2 ** max(0, streak - STALL))


def verdict(lane, inputs, now):
    """None admits the wake; otherwise the refusal and the lane's wake_after."""
    streak = lane.get('stall_streak') or 0  # Lanes written before this guard read as streak 0.
    if streak < STALL:
        return None
    assessed = set(lane.get('wake_inputs') or [])
    if any(i not in assessed for i in inputs or []):
        return None
    after = lane.get('wake_after')
    if type(after) in (int, float) and now >= after:
        return None  # Periodic recheck: a missed input change cannot strand the lane.
    after = after if type(after) in (int, float) else now + backoff(streak)
    since = (lane.get('progress_signal') or {}).get('generation')
    return dict(wake_after=after, stall_streak=streak, message=(
        f'No progress since generation {since} (stall streak {streak}); parked until {int(after)} awaiting '
        'a new receipt, decision or pin change. Operator/user reasons and recovery continuations still launch.'))


def park(reg, state, lane, reason, refusal):
    first = lane.get('wake_after') != refusal['wake_after']
    lane['wake_after'] = refusal['wake_after']
    lane['parked'] = dict(at=reg.clock(), generation=lane['generation'], stall_streak=refusal['stall_streak'],
                          wake_after=refusal['wake_after'], reason=reason,
                          waiting_for='an input not among the %d already offered since the last progress'
                          % len(lane.get('wake_inputs') or []))
    if first:
        reg.event(state, 'lane_parked', lane['lane'], reason=reason, wake_after=refusal['wake_after'],
                  stall_streak=refusal['stall_streak'])


def admit(reg, state, lane, reason):
    if lane.pop('parked', None) is not None:
        reg.event(state, 'lane_unparked', lane['lane'], reason=reason)
    lane.pop('wake_after', None)


def bound(lane, launch):
    """A bound launch's inputs count as offered; the running lane is no longer parked."""
    offered = list(lane.get('wake_inputs') or [])
    offered += [i for i in launch.get('inputs') or [] if i not in offered]
    if offered:
        lane['wake_inputs'] = offered[-ASSESSED:]
    lane['guarded_generation'] = lane['generation']  # This generation's outcome may count as a stall.
    lane.pop('parked', None)
    lane.pop('wake_after', None)


def parked(state, now):
    """Visible parked lanes with the input each is waiting for."""
    return sorted((dict(lane=k, stall_streak=l.get('stall_streak'), wake_after=l.get('wake_after'),
                        due=type(l.get('wake_after')) in (int, float) and now >= l['wake_after'],
                        reason=l['parked'].get('reason'), waiting_for=l['parked'].get('waiting_for'))
                   for k, l in state.get('lanes', {}).items() if l.get('parked') and l.get('state') != 'done'),
                  key=lambda x: x['lane'])


def main(argv=None):
    """Read-only report: stall streaks and parked lanes of a registry, or of a copy anywhere via --db."""
    import argparse
    import json
    import sqlite3
    import time
    from pathlib import Path
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--root', type=Path, help='workspace whose output/workflow/registry.sqlite3 is read')
    parser.add_argument('--db', type=Path, help='any registry file (e.g. a copy); opened mode=ro, no workspace checks')
    args = parser.parse_args(argv)
    if args.db:
        from .storage import load
        db = sqlite3.connect('file:%s?mode=ro' % args.db.resolve().as_posix(), uri=True)
        try:
            db.execute('PRAGMA query_only=ON')
            state = load(db)[0]
        finally:
            db.close()
    else:
        from .registry import Registry
        if args.root is None: parser.error('--root or --db required')
        root = args.root.resolve()
        state = Registry(root / 'output/workflow/registry.sqlite3', root).snapshot()
    now = time.time()
    lanes = state['lanes']
    print(json.dumps(dict(lanes=len(lanes), recorded=sum('progress_signal' in l for l in lanes.values()),
                          stalled=sorted(k for k, l in lanes.items() if (l.get('stall_streak') or 0) >= STALL),
                          would_park=sorted(k for k, l in lanes.items() if l.get('state') != 'done' and
                                            verdict(l, [], now) is not None),
                          parked=parked(state, now)), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
