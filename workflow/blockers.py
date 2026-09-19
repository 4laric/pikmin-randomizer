"""Structured blocker references: dependency prose, producer links and classifications as issue/lane refs.

Pure over one registry state and read-only: a ref is 'issue:N' ('#N' and REPO#N alike),
'external:<owner/repo>#N' (another repository's issue), 'lane:<key>' or 'user:<lane>' (an open
user-owned external ask). Each ref resolves to its owning lane and that lane's state; groups cluster
blocked lanes on their resolved owner and follow blocked owners to their roots. Nothing here clears,
links or wakes anything; the prose stays the record."""
import re

ISSUE = re.compile(r'(?<!\w)(?:([\w.-]+/[\w.-]+))?#(\d+)\b')
REPO = '4laric/pikmin-randomizer'  # Qualified refs to this repository are local issues.
TOKEN = re.compile(r'[A-Za-z0-9][\w-]*')
WAITING = ('blocked', 'waiting_resource')
LIVE = ('ready', 'running', 'waiting_resource', 'reconciling')
HANDOFF = ('handoff_ready', 'integrating', 'review_ready')
ASKED = WAITING + ('handoff_ready', 'integrating')  # States a support worker may record a user ask against.
DECISIONS = (186,)  # Shared-hook decision issues: no producer lane owns them, a reviewer decides.
POLICY = (632,)  # Standing policy cited by many lanes (captain safety); never a blocker.


def issues(text):
    """Local issue numbers: '#N' and REPO#N, never another repository's."""
    return sorted({int(n) for repo, n in ISSUE.findall(str(text)) if not repo or repo.casefold() == REPO})


def external(text):
    """'owner/repo#N' refs to other repositories; no local lane owns them."""
    return sorted({'%s#%s' % (repo, n) for repo, n in ISSUE.findall(str(text)) if repo and repo.casefold() != REPO})


def asked(action, lane):
    """A user ask the lane still waits on: it waits now, at the generation the ask targeted (legacy rows
    without a target generation count as current). A relaunched lane's older asks are superseded."""
    generation = (action.get('target') or {}).get('generation', (lane or {}).get('generation'))
    return bool(lane) and lane.get('state') in ASKED and generation == lane.get('generation')


def owners(state):
    """{issue: [lane keys]}, most actionable owner first: live, handoff, done but unlanded, blocked,
    landed; newest first within each."""
    rank = dict(live=0, handoff=1, done_unlanded=2, blocked=3, landed=4)
    table = {}
    for key, lane in state.get('lanes', {}).items():
        if type(lane.get('issue')) is int: table.setdefault(lane['issue'], []).append(key)
    lanes = state.get('lanes', {})
    for keys in table.values():
        keys.sort(key=lambda k: (rank.get(standing(lanes[k]), 5), -(lanes[k].get('created_at') or 0), k))
    return table


def standing(lane):
    """live | blocked | handoff | done_unlanded | landed | missing."""
    if not lane: return 'missing'
    state = lane.get('state')
    if state in LIVE: return 'live'
    if state in HANDOFF: return 'handoff'
    if state == 'done': return 'landed' if lane.get('integration') else 'done_unlanded'
    return 'blocked' if state == 'blocked' else str(state)


def refs(state, key, table=None, decisions=DECISIONS):
    """Sorted structured refs of one lane: its dependency text, current-pin producer link, the
    classification of its current snapshot, structured shared_hooks and open user-owned asks.
    A lane's reference to its own issue or name is not a blocker and is dropped."""
    lanes = state.get('lanes', {})
    lane = lanes.get(key) or {}
    found = set()
    for text in lane.get('dependencies') or []:
        found.update('issue:%d' % n for n in issues(text) if n not in POLICY)
        found.update('external:' + r for r in external(text))
        found.update('lane:' + t for t in TOKEN.findall(str(text)) if t in lanes)
    link = state.get('blocked_producer_links', {}).get(key) or {}
    if link.get('source_pins') == {k: (lane.get(k) or {}).get('head') for k in ('root', 'native')}:
        found.update('lane:' + p for p in link.get('producers', []) if p in lanes)
    for hook in lane.get('shared_hooks') or []:
        if type(hook.get('issue')) is int: found.add('issue:%d' % hook['issue'])
    classified = classification(state, key)
    contracts, actions = state.get('delivery_contracts', {}), state.get('support_actions', {})
    for d in (classified or {}).get('dispositions', []):
        contract = contracts.get(d.get('contract_id')) or {}
        action = actions.get(d.get('action_id')) or {}
        internal = d.get('internal_blocker') or {}
        if contract.get('producer') in lanes: found.add('lane:' + contract['producer'])
        if internal.get('owner_lane') in lanes: found.add('lane:' + internal['owner_lane'])
        if action.get('action') == 'producer' and (action.get('details') or {}).get('lane') in lanes:
            found.add('lane:' + action['details']['lane'])
    if any(a.get('action') == 'external' and a.get('key') == key and asked(a, lane) for a in actions.values()):
        found.add('user:' + key)
    own = {'lane:' + key} | ({'issue:%d' % lane['issue']} if type(lane.get('issue')) is int else set())
    return sorted(found - own)


def classification(state, key):
    """The dependency classification recorded for the lane's current snapshot, else None."""
    from .dependency_classification import signature
    lane = state.get('lanes', {}).get(key)
    if not lane: return None
    try: snapshot = signature(lane)
    except (TypeError, ValueError, KeyError): return None
    rows = [r for r in state.get('dependency_classifications', {}).values()
            if r.get('consumer') == key and r.get('snapshot') == snapshot]
    return max(rows, key=lambda r: r.get('at', 0), default=None)


