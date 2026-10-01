"""Bounded helper follow-up when export packets never become receipts."""
from .control import fingerprint
from .support_actions import same


def semantic(packet):
    details = packet['details']
    return fingerprint([packet['key'],
        {k:packet['target'].get(k) for k in ('generation','root','native','handoff')},
        details.get('destination'), (details.get('export_patch') or {}).get('sha256')])


def stalled(state, packet):
    """One reassessment per patch/destination, never per new report wording."""
    lane = state['lanes'].get(packet['key'], {})
    if lane.get('integration') or not same(packet['target'], lane):
        return None
    token = semantic(packet)
    equivalents = [a for a in state.get('support_actions', {}).values()
        if a['action']=='integration_packet' and a['target'].get('kind')=='export_preparation'
        and semantic(a)==token]
    ids = {a['id'] for a in equivalents}
    owners = {s.get('owner_lane') for s in state.get('throughput', {}).get('workstreams', {}).values()
              if packet['key'] in s.get('lanes', [])}
    attempts = sorted([x for x in state.get('control', {}).get('launches', {}).values()
        if x.get('lane') in owners and x.get('status')=='exited' and x.get('bound_generation')
        and any(i in x.get('instruction','') for i in ids)], key=lambda x:x['created_at'])
    if len(attempts)<2:
        return None
    first = min(equivalents, key=lambda a:a['at'])
    return dict(packet=first['id'], recovery_token=token,
        reason='Two completed integration attempts received this export packet without completing delivery; inspect their evidence and correct the concrete remaining blocker.',
        attempts=[dict(lane=x['lane'],generation=x['bound_generation'],created_at=x['created_at'])
                  for x in attempts[:2]])
