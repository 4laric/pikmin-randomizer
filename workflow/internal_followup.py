"""Route evidenced internal findings separately from completed classification."""
import copy
from .control import fingerprint
from .handoff import require, nonempty
from .planner_demand import is_helper

ACTIVE={'ready','running','waiting_resource','reconciling','handoff_ready','integrating'}


def validate_finding(state, consumer, finding):
    require(isinstance(finding,dict) and finding.get('kind') in
            ('missing_producer','owner_blocked','integration_review'),'Typed internal blocker required')
    require(nonempty(finding.get('missing')) and nonempty(finding.get('next_action')),
            'Precise missing input and concrete follow-up required')
    inspected=finding.get('inspected_lanes')
    require(isinstance(inspected,list) and all(isinstance(k,str) and k in state['lanes'] for k in inspected),
            'Record existing lane identities inspected for ownership')
    owner=finding.get('owner_lane')
    if finding['kind']=='missing_producer':
        require(not owner,'Missing producer cannot claim an existing owner')
    else:
        require(owner in state['lanes'] and not is_helper(owner) and owner in inspected,
                'Existing inspected implementation owner required')
    # Consumer-owned unfinished work is a legitimate classification, never a delivery edge.


def requests(state):
    from .dependency_classification import signature
    result={}
    latest={}
    for row in sorted(state.get('dependency_classifications',{}).values(),key=lambda r:r['at']):
        latest[row['consumer']]=row
    for row in latest.values():
        key=row['consumer'];lane=state['lanes'].get(key,{})
        if lane.get('state')!='blocked' or row['snapshot']!=signature(lane):continue
        findings=[dict(requirement=d['requirement'],check=d['check'],reason=d['reason'],**d['internal_blocker'])
                  for d in row['dispositions'] if d.get('internal_blocker')]
        if not findings:continue
        # Re-recording or changing report prose must not reset the attempt budget.
        identity='internal-followup:'+fingerprint([key,row['snapshot']])
        result[identity]=dict(id=identity,consumer=key,snapshot=row['snapshot'],findings=findings,
                             report=row['evidence'],classification=row['id'])
    return result


def queue_status(state):
    attempts=state.get('throughput_runtime',{}).get('autofill',{}).get('prerequisite_recovery',{})
    result=[]
    for identity,row in requests(state).items():
        attempt=attempts.get(identity,{})
        helper=attempt.get('lane');lane=state['lanes'].get(helper,{})
        actions=[a for a in state.get('support_actions',{}).values() if a.get('reviewer')==helper and a.get('key')==row['consumer']]
        status=('awaiting_delivery' if any(a['action'] in ('proposal','producer','integration_packet') for a in actions)
                else 'needs_attention' if attempt and lane.get('state') in ('blocked','done')
                else 'assigned' if attempt else 'pending')
        result.append(dict(row,status=status,helper=helper))
    return result


def allocations(state, helpers, records, prior=None):
    result=dict(prior or {});reserved=set()
    for item in result.values():reserved.update(item['request']['lanes'])
    for row in records.values():
        if 'completed_at' not in row:
            reserved.update(row.get('recovery_targets',[]));reserved.update(row.get('followup_owner_lanes',[]))
            reserved.update(t['lane'] for t in row.get('support_targets',[]))
    available=[h for h in helpers if not h.get('kind') and h['scope'] not in result and
               (not records.get(h['scope']) or 'completed_at' in records[h['scope']])]
    data=state.get('throughput_runtime',{}).get('autofill',{})
    for identity,row in requests(state).items():
        from .action_routing import routes
        planning=[r['finding'] for r in routes(state,row) if r['kind']=='planning']
        if not planning:continue
        row=dict(row,findings=planning)
        key=row['consumer'];owners={f['owner_lane'] for f in row['findings'] if f.get('owner_lane')}
        targets=owners|{key}
        if identity in data.get('prerequisite_recovery',{}) or targets & reserved:continue
        if any(state['lanes'][k].get('state') in ACTIVE for k in owners):continue
        if any(x.get('lane') in targets and x.get('status') in ('intent','spawned','running','exiting')
               for x in state.get('control',{}).get('launches',{}).values()):continue
        # Reuse already staged/published work, including work created by a classifier.
        def outstanding(a):
            item=data.get('items',{}).get(a.get('details',{}).get('proposal_id'),{})
            producer=state['lanes'].get(item.get('lane'),{})
            return producer.get('state') in ACTIVE or (not producer and item.get('status') not in ('completed','rejected','superseded'))
        if any(a.get('key') in targets and a.get('action')=='proposal' and outstanding(a)
               for a in state.get('support_actions',{}).values()):continue
        if not available:break
        helper=available.pop(0)
        result[helper['scope']]=dict(key=identity,input_snapshot=row['snapshot'],request=dict(
            id=identity,status='internal-blocker-followup',scope=helper['scope'],report=copy.deepcopy(row['report']),
            lanes=[key],issues=[state['lanes'][key]['issue']],internal_followup=copy.deepcopy(row),
            followup_owner_lanes=sorted(owners),required_result='Classification is already complete. Prepare the '
            'named bounded implementation, ownership repair, or integration-review packet through existing '
            'proposal/support-action APIs. Reuse the inspected owner and canonical claims; do not duplicate '
            'active scopes. A consumer-owned gap calls for repair/resumption planning, never a self dependency. '
            'Record a validated actionable outcome or finish blocked with exact evidence; do not reclassify '
            'the same finding, manufacture external inputs or claim the consumer is unblocked.'))
        reserved.update(targets)
    return result
