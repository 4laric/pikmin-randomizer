"""Compact assignment visibility for native export repair demand."""
from .support_actions import extra_targets, same


def status(reg):
    state=reg.snapshot()
    scopes=state.get('throughput_runtime',{}).get('autofill',{}).get('planner_pool',{}).get('scopes',{})
    rows=[]
    for target in extra_targets(reg,state):
        if target['kind']!='export_preparation':continue
        row=dict(lane=target['lane'],status='awaiting helper',helper=None,worker=None,
                 reason=target['export_blocker'])
        for scope in scopes.values():
            if 'completed_at' in scope:continue
            if any(t.get('kind')=='export_preparation' and t['lane']==target['lane'] and same(t,state['lanes'][target['lane']])
                   for t in scope.get('support_targets',[])):
                helper=scope['spec']['lane']['lane'];lane=state['lanes'].get(helper,{})
                row.update(helper=helper,worker=lane.get('worker_id'),status=lane.get('state','preparing assignment'))
                break
        packets=[a for a in state.get('support_actions',{}).values() if a['key']==target['lane'] and
                 a['action']=='integration_packet' and a['target'].get('kind')=='export_preparation' and
                 same(a['target'],state['lanes'][target['lane']])]
        if packets:
            packet=max(packets,key=lambda a:a['at'])
            from .export_packet import error
            problem=error(reg,packet)
            if problem:
                row['packet_error']=problem
                if row['status']=='awaiting helper':row['status']='invalid packet; awaiting replacement'
            elif target.get('export_packet_repair'):
                row['packet']=packet['id']
                row['packet_error']=target['export_packet_repair']['reason']
                if row['status']=='awaiting helper':row['status']='unconsumed packet; awaiting reassessment'
            else:
                row.update(status='packet ready for integrator',helper=packet['reviewer'],packet=packet['id'])
        rows.append(row)
    return rows