def owner(state, ref, table, decisions=DECISIONS):
    """(owning lane key or None, standing) of one ref; decision issues and user asks have no lane owner,
    and no local lane owns another repository's issue ('missing')."""
    kind, _, name = ref.partition(':')
    if kind == 'user': return None, 'user'
    if kind == 'external': return None, 'missing'
    if kind == 'lane': return name, standing(state['lanes'].get(name))
    if int(name) in decisions: return None, 'decision'
    keys = table.get(int(name)) or []
    return (keys[0], standing(state['lanes'][keys[0]])) if keys else (None, 'missing')


def label(ref):
    kind, _, name = ref.partition(':')
    return '#' + name if kind == 'issue' else 'you (asked by %s)' % name if kind == 'user' else name


def action(ref, owner_key, standing_, waits_on, count):
    """(accountable, the one next action) for a group of `count` lanes blocked on ref."""
    name, lanes = label(ref), '%d lane%s' % (count, '' if count == 1 else 's')
    if standing_ == 'decision':
        return 'reviewer', ('Record the %s shared-hook decision for these %s (approvals shared-hook from a reviewer '
                            'lane, or review_packet request against a committed packet)' % (name, lanes))
    if standing_ == 'user': return 'user', 'Answer the open ask in Needs you'
    if standing_ == 'missing':
        return 'planner', 'No lane owns %s: publish or link a producer (prerequisite_queue / delivery_contracts)' % name
    if standing_ == 'live': return 'producer', '%s is running; nothing to do unless it stalls (inspect lane %s)' % (owner_key, owner_key)
    if standing_ == 'handoff': return 'integrator', 'Integrator: land %s\'s handoff; %s wait on it' % (owner_key, lanes)
    if standing_ == 'done_unlanded':
        return 'integrator', 'Integrator: land %s\'s reviewed commits and record its integration receipt' % owner_key
    if standing_ == 'landed':
        return 'controller', ('%s is integrated; each lane either verifies its receipt on a prerequisite wake or holds '
                              'on its own remaining gap (`inspect lane <consumer>` shows which)' % owner_key)
    if standing_ == 'blocked':
        return 'owner', 'Unblock %s first; it waits on %s' % (owner_key, ', '.join(map(label, waits_on)) or 'unstructured prose')
    return 'operator', 'Inspect %s (state %s)' % (owner_key, standing_)


def index(state, decisions=DECISIONS, keys=None):
    """{lane: refs} for blocked/waiting lanes (or `keys`), and the issue owner table."""
    table = owners(state)
    lanes = state.get('lanes', {})
    keys = [k for k, l in lanes.items() if l.get('state') in WAITING] if keys is None else keys
    return {k: refs(state, k, table, decisions) for k in keys}, table


def roots(state, key, found, table, decisions=DECISIONS, seen=None):
    """Terminal refs reached by following blocked owners from `key`, and any cycle as a lane list."""
    seen = (seen or []) + [key]
    result, cycles = set(), []
    for ref in found.get(key, []):
        lane, how = owner(state, ref, table, decisions)
        if how != 'blocked' or lane is None:
            result.add(ref); continue
        if lane in seen:
            cycles.append(seen[seen.index(lane):] + [lane]); continue
        if lane not in found: found[lane] = refs(state, lane, table, decisions)
        deeper, more = roots(state, lane, found, table, decisions, seen)
        result |= deeper or {ref}
        cycles += more
    return result, cycles


def groups(state, decisions=DECISIONS, limit=None):
    """Blocked/waiting lanes grouped on each resolved owner lane, with root and one next action; refs
    no lane owns (a decision issue, a user ask, an unowned or external issue) group on the ref.

    '#N' and the name of the lane owning issue N form one group, and `refs` keeps every ref that
    pointed there. A lane with several owners appears in each group; `unstructured` lists lanes with none."""
    found, table = index(state, decisions)
    members = {}
    for key, value in found.items():
        for ref in value:
            lane = owner(state, ref, table, decisions)[0]
            row = members.setdefault('lane:' + lane if lane else ref, (set(), set()))
            row[0].add(key); row[1].add(ref)
    result, cycles = [], []
    for ref, (keys, cited) in members.items():
        lane, how = owner(state, ref, table, decisions)
        waits = found.get(lane) if lane in found else refs(state, lane, table, decisions) if how == 'blocked' else []
        rooted, loop = roots(state, lane, dict(found, **{lane: waits}), table, decisions) if how == 'blocked' else (set(), [])
        cycles += loop
        who, next_action = action(ref, lane, how, waits, len(keys))
        if loop: who, next_action = 'owner', 'Break the circular wait ' + ' -> '.join(loop[0])
        result.append(dict(ref=ref, refs=sorted(cited), label=', '.join(map(label, sorted(cited))), count=len(keys),
                           lanes=sorted(keys), owner=lane, owner_state=how,
                           owner_waits_on=waits, roots=sorted(rooted), accountable=who, next_action=next_action))
    result.sort(key=lambda g: (-g['count'], g['ref']))
    unique = {tuple(c[:-1]) for c in cycles}
    return dict(groups=result[:limit] if limit else result, total_groups=len(result),
                unstructured=sorted(k for k, v in found.items() if not v),
                cycles=[list(c) + [c[0]] for c in sorted({min(c[i:] + c[:i] for i in range(len(c))) for c in unique})])


def prose(lane):
    """Normalized dependency text of a lane without structured refs (the older byte-exact signature)."""
    deps = lane.get('dependencies') or []
    text = ' '.join(sorted(d.strip() for d in deps if isinstance(d, str) and d.strip()))
    if not text:
        text = lane.get('progress_detail') or lane.get('next_action') or ''
        text = text if isinstance(text, str) else ''
    return ' '.join(text.casefold().split()) or None
