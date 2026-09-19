"""Change-driven rechecks of verified no-work reports; heartbeat is not demand."""
import re

from .control import fingerprint
from .handoff import digest, local_path


def is_helper(key):
    return key.startswith(('planning-', 'publication-review-', 'integration-support-'))


def dispatch_priority(item, lanes, now, fairness_seconds=180):
    lane = lanes[item['lane']]
    work_class = 1 if item.get('work_class') == 'expansion' else 0
    focus = {'enemy_acceptance': 0, 'existing_content': 1, 'expansion': 2}.get(item.get('focus'), 1)
    if is_helper(item['lane']):
        if now - item['created_at'] >= max(60, fairness_seconds):
            return (1, 0, item['created_at'], 0, 0, 0)
        return (1, 1, work_class, focus, 0, item['created_at'])
    downstream = sum(item['lane'] in other.get('dependencies', []) for other in lanes.values()
                     if other['state'] != 'done')
    return (0, work_class, focus, -downstream, len(lane.get('closes_gates', [])) or 99, item['created_at'])


def inputs(state, issues, keys):
    def signal(lane):
        return dict(state=lane['state'] if lane['state'] in ('done', 'blocked', 'handoff_ready', 'review_ready') else 'pending',
                    root=(lane.get('root') or {}).get('head'), native=(lane.get('native') or {}).get('head'),
                    dependencies=sorted(lane.get('dependencies', [])),
                    handoff=(lane.get('handoff') or {}).get('sha256'),
                    integrated=bool(lane.get('integration')))
    return fingerprint({k:signal(l) for k,l in state['lanes'].items()
                        if not is_helper(k) and k != 'acceptance-backlog-planner'
                        and (not issues and not keys or l.get('issue') in issues or k in keys)})


def no_work_observation(reg, state, record):
    """Only an accepted, hash-verified report may suppress another model turn."""
    lane = state['lanes'].get(record['spec']['lane']['lane'], {})
    review = lane.get('review') or {}
    if lane.get('state') != 'done' or not lane.get('review_disposition'): return None
    if not re.search(r'\bno[- ]work\b|\bno (?:new )?proposals\b|\bno actionable', review.get('conclusion', ''), re.I):
        return None
    disposition = lane['review_disposition']
    evidence = disposition.get('archived_evidence') or review.get('evidence', {}).get('review')
    if not evidence: return None
    try:
        path = local_path(reg.root, evidence['path'])
        if digest(path) != evidence['sha256']: return None
        text = path.read_text(encoding='utf-8-sig')
    except (OSError, ValueError, KeyError):
        return None
    issues = sorted({int(n) for n in re.findall(r'#(\d+)\b', text)} - {lane.get('issue')})
    keys = sorted(k for k in state['lanes'] if not is_helper(k) and k != 'acceptance-backlog-planner'
                  and re.search(r'(?<![\w-])' + re.escape(k) + r'(?![\w-])', text))
    return dict(report=evidence, issues=issues, lanes=keys,
                snapshot=inputs(state, issues, keys), observed_at=reg.clock())


def demand(reg, state, record, recheck_seconds=3600):
    observation = record.get('no_work')
    if not observation: return True, 'Planning inputs not exhausted'
    if inputs(state, observation['issues'], observation['lanes']) != observation['snapshot']:
        return True, 'Recorded dependency inputs changed'
    if reg.clock() - record['completed_at'] >= max(300, recheck_seconds):
        return True, 'Periodic recheck for external issue changes'
    return False, 'Waiting for recorded dependency inputs to change'


def prerequisites(state, keys):
    """Explicit provider jobs outrank inferred references in narrative reports."""
    blockers, completed = [], {}
    for key in keys:
        lane = state['lanes'].get(key, {})
        accepted = lane.get('state') == 'done' and (lane.get('integration') or lane.get('review_disposition'))
        if not accepted:
            blockers.append(dict(lane=key, issue=lane.get('issue'), state=lane.get('state', 'awaiting admission'),
                                 owner=lane.get('owner'), next_action=lane.get('next_action')))
        else:
            completed[key] = dict(generation=lane.get('generation'), root=(lane.get('root') or {}).get('head'),
                                 native=(lane.get('native') or {}).get('head'))
    return not blockers, fingerprint(completed), blockers
